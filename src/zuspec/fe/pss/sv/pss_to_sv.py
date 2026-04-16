"""Top-level entry point: IR Context -> List[SV IR nodes].

Orchestrates all lowering passes in dependency order.
"""
from __future__ import annotations

from typing import Any, List, Tuple

from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv import SVForwardDecl

from ..ast_to_ir import AstToIrContext
from .context import LoweringContext
from .lower_types import lower_enum, lower_struct
from .lower_components import lower_component
from .lower_actions import lower_action
from .lower_imports import lower_import_interface


def pss_to_sv(ir_ctx: AstToIrContext) -> List[Any]:
    """Lower a Zuspec IR context to a list of SV IR nodes.

    The returned list is in dependency order:
    1. Forward declarations
    2. Enums
    3. Structs (plain data types)
    4. Import interface classes
    5. Components
    6. Actions

    Uses the qualified name from the type_map key (e.g. ``top_c::hello``)
    for name mangling rather than the dtype's own ``name`` field, which
    may be unqualified (e.g. ``hello``).

    Args:
        ir_ctx: The translation context from ``AstToIrTranslator.translate()``.

    Returns:
        Ordered list of SV IR nodes ready for ``SVEmitter``.
    """
    ctx = LoweringContext(ir_ctx=ir_ctx)
    result: List[Any] = []

    # Classify IR types, keeping the qualified name from the type_map key
    enums: List[Tuple[str, ir.DataTypeEnum]] = []
    structs: List[Tuple[str, ir.DataTypeStruct]] = []
    components: List[Tuple[str, ir.DataTypeComponent]] = []
    actions: List[Tuple[str, ir.DataTypeClass]] = []

    for name, dtype in ir_ctx.type_map.items():
        # Skip duplicates (same type registered under multiple names)
        if id(dtype) in ctx.emitted:
            continue
        ctx.emitted.add(id(dtype))

        if isinstance(dtype, ir.DataTypeEnum):
            enums.append((name, dtype))
        elif isinstance(dtype, ir.DataTypeComponent):
            components.append((name, dtype))
        elif isinstance(dtype, ir.DataTypeClass):
            actions.append((name, dtype))
        elif isinstance(dtype, ir.DataTypeStruct):
            structs.append((name, dtype))

    # 1. Enums
    for qname, e in enums:
        result.append(lower_enum(ctx, e))

    # 2. Structs (forward decls then definitions)
    for qname, s in structs:
        sv_name = ctx.mangle_name(qname)
        result.append(SVForwardDecl(class_name=sv_name))
    for qname, s in structs:
        # Temporarily set qualified name for lowering
        orig_name = s.name
        s.name = qname
        result.append(lower_struct(ctx, s))
        s.name = orig_name

    # 3. Import interfaces
    for qname, comp in components:
        orig_name = comp.name
        comp.name = qname
        imp_cls = lower_import_interface(ctx, comp)
        if imp_cls is not None:
            result.append(imp_cls)
        comp.name = orig_name

    # 4. Components (forward decls then definitions)
    for qname, comp in components:
        sv_name = ctx.mangle_name(qname)
        result.append(SVForwardDecl(class_name=sv_name))
    for qname, comp in components:
        orig_name = comp.name
        comp.name = qname
        result.append(lower_component(ctx, comp))
        comp.name = orig_name

    # 5. Actions (forward decls then definitions)
    for qname, act in actions:
        sv_name = ctx.mangle_name(qname)
        result.append(SVForwardDecl(class_name=sv_name))
    for qname, act in actions:
        comp_name = ir_ctx.parent_comp_names.get(qname)
        if not comp_name:
            # Fallback: try the unqualified name
            comp_name = ir_ctx.parent_comp_names.get(act.name)
        orig_name = act.name
        act.name = qname
        result.append(lower_action(ctx, act, comp_type_name=comp_name))
        act.name = orig_name

    return result
