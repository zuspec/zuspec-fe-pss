"""Lower PSS import functions to SV virtual class declarations.

For each component with import functions, emit a virtual class with
pure virtual task/function declarations.
"""
from __future__ import annotations

from typing import List, Optional

from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv import (
    SVArg,
    SVClass,
    SVFunctionDecl,
    SVTaskDecl,
)

from .context import LoweringContext


def lower_import_interface(
    ctx: LoweringContext,
    comp: ir.DataTypeComponent,
) -> Optional[SVClass]:
    """Lower import functions from a component to a virtual interface class.

    Returns None if the component has no import functions.
    """
    import_funcs = [f for f in comp.functions if getattr(f, 'is_import', False)]
    if not import_funcs:
        return None

    comp_name = ctx.mangle_name(comp.name) if comp.name else "unnamed"
    cls_name = f"{comp_name}_import_if"

    tasks: List[SVTaskDecl] = []
    functions: List[SVFunctionDecl] = []

    for func in import_funcs:
        # Build SV argument list
        sv_args: List[SVArg] = []
        if func.args:
            for arg in (func.args.args if hasattr(func.args, 'args') else []):
                arg_name = arg.arg if hasattr(arg, 'arg') else str(arg)
                sv_args.append(SVArg(name=arg_name, dtype="int"))

        if func.is_async or (func.name == "body"):
            # Async import -> pure virtual task
            tasks.append(SVTaskDecl(
                name=func.name,
                args=sv_args,
                is_pure=True,
            ))
        else:
            # Sync import -> pure virtual function
            ret_type = "void"
            if func.returns:
                ret_type = ctx.pss_type_to_sv_type_str(func.returns)
            functions.append(SVFunctionDecl(
                name=func.name,
                args=sv_args,
                return_type=ret_type,
                is_pure=True,
            ))

    return SVClass(
        name=cls_name,
        is_virtual=True,
        tasks=tasks,
        functions=functions,
    )
