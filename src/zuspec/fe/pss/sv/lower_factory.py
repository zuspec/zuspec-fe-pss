"""Generate an action factory function for runtime inference.

The factory emits a ``zsp_create_action()`` SV function with a ``case``
statement mapping integer type IDs to ``new()`` calls for every concrete
action type in the model.  This enables runtime inference to instantiate
actions by type ID without SV reflection.

Design reference: pss-to-sv-execution-design.md S12.3.1
"""
from __future__ import annotations

import dataclasses as dc
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from zuspec.be.sv.ir.sv import (
    SVFunctionDecl,
    SVArg,
    SVRawItem,
)

if TYPE_CHECKING:
    from .context import LoweringContext


@dc.dataclass
class ActionTypeEntry:
    """Registry entry for one action type in the factory.

    Attributes:
        type_id:       Integer identifier (unique across the model).
        sv_class_name: Mangled SV class name (e.g. ``dma_c__transfer``).
        comp_type:     Mangled SV component class name (e.g. ``dma_c``).
                       None for actions without a component context.
    """
    type_id: int
    sv_class_name: str
    comp_type: Optional[str] = None


def assign_type_ids(
    action_names: List[str],
    ctx: LoweringContext,
) -> Dict[str, ActionTypeEntry]:
    """Assign sequential integer type IDs to a list of action names.

    Args:
        action_names: PSS qualified action names (e.g. ``"dma_c::transfer"``).
        ctx: Lowering context for name mangling and component lookup.

    Returns:
        Dict mapping PSS action name to ``ActionTypeEntry``.
    """
    registry: Dict[str, ActionTypeEntry] = {}
    for i, name in enumerate(sorted(action_names)):
        sv_name = ctx.mangle_name(name)
        comp_name = None
        if ctx.ir_ctx and hasattr(ctx.ir_ctx, 'parent_comp_names'):
            pss_comp = ctx.ir_ctx.parent_comp_names.get(name)
            if pss_comp:
                comp_name = ctx.mangle_name(pss_comp)
        registry[name] = ActionTypeEntry(
            type_id=i,
            sv_class_name=sv_name,
            comp_type=comp_name,
        )
    return registry


def emit_type_id_constants(
    registry: Dict[str, ActionTypeEntry],
) -> List[str]:
    """Emit ``parameter int`` declarations for type ID constants.

    Returns:
        SV lines declaring each type ID as a localparam.
    """
    lines: List[str] = []
    for _name, entry in sorted(registry.items(), key=lambda kv: kv[1].type_id):
        const_name = f"TYPE_ID_{entry.sv_class_name.upper()}"
        lines.append(f"localparam int {const_name} = {entry.type_id};")
    return lines


def emit_factory_function(
    registry: Dict[str, ActionTypeEntry],
) -> SVFunctionDecl:
    """Emit the ``zsp_create_action`` factory function.

    The function takes a type ID and component reference, instantiates
    the corresponding action class via a ``case`` statement, assigns
    the component, and returns the action as a ``zsp_action`` handle.

    Args:
        registry: Action type registry from ``assign_type_ids()``.

    Returns:
        SVFunctionDecl node for the factory function.
    """
    body: List[str] = []
    body.append("case (type_id)")

    for _name, entry in sorted(registry.items(), key=lambda kv: kv[1].type_id):
        const_name = f"TYPE_ID_{entry.sv_class_name.upper()}"
        body.append(f"  {const_name}: begin")
        body.append(f"    {entry.sv_class_name} a = new();")
        if entry.comp_type:
            body.append(f"    a.comp = comp;")
        else:
            body.append(f"    a.comp_base = comp;")
        body.append(f"    return a;")
        body.append(f"  end")

    body.append(f"  default: begin")
    body.append(f'    $fatal(1, "Unknown action type_id=%0d", type_id);')
    body.append(f"    return null;")
    body.append(f"  end")
    body.append("endcase")

    return SVFunctionDecl(
        name="zsp_create_action",
        args=[
            SVArg(name="type_id", dtype="int"),
            SVArg(name="comp", dtype="zsp_component"),
        ],
        return_type="zsp_action",
        body_lines=body,
    )


def emit_factory_items(
    registry: Dict[str, ActionTypeEntry],
) -> List:
    """Emit all factory-related SV IR nodes: type ID constants + factory function.

    Returns:
        List of SV IR nodes (SVRawItem for constants, SVFunctionDecl for factory).
    """
    items = []

    # Type ID constants
    const_lines = emit_type_id_constants(registry)
    if const_lines:
        items.append(SVRawItem(lines=const_lines))

    # Factory function
    items.append(emit_factory_function(registry))

    return items
