"""Lower head-action coordinated solve for parallel blocks.

When a parallel block has multiple branches whose head actions claim
resources from the same pool, a coordinated solve ensures unique
resource assignment across branches.
"""
from __future__ import annotations

import dataclasses as dc
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from .lower_resources import ResourceClaim

if TYPE_CHECKING:
    from .context import LoweringContext


@dc.dataclass
class HeadAction:
    """Describes a head action on one branch of a parallel block.

    Attributes:
        branch_index: Index of the branch in the parallel block.
        action_var:   SV variable name of the action instance.
        action_type:  Mangled SV type name.
        claims:       Resource claims on this action.
    """
    branch_index: int
    action_var: str
    action_type: str
    claims: List[ResourceClaim] = dc.field(default_factory=list)


def emit_head_action_solve(
    heads: List[HeadAction],
    pool_sizes: Dict[str, int],
) -> List[str]:
    """Emit the coordinated solve for head actions sharing resource pools.

    Groups head actions by pool, then emits either a shuffle-based
    permutation (simple case) or ``std::randomize`` with ``unique``
    (complex case).

    Args:
        heads: Head actions from each branch.
        pool_sizes: Map from pool expression to pool size.

    Returns:
        List of SV statement lines.
    """
    if not heads:
        return []

    # Group claims by pool
    pool_to_claims: Dict[str, List[Tuple[HeadAction, ResourceClaim]]] = {}
    for h in heads:
        for c in h.claims:
            pool_to_claims.setdefault(c.pool_expr, []).append((h, c))

    lines: List[str] = []

    for pool_expr, entries in pool_to_claims.items():
        if len(entries) <= 1:
            # Single claim on this pool -- no coordination needed
            continue

        pool_size = pool_sizes.get(pool_expr, len(entries))
        id_vars = [f"{h.action_var}.{c.id_field}" for h, c in entries]
        n = len(entries)

        if pool_size >= n and n <= 8:
            # Simple case: shuffle-based permutation
            lines.extend(_emit_shuffle_solve(id_vars, pool_size))
        else:
            # Complex case: std::randomize with unique
            lines.extend(_emit_randomize_solve(id_vars, pool_size))

    return lines


def _emit_shuffle_solve(id_vars: List[str], pool_size: int) -> List[str]:
    """Emit shuffle-based permutation for simple resource assignment.

    Creates an index array, shuffles it, and assigns indices to id vars.
    """
    n = len(id_vars)
    lines: List[str] = []
    lines.append("begin")
    lines.append(f"  int _pool_idx [{pool_size}];")
    lines.append(f"  // Initialize pool indices")
    lines.append(f"  for (int _i = 0; _i < {pool_size}; _i++)")
    lines.append(f"    _pool_idx[_i] = _i;")
    lines.append(f"  // Fisher-Yates shuffle")
    lines.append(f"  for (int _i = {pool_size} - 1; _i > 0; _i--) begin")
    lines.append(f"    int _j = $urandom_range(0, _i);")
    lines.append(f"    int _tmp = _pool_idx[_i];")
    lines.append(f"    _pool_idx[_i] = _pool_idx[_j];")
    lines.append(f"    _pool_idx[_j] = _tmp;")
    lines.append(f"  end")
    for i, var in enumerate(id_vars):
        lines.append(f"  {var} = _pool_idx[{i}];")
    lines.append("end")
    return lines


def _emit_randomize_solve(id_vars: List[str], pool_size: int) -> List[str]:
    """Emit std::randomize with unique constraint for complex cases."""
    n = len(id_vars)
    lines: List[str] = []
    lines.append("begin")

    # Declare temporary variables for std::randomize
    for i, var in enumerate(id_vars):
        lines.append(f"  int unsigned _rid_{i};")

    # Build constraint block
    constraint_parts: List[str] = []
    for i in range(n):
        constraint_parts.append(f"_rid_{i} inside {{[0:{pool_size - 1}]}}")

    # Unique constraint
    rid_list = ", ".join(f"_rid_{i}" for i in range(n))
    constraint_parts.append(f"unique {{{rid_list}}}")

    rid_decl_list = ", ".join(f"_rid_{i}" for i in range(n))
    constraints_str = "; ".join(constraint_parts)
    lines.append(f"  if (!std::randomize({rid_decl_list}) with {{ {constraints_str}; }})")
    lines.append(f'    $fatal(1, "head-action resource solve failed");')

    # Assign back
    for i, var in enumerate(id_vars):
        lines.append(f"  {var} = _rid_{i};")

    lines.append("end")
    return lines
