"""Lower flow-object constraint propagation from consumer to producer.

When a producer and consumer share a flow object (buffer, stream, or
state), the consumer may impose constraints on the flow-object fields.
These constraints must be propagated to the producer's ``randomize()``
call so the producer generates values that satisfy the consumer.

At lowering time:
1. For each producer/consumer pair bound by a flow object, extract
   the consumer's constraints that reference flow-object fields.
2. Translate those constraints to SV expression strings.
3. Inject them as additional ``randomize() with { ... }`` arguments
   on the producer's traversal.
"""
from __future__ import annotations

import dataclasses as dc
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from zuspec.dataclasses import ir

if TYPE_CHECKING:
    from .context import LoweringContext


@dc.dataclass
class PropagatedConstraint:
    """A constraint extracted from a consumer and remapped for the producer.

    Attributes:
        original_expr: The original SV constraint expression string
                       (from the consumer's constraint block).
        remapped_expr: The expression with flow-object field references
                       remapped to the producer's output field names.
        source_action: Name of the consumer action type the constraint
                       came from.
        source_constraint: Name of the constraint block on the consumer.
    """
    original_expr: str
    remapped_expr: str
    source_action: str = ""
    source_constraint: str = ""


def extract_flow_constraints(
    ctx: LoweringContext,
    consumer_constraints: List[Tuple[str, List[str]]],
    flow_fields: Set[str],
    field_remap: Optional[Dict[str, str]] = None,
) -> List[PropagatedConstraint]:
    """Extract and remap constraints that reference flow-object fields.

    Scans the consumer's constraint expressions for references to
    flow-object input fields, and remaps them to the producer's
    corresponding output field names.

    Args:
        ctx: Lowering context.
        consumer_constraints: List of (constraint_name, [expr_strings])
            from the consumer action's SVConstraintBlock nodes.
        flow_fields: Set of field names on the consumer that are
            flow-object inputs (e.g. ``{"buf_in"}``).
        field_remap: Optional mapping from consumer field name to
            producer field name (e.g. ``{"buf_in": "buf_out"}``).
            If not provided, field names are used as-is.

    Returns:
        List of PropagatedConstraint with remapped expressions.
    """
    remap = field_remap or {}
    result: List[PropagatedConstraint] = []

    for cname, exprs in consumer_constraints:
        for expr in exprs:
            if _references_any_field(expr, flow_fields):
                remapped = _remap_fields(expr, remap)
                result.append(PropagatedConstraint(
                    original_expr=expr,
                    remapped_expr=remapped,
                    source_constraint=cname,
                ))

    return result


def propagate_constraints_to_producer(
    consumer_constraints: List[Tuple[str, List[str]]],
    flow_fields: Set[str],
    field_remap: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Extract consumer constraints on flow fields and return SV
    expression strings suitable for the producer's ``randomize() with``
    block.

    This is the main entry point for constraint propagation. It
    combines extraction and remapping into a single call.

    Args:
        consumer_constraints: List of (constraint_name, [expr_strings]).
        flow_fields: Consumer field names that are flow-object inputs.
        field_remap: Consumer-to-producer field name mapping.

    Returns:
        List of SV constraint expression strings for the producer.
    """
    remap = field_remap or {}
    result: List[str] = []

    for _cname, exprs in consumer_constraints:
        for expr in exprs:
            if _references_any_field(expr, flow_fields):
                result.append(_remap_fields(expr, remap))

    return result


def build_field_remap(
    consumer_field: str,
    producer_field: str,
    sub_fields: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Build a field remapping dictionary for constraint propagation.

    Maps the consumer's input field (and optional sub-fields) to the
    producer's output field (and corresponding sub-fields).

    Args:
        consumer_field: Consumer's flow-object input field name.
        producer_field: Producer's flow-object output field name.
        sub_fields: Optional list of sub-field names (e.g. ``["addr", "size"]``).
            If provided, generates mappings like
            ``buf_in.addr -> buf_out.addr``.

    Returns:
        Dict mapping consumer field references to producer field references.
    """
    remap: Dict[str, str] = {consumer_field: producer_field}

    if sub_fields:
        for sf in sub_fields:
            remap[f"{consumer_field}.{sf}"] = f"{producer_field}.{sf}"

    return remap


# -----------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------

def _references_any_field(expr: str, fields: Set[str]) -> bool:
    """Check if an expression string references any of the given fields.

    Uses a simple token-boundary check: the field name must appear as a
    standalone identifier (not as a substring of a longer identifier).
    """
    for field in fields:
        idx = 0
        while True:
            idx = expr.find(field, idx)
            if idx < 0:
                break
            # Check character before
            if idx > 0 and (expr[idx - 1].isalnum() or expr[idx - 1] == '_'):
                idx += 1
                continue
            # Check character after
            end = idx + len(field)
            if end < len(expr) and (expr[end].isalnum() or expr[end] == '_'):
                idx += 1
                continue
            return True
    return False


def _remap_fields(expr: str, remap: Dict[str, str]) -> str:
    """Replace field references in an expression string using the remap dict.

    Processes longer keys first to avoid partial replacements
    (e.g. ``buf_in.addr`` before ``buf_in``).
    """
    if not remap:
        return expr

    result = expr
    # Sort by key length descending to replace longer matches first
    for old, new in sorted(remap.items(), key=lambda kv: -len(kv[0])):
        result = _replace_identifier(result, old, new)
    return result


def _replace_identifier(text: str, old: str, new: str) -> str:
    """Replace ``old`` with ``new`` only at identifier boundaries."""
    result = []
    idx = 0
    while idx < len(text):
        pos = text.find(old, idx)
        if pos < 0:
            result.append(text[idx:])
            break

        # Check boundary before
        if pos > 0 and (text[pos - 1].isalnum() or text[pos - 1] == '_'):
            result.append(text[idx:pos + 1])
            idx = pos + 1
            continue

        # Check boundary after
        end = pos + len(old)
        if end < len(text) and (text[end].isalnum() or text[end] == '_'):
            result.append(text[idx:pos + 1])
            idx = pos + 1
            continue

        result.append(text[idx:pos])
        result.append(new)
        idx = end

    return "".join(result)
