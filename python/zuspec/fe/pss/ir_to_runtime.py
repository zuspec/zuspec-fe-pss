"""
IR to Runtime Builder

Converts an AstToIrContext (produced by AstToIrTranslator) into live Python
classes that use the zuspec-dataclasses runtime.  No source-code generation is
performed — all classes are constructed in memory.
"""
from __future__ import annotations

import dataclasses as _stdlib_dc
import enum as pyenum
import types as pytypes
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import zuspec.dataclasses as zdc
from zuspec.dataclasses import ir as zdc_ir
from zuspec.dataclasses.rt.executor import ObjectExecutor

if TYPE_CHECKING:
    from .ast_to_ir import AstToIrContext

# ---------------------------------------------------------------------------
# Scalar integer type map  (bits, signed) -> zdc type alias
# ---------------------------------------------------------------------------
_INT_TYPE_MAP = {
    (1,  False): zdc.u1,
    (2,  False): zdc.u2,
    (4,  False): zdc.u4,
    (8,  False): zdc.u8,
    (16, False): zdc.u16,
    (32, False): zdc.u32,
    (64, False): zdc.u64,
    (8,  True):  zdc.i8,
    (16, True):  zdc.i16,
    (32, True):  zdc.i32,
    (64, True):  zdc.i64,
}


class ClassRegistry:
    """Dict-like container that also supports attribute access.

    Returned by :meth:`IrToRuntimeBuilder.build`.  Keys use the same
    conventions as the underlying dict:

    - Simple names for components: ``registry.Top``, ``registry['Top']``
    - Qualified names for actions:  ``registry['MyC::MyA']``
    - Nested attribute access via the component class attribute:
      ``registry.MyC.MyA``
    """

    def __init__(self, classes: Dict[str, Any]):
        object.__setattr__(self, '_classes', classes)

    # --- dict-style access ---------------------------------------------------

    def __getitem__(self, key: str) -> Any:
        return self._classes[key]

    def __contains__(self, key: str) -> bool:
        return key in self._classes

    def __iter__(self):
        return iter(self._classes)

    def keys(self):
        return self._classes.keys()

    def values(self):
        return self._classes.values()

    def items(self):
        return self._classes.items()

    def get(self, key: str, default=None):
        return self._classes.get(key, default)

    # --- attribute-style access ----------------------------------------------

    def __getattr__(self, name: str) -> Any:
        classes = object.__getattribute__(self, '_classes')
        if name in classes:
            return classes[name]
        raise AttributeError(f"No class named '{name}' in registry")

    def __repr__(self) -> str:
        return f"ClassRegistry({list(self._classes.keys())})"


class IrToRuntimeBuilder:
    """Convert an AstToIrContext into a dict of Python runtime classes.

    Usage::

        classes = IrToRuntimeBuilder(ir_ctx).build()
        Top = classes['Top']
        MyA = classes['MyC'].MyA   # action nested in component
        # equivalently: classes['MyC::MyA']

    The returned dict contains:
    - All ``DataTypeComponent`` entries keyed by their simple name.
    - All ``DataTypeClass`` (action) entries keyed by their qualified name
      (``'CompName::ActionName'``).  The action class is also set as an
      attribute on its parent component class so callers can write
      ``MyC.MyA``.
    """

    def __init__(self, ctx: 'AstToIrContext'):
        self.ctx = ctx
        # Accumulates built Python classes; populated during build()
        self.python_classes: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self) -> ClassRegistry:
        """Build and return the ClassRegistry of Python classes."""
        # Build enum types first (they may be referenced by fields)
        for name, dt in self.ctx.type_map.items():
            if isinstance(dt, zdc_ir.DataTypeEnum):
                cls = self._build_enum(name, dt)
                self.python_classes[name] = cls

        # Build pure data structs (DataTypeStruct but not DataTypeClass/Component)
        # before components so struct fields resolve correctly
        struct_entries = [
            (k, v) for k, v in self.ctx.type_map.items()
            if isinstance(v, zdc_ir.DataTypeStruct)
            and not isinstance(v, zdc_ir.DataTypeClass)
        ]
        for name, dt in self._topo_sort(struct_entries):
            cls = self._build_struct(name, dt)
            self.python_classes[name] = cls

        comp_entries = [
            (k, v) for k, v in self.ctx.type_map.items()
            if isinstance(v, zdc_ir.DataTypeComponent)
        ]
        action_entries = [
            (k, v) for k, v in self.ctx.type_map.items()
            if (isinstance(v, zdc_ir.DataTypeClass)
                and not isinstance(v, zdc_ir.DataTypeComponent)
                and '::' in k)
        ]

        # Build components in dependency order
        for name, dt in self._topo_sort(comp_entries):
            cls = self._build_component(name, dt)
            self.python_classes[name] = cls

        # Build actions (after all components are ready)
        for qname, dt in action_entries:
            parent_name = self.ctx.parent_comp_names.get(qname)
            if parent_name is None:
                continue
            if parent_name not in self.python_classes:
                continue
            cls = self._build_action(dt, parent_name)
            self.python_classes[qname] = cls
            # Also expose as attribute on the parent component class
            setattr(self.python_classes[parent_name], dt.name, cls)

        return ClassRegistry(self.python_classes)

    # ------------------------------------------------------------------
    # Struct construction (pure data types — PSS 'struct')
    # ------------------------------------------------------------------

    def _build_struct(self, name: str, dt: zdc_ir.DataTypeStruct) -> type:
        """Build a plain Python dataclass from a PSS struct IR node.

        The generated class has no zuspec-specific base class — it is a plain
        value container.  ``cls._zdc_struct`` is attached so that
        ``randomize()`` can find the IR metadata (rand fields, domains,
        constraint functions) without any extra decoration.
        """
        annotations: Dict[str, Any] = {}
        ns: Dict[str, Any] = {}

        for f in dt.fields:
            py_type, default = self._field_to_plain(f)
            annotations[f.name] = py_type
            ns[f.name] = default

        ns['__annotations__'] = annotations
        cls = type(name, (), ns)
        cls = _stdlib_dc.dataclass(cls)
        cls._zdc_struct = dt
        return cls

    # ------------------------------------------------------------------
    # Enum construction
    # ------------------------------------------------------------------

    def _build_enum(self, name: str, dt: zdc_ir.DataTypeEnum) -> type:
        """Build a Python IntEnum class from a DataTypeEnum IR node."""
        members = list(dt.items.items())
        cls = pyenum.IntEnum(name, members, start=0)
        # Override auto-start: IntEnum(name, {k: v}) form is most reliable
        cls = pyenum.IntEnum(name, {k: v for k, v in members})
        # Attach reference back to IR node so downstream tools can reflect
        dt.py_type = cls
        return cls

    # ------------------------------------------------------------------
    # Component construction
    # ------------------------------------------------------------------

    def _build_component(self, name: str, dt: zdc_ir.DataTypeComponent):
        annotations: Dict[str, Any] = {}
        defaults: Dict[str, Any] = {}

        for f in dt.fields:
            py_type, default = self._field_to_zdc(f)
            annotations[f.name] = py_type
            defaults[f.name] = default

        ns: Dict[str, Any] = {'__annotations__': annotations, **defaults}

        init_down = self._get_function(dt, 'init_down')
        if init_down:
            ns['__post_init__'] = self._build_post_init(init_down)

        cls = type(name, (zdc.Component,), ns)
        return zdc.dataclass(cls)

    # ------------------------------------------------------------------
    # Action construction
    # ------------------------------------------------------------------

    def _build_action(self, dt: zdc_ir.DataTypeClass, parent_comp_name: str):
        comp_type = self.python_classes[parent_comp_name]
        ActionBase = zdc.Action[comp_type]

        annotations: Dict[str, Any] = {}
        defaults: Dict[str, Any] = {}

        for f in dt.fields:
            py_type, default = self._field_to_zdc(f)
            annotations[f.name] = py_type
            defaults[f.name] = default

        ns: Dict[str, Any] = {'__annotations__': annotations, **defaults}

        body_fn = self._get_function(dt, 'body')
        if body_fn:
            ns['body'] = self._build_body_fn(body_fn)

        pre_solve_fn = self._get_function(dt, 'pre_solve')
        if pre_solve_fn:
            ns['pre_solve'] = self._build_sync_fn(pre_solve_fn)

        post_solve_fn = self._get_function(dt, 'post_solve')
        if post_solve_fn:
            ns['post_solve'] = self._build_sync_fn(post_solve_fn)

        return pytypes.new_class(
            dt.name,
            (ActionBase,),
            {},
            lambda d: d.update(ns),
        )

    # ------------------------------------------------------------------
    # Callable builders (body / post_init / pre_solve / post_solve)
    # ------------------------------------------------------------------

    def _build_body_fn(self, func: zdc_ir.Function):
        stmts = func.body

        async def body(self_action):
            ObjectExecutor(self_action).execute_stmts(stmts)

        return body

    def _build_post_init(self, func: zdc_ir.Function):
        stmts = func.body

        def __post_init__(self_comp):
            ObjectExecutor(self_comp).execute_stmts(stmts)

        return __post_init__

    def _build_sync_fn(self, func: zdc_ir.Function):
        stmts = func.body

        def fn(self_action):
            ObjectExecutor(self_action).execute_stmts(stmts)

        fn.__name__ = func.name
        return fn

    # ------------------------------------------------------------------
    # Field helpers
    # ------------------------------------------------------------------

    def _field_to_plain(self, f: zdc_ir.Field) -> Tuple[Any, Any]:
        """Return (python_type, default) for a struct field using plain types.

        Unlike ``_field_to_zdc``, this returns stdlib-compatible defaults
        (no ``zdc.field()``), suitable for a plain ``@dataclasses.dataclass``.
        """
        dt = f.datatype
        if isinstance(dt, zdc_ir.DataTypeInt):
            py_type = _INT_TYPE_MAP.get((dt.bits, dt.signed), int)
            return py_type, 0
        elif isinstance(dt, zdc_ir.DataTypeEnum):
            return int, 0
        elif isinstance(dt, (zdc_ir.DataTypeChandle,)):
            return int, 0
        elif isinstance(dt, (zdc_ir.DataTypeList, zdc_ir.DataTypeArray)):
            return list, _stdlib_dc.field(default_factory=list)
        elif isinstance(dt, zdc_ir.DataTypeMap):
            return dict, _stdlib_dc.field(default_factory=dict)
        elif isinstance(dt, zdc_ir.DataTypeSet):
            return set, _stdlib_dc.field(default_factory=set)
        elif isinstance(dt, zdc_ir.DataTypeString):
            return str, ""
        elif isinstance(dt, zdc_ir.DataTypeRef):
            ref_cls = self.python_classes.get(dt.ref_name)
            if ref_cls is not None:
                return ref_cls, _stdlib_dc.field(default_factory=ref_cls)
            return int, 0
        return int, 0

    def _field_to_zdc(self, f: zdc_ir.Field) -> Tuple[Any, Any]:
        dt = f.datatype
        if isinstance(dt, zdc_ir.DataTypeInt):
            py_type = _INT_TYPE_MAP.get((dt.bits, dt.signed), int)
            return py_type, zdc.field()
        elif isinstance(dt, zdc_ir.DataTypeEnum):
            enum_cls = dt.py_type if dt.py_type is not None else int
            return enum_cls, zdc.field()
        elif isinstance(dt, zdc_ir.DataTypeChandle):
            return int, zdc.field()
        elif isinstance(dt, zdc_ir.DataTypeList):
            return list, zdc.field(default_factory=list)
        elif isinstance(dt, zdc_ir.DataTypeArray):
            return list, zdc.field(default_factory=list)
        elif isinstance(dt, zdc_ir.DataTypeMap):
            return dict, zdc.field(default_factory=dict)
        elif isinstance(dt, zdc_ir.DataTypeSet):
            return set, zdc.field(default_factory=set)
        elif isinstance(dt, zdc_ir.DataTypeString):
            return str, zdc.field()
        elif isinstance(dt, zdc_ir.DataTypeRef):
            ref_cls = self.python_classes.get(dt.ref_name)
            if ref_cls is not None:
                return ref_cls, zdc.inst()
            return int, zdc.field()
        elif isinstance(dt, zdc_ir.DataTypeComponent):
            # Inline component sub-type — look up the built Python class by name
            ref_cls = self.python_classes.get(dt.name) if dt.name else None
            if ref_cls is not None:
                return ref_cls, zdc.inst()
            return int, zdc.field()
        return int, zdc.field()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _get_function(dt: zdc_ir.DataTypeStruct,
                      name: str) -> Optional[zdc_ir.Function]:
        return next((f for f in dt.functions if f.name == name), None)

    def _topo_sort(
        self,
        entries: List[Tuple[str, zdc_ir.DataTypeComponent]],
    ) -> List[Tuple[str, zdc_ir.DataTypeComponent]]:
        """Return entries ordered so dependencies come before dependents."""
        name_to_dt = {name: dt for name, dt in entries}
        result: List[Tuple[str, zdc_ir.DataTypeComponent]] = []
        visited: set = set()

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            dt = name_to_dt.get(name)
            if dt is None:
                return
            for f in dt.fields:
                if isinstance(f.datatype, zdc_ir.DataTypeRef):
                    visit(f.datatype.ref_name)
            result.append((name, dt))

        for name, _ in entries:
            visit(name)

        return result
