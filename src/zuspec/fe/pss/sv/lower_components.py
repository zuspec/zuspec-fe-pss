"""Lower PSS components to SV IR nodes.

Each ``DataTypeComponent`` becomes an ``SVClass extends zsp_component``
with a constructor, sub-component fields, resource pool fields, and
an import interface reference when the component declares import functions.
"""
from __future__ import annotations

from typing import List

from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv import (
    SVArg,
    SVClass,
    SVClassField,
    SVFunctionDecl,
)

from .context import LoweringContext


def lower_component(ctx: LoweringContext, dtype: ir.DataTypeComponent) -> SVClass:
    """Lower a PSS component to an SVClass extending zsp_component."""
    sv_name = ctx.mangle_name(dtype.name) if dtype.name else "unnamed_comp"

    extends = "zsp_component"
    if dtype.super:
        if isinstance(dtype.super, ir.DataTypeRef):
            extends = ctx.mangle_name(dtype.super.ref_name)
        elif hasattr(dtype.super, 'name') and dtype.super.name:
            extends = ctx.mangle_name(dtype.super.name)

    # Fields
    fields: List[SVClassField] = []
    ctor_body: List[str] = ["super.new(name, parent);"]

    # Import interface field (if the component has import functions)
    import_funcs = [f for f in dtype.functions if getattr(f, 'is_import', False)]
    if import_funcs:
        import_if_name = f"{sv_name}_import_if"
        fields.append(SVClassField(name="import_if", dtype=import_if_name))

    for f in dtype.fields:
        sv_dtype = ctx.pss_type_to_sv_type_str(f.datatype)
        fields.append(SVClassField(name=f.name, dtype=sv_dtype))

        # Auto-construct sub-components and resource pools
        if isinstance(f.datatype, ir.DataTypeComponent):
            ctor_body.append(f'{f.name} = new("{f.name}", this);')
        elif isinstance(f.datatype, ir.DataTypeRef):
            # May be a resource pool -- detect by naming convention
            ref_name = f.datatype.ref_name
            resolved = ctx.ir_ctx.type_map.get(ref_name) if ctx.ir_ctx else None
            if resolved and isinstance(resolved, ir.DataTypeComponent):
                ctor_body.append(f'{f.name} = new("{f.name}", this);')

    # Constructor
    ctor = SVFunctionDecl(
        name="new",
        args=[
            SVArg(name="name", dtype="string"),
            SVArg(name="parent", dtype="zsp_component"),
        ],
        return_type="",
        body_lines=ctor_body,
    )

    return SVClass(
        name=sv_name,
        extends_name=extends,
        fields=fields,
        functions=[ctor],
    )
