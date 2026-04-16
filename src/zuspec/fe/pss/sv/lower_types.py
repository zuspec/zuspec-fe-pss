"""Lower PSS type definitions to SV IR nodes.

Handles DataTypeStruct, DataTypeEnum, and flow-object base types
(resource, buffer, stream, state).
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv import (
    SVClass,
    SVClassField,
    SVConstraintBlock,
    SVFunctionDecl,
    SVTypedefEnum,
)

from .context import LoweringContext
from .lower_constraints import lower_constraint_func


def lower_enum(ctx: LoweringContext, dtype: ir.DataTypeEnum) -> SVTypedefEnum:
    """Lower a PSS enum to an SVTypedefEnum."""
    sv_name = ctx.mangle_name(dtype.name) if dtype.name else "unnamed_enum"
    members: List[Tuple[str, int]] = list(dtype.items.items())
    return SVTypedefEnum(name=sv_name, members=members)


def lower_struct(ctx: LoweringContext, dtype: ir.DataTypeStruct) -> SVClass:
    """Lower a PSS struct to an SVClass.

    Struct fields map to SVClassField; constraint functions become
    SVConstraintBlock nodes.
    """
    sv_name = ctx.mangle_name(dtype.name) if dtype.name else "unnamed_struct"

    # Determine base class
    extends = None
    if dtype.super:
        if isinstance(dtype.super, ir.DataTypeRef):
            extends = ctx.mangle_name(dtype.super.ref_name)
        elif hasattr(dtype.super, 'name') and dtype.super.name:
            extends = ctx.mangle_name(dtype.super.name)

    # Fields
    fields: List[SVClassField] = []
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
    for func in dtype.functions:
        exprs = lower_constraint_func(ctx, func)
        if exprs is not None:
            constraints.append(SVConstraintBlock(name=func.name, exprs=exprs))

    return SVClass(
        name=sv_name,
        extends_name=extends,
        fields=fields,
        constraints=constraints,
    )


def lower_resource(ctx: LoweringContext, dtype: ir.DataTypeStruct) -> SVClass:
    """Lower a PSS resource type to an SVClass extending zsp_resource."""
    cls = lower_struct(ctx, dtype)
    if cls.extends_name is None:
        cls.extends_name = "zsp_resource"
    return cls


def lower_buffer(ctx: LoweringContext, dtype: ir.DataTypeStruct) -> SVClass:
    """Lower a PSS buffer type to an SVClass extending zsp_buffer."""
    cls = lower_struct(ctx, dtype)
    if cls.extends_name is None:
        cls.extends_name = "zsp_buffer"
    return cls


def lower_stream(ctx: LoweringContext, dtype: ir.DataTypeStruct) -> SVClass:
    """Lower a PSS stream type to an SVClass extending zsp_stream."""
    cls = lower_struct(ctx, dtype)
    if cls.extends_name is None:
        cls.extends_name = "zsp_stream"
    return cls


def lower_state(ctx: LoweringContext, dtype: ir.DataTypeStruct) -> SVClass:
    """Lower a PSS state type to an SVClass extending zsp_state."""
    cls = lower_struct(ctx, dtype)
    if cls.extends_name is None:
        cls.extends_name = "zsp_state"
    return cls
