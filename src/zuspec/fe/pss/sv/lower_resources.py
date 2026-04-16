"""Lower PSS resource acquire/release to SV statements.

For each action with resource claims (lock/share), emits the
corresponding pool operations in the generated SV code.
"""
from __future__ import annotations

import dataclasses as dc
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import LoweringContext


@dc.dataclass
class ResourceClaim:
    """Describes one resource claim on an action.

    Attributes:
        field_name:  Name of the resource field on the action.
        pool_expr:   SV expression for the pool (e.g. ``comp.chan_pool``).
        id_field:    Name of the instance_id field (e.g. ``chan_instance_id``).
        claim_kind:  ``"lock"`` or ``"share"``.
        is_head:     True if this is a head action (force_lock vs blocking lock).
    """
    field_name: str
    pool_expr: str
    id_field: str
    claim_kind: str = "lock"
    is_head: bool = False


def emit_resource_acquire(
    claims: List[ResourceClaim],
    action_var: str,
) -> List[str]:
    """Emit resource acquire statements for an action traversal.

    Claims are sorted by (pool_expr, field_name) for canonical ordering
    to prevent deadlock from inconsistent lock ordering.

    Args:
        claims: Resource claims for this action.
        action_var: SV variable name of the action instance.

    Returns:
        List of SV statement lines.
    """
    if not claims:
        return []

    sorted_claims = sorted(claims, key=lambda c: (c.pool_expr, c.field_name))
    lines: List[str] = []

    for c in sorted_claims:
        id_expr = f"{action_var}.{c.id_field}"
        if c.claim_kind == "share":
            if c.is_head:
                lines.append(f"{c.pool_expr}.force_share({id_expr});")
            else:
                lines.append(f"{c.pool_expr}.try_share({id_expr});")
        else:  # lock
            if c.is_head:
                lines.append(f"{c.pool_expr}.force_lock({id_expr});")
            else:
                lines.append(f"{c.pool_expr}.lock({id_expr});")

    # Assign resource references from pool after acquire
    for c in sorted_claims:
        id_expr = f"{action_var}.{c.id_field}"
        lines.append(f"{action_var}.{c.field_name} = {c.pool_expr}.get({id_expr});")

    return lines


def emit_resource_release(
    claims: List[ResourceClaim],
    action_var: str,
) -> List[str]:
    """Emit resource release statements after action body completes.

    Releases in reverse order of acquisition.

    Args:
        claims: Resource claims for this action.
        action_var: SV variable name of the action instance.

    Returns:
        List of SV statement lines.
    """
    if not claims:
        return []

    # Release in reverse of acquisition order
    sorted_claims = sorted(claims, key=lambda c: (c.pool_expr, c.field_name))
    reversed_claims = list(reversed(sorted_claims))
    lines: List[str] = []

    for c in reversed_claims:
        id_expr = f"{action_var}.{c.id_field}"
        if c.claim_kind == "share":
            lines.append(f"{c.pool_expr}.unshare({id_expr});")
        else:
            lines.append(f"{c.pool_expr}.unlock({id_expr});")

    return lines


def emit_resource_domain_constraint(
    claims: List[ResourceClaim],
    pool_sizes: dict,
) -> List[str]:
    """Emit domain constraint expressions for resource instance_id fields.

    Each instance_id must be in [0, pool_size-1].

    Args:
        claims: Resource claims.
        pool_sizes: Map from pool_expr -> pool size.

    Returns:
        List of SV constraint expression strings.
    """
    exprs: List[str] = []
    for c in claims:
        size = pool_sizes.get(c.pool_expr)
        if size is not None:
            exprs.append(f"{c.id_field} inside {{[0:{size - 1}]}}")
    return exprs
