"""Shared lowering context for PSS-to-SV translation.

Tracks name mangling, type registry, and source location state
across all lowering passes.
"""
from __future__ import annotations

import dataclasses as dc
import re
from typing import Any, Dict, List, Optional, Set

from zuspec.dataclasses import ir


@dc.dataclass
class LoweringContext:
    """State shared across all PSS-to-SV lowering passes."""

    # Maps PSS qualified type name -> mangled SV class name
    sv_name_map: Dict[str, str] = dc.field(default_factory=dict)

    # Maps PSS type name -> SV IR node (for forward-ref resolution)
    sv_node_map: Dict[str, Any] = dc.field(default_factory=dict)

    # Set of names already emitted (to avoid duplicates)
    emitted: Set[str] = dc.field(default_factory=set)

    # The AstToIrContext from the parser (type_map, parent_comp_names, etc.)
    ir_ctx: Optional[Any] = dc.field(default=None)

    def mangle_name(self, pss_name: str) -> str:
        """Convert a PSS qualified name to a valid SV identifier.

        ``MyComp::MyAction`` -> ``MyComp__MyAction``
        ``pkg::Type``        -> ``pkg__Type``
        """
        if pss_name in self.sv_name_map:
            return self.sv_name_map[pss_name]
        sv_name = re.sub(r'::', '__', pss_name)
        # Replace any remaining non-identifier chars
        sv_name = re.sub(r'[^A-Za-z0-9_]', '_', sv_name)
        self.sv_name_map[pss_name] = sv_name
        return sv_name

    def pss_type_to_sv_type_str(self, dtype: ir.DataType) -> str:
        """Map a PSS IR DataType to an SV type string.

        Returns a string suitable for use as an SV field type declaration.
        """
        if isinstance(dtype, ir.DataTypeInt):
            if dtype.bits == 1:
                return "bit"
            if dtype.signed:
                if dtype.bits == 32:
                    return "int"
                return f"int signed [{dtype.bits - 1}:0]"
            return f"bit [{dtype.bits - 1}:0]"

        if isinstance(dtype, ir.DataTypeEnum):
            return self.mangle_name(dtype.name) if dtype.name else "int"

        if isinstance(dtype, ir.DataTypeString):
            return "string"

        if isinstance(dtype, ir.DataTypeChandle):
            return "chandle"

        if isinstance(dtype, ir.DataTypeBool) if hasattr(ir, 'DataTypeBool') else False:
            return "bit"

        if isinstance(dtype, ir.DataTypeList):
            elem = self.pss_type_to_sv_type_str(dtype.element_type) if dtype.element_type else "int"
            return f"{elem} [$]"

        if isinstance(dtype, ir.DataTypeArray):
            elem = self.pss_type_to_sv_type_str(dtype.element_type) if dtype.element_type else "int"
            if dtype.size > 0:
                return f"{elem} [{dtype.size}]"
            return f"{elem} [$]"

        if isinstance(dtype, ir.DataTypeMap):
            key = self.pss_type_to_sv_type_str(dtype.key_type) if dtype.key_type else "string"
            val = self.pss_type_to_sv_type_str(dtype.value_type) if dtype.value_type else "int"
            return f"{val} [{key}]"

        if isinstance(dtype, ir.DataTypeSet):
            # SV has no native set; use associative array with dummy value
            elem = self.pss_type_to_sv_type_str(dtype.element_type) if dtype.element_type else "int"
            return f"bit [{elem}]"

        if isinstance(dtype, ir.DataTypeRef):
            return self.mangle_name(dtype.ref_name)

        if isinstance(dtype, (ir.DataTypeStruct, ir.DataTypeClass, ir.DataTypeComponent)):
            return self.mangle_name(dtype.name) if dtype.name else "int"

        # Fallback
        return "int"
