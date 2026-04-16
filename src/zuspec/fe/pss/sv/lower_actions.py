"""Lower PSS actions to SV IR nodes.

Each ``DataTypeClass`` (action) becomes an ``SVClass extends zsp_action``
with rand fields, constraints, body task, and component reference.
"""
from __future__ import annotations

from typing import List, Optional

from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv import (
    SVArg,
    SVClass,
    SVClassField,
    SVConstraintBlock,
    SVFunctionDecl,
    SVTaskDecl,
)

from .context import LoweringContext
from .lower_constraints import lower_constraint_func


def lower_action(
    ctx: LoweringContext,
    dtype: ir.DataTypeClass,
    comp_type_name: Optional[str] = None,
) -> SVClass:
    """Lower a PSS action to an SVClass extending zsp_action.

    Args:
        ctx: Lowering context.
        dtype: Action IR type (DataTypeClass or DataTypeAction).
        comp_type_name: Name of owning component (for comp field type).
    """
    sv_name = ctx.mangle_name(dtype.name) if dtype.name else "unnamed_action"

    extends = "zsp_action"
    if dtype.super:
        if isinstance(dtype.super, ir.DataTypeRef):
            extends = ctx.mangle_name(dtype.super.ref_name)
        elif hasattr(dtype.super, 'name') and dtype.super.name:
            extends = ctx.mangle_name(dtype.super.name)

    # Fields
    fields: List[SVClassField] = []

    # Component context field
    if comp_type_name:
        comp_sv_type = ctx.mangle_name(comp_type_name)
        fields.append(SVClassField(name="comp", dtype=comp_sv_type))

    for f in dtype.fields:
        sv_dtype = ctx.pss_type_to_sv_type_str(f.datatype)
        is_rand = f.rand_kind == "rand"
        is_randc = f.rand_kind == "randc"
        fields.append(SVClassField(
            name=f.name,
            dtype=sv_dtype,
            is_rand=is_rand,
            is_randc=is_randc,
        ))

    # Constraints
    constraints: List[SVConstraintBlock] = []
    functions: List[SVFunctionDecl] = []
    tasks: List[SVTaskDecl] = []

    for func in dtype.functions:
        # Constraint functions
        exprs = lower_constraint_func(ctx, func)
        if exprs is not None:
            constraints.append(SVConstraintBlock(name=func.name, exprs=exprs))
            continue

        # body -> virtual task
        if func.name == "body":
            tasks.append(SVTaskDecl(
                name="body",
                is_virtual=True,
                body_lines=["// body placeholder"],
            ))

        # pre_solve / post_solve -> virtual functions
        elif func.name in ("pre_solve", "post_solve"):
            functions.append(SVFunctionDecl(
                name=func.name,
                return_type="void",
                is_virtual=True,
                body_lines=["// placeholder"],
            ))

    return SVClass(
        name=sv_name,
        extends_name=extends,
        fields=fields,
        constraints=constraints,
        functions=functions,
        tasks=tasks,
    )
