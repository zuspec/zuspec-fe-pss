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
from zuspec.dataclasses.rt.executor import ObjectExecutor, _ReturnSignal

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

        # Resolve action_type_cls on all ActivityAnonTraversal nodes now that
        # all classes are built.
        self._resolve_activity_action_types()

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

        When the struct inherits from a base (``dt.super`` is set), Python
        class inheritance is used so that base-class attributes are accessible
        on child instances, and a merged ``_zdc_struct`` is built so the
        constraint solver sees *all* fields (inherited + own).
        """
        annotations: Dict[str, Any] = {}
        ns: Dict[str, Any] = {}

        # Resolve base Python class and merged IR for inheritance
        base_py_cls, merged_dt = self._resolve_super(dt)
        base_classes = (base_py_cls,) if base_py_cls is not None else ()

        # Only add this struct's *own* fields to the dataclass body —
        # inherited fields come via Python class inheritance.
        for f in dt.fields:
            py_type, default = self._field_to_plain(f)
            annotations[f.name] = py_type
            ns[f.name] = default

        ns['__annotations__'] = annotations
        cls = type(name, base_classes, ns)
        cls = _stdlib_dc.dataclass(cls)
        # Resolve DataTypeRef fields to concrete types so the solver
        # can identify their domains (e.g., DataTypeRef('lang_e') -> DataTypeEnum).
        self._resolve_field_types(merged_dt)
        cls._zdc_struct = merged_dt
        # Tag state/buffer/stream/resource structs so the runtime can identify flow_kind
        if getattr(dt, 'flow_kind', None) is not None:
            cls._pss_flow_kind = dt.flow_kind
            cls._pss_has_initial = getattr(dt, 'has_initial_constraint', False)
            # For resource types: ensure instance_id field exists (built-in PSS LRM field).
            # For state types: ensure initial field exists (built-in PSS LRM field).
            # The pre-processor injects these into PSS source; we guard here in case
            # the Python-native path bypasses PSS parsing.
            if dt.flow_kind == 'resource' and not hasattr(cls, 'instance_id'):
                cls.instance_id = 0
            if dt.flow_kind == 'state' and not hasattr(cls, 'initial'):
                # Rebuild the dataclass with `initial` as an additional field
                import dataclasses as _dc2
                extra_ns = {'initial': _dc2.field(default=True), '__annotations__': {'initial': bool}}
                extra_ns.update(cls.__dict__)
                cls = type(cls.__name__, (object,), extra_ns)
                cls = _stdlib_dc.dataclass(cls)
                cls._zdc_struct = merged_dt
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

        # Resolve base Python class for component inheritance
        base_py_cls, merged_dt = self._resolve_super(dt)
        comp_base = base_py_cls if base_py_cls is not None else zdc.Component

        # Only add this component's *own* fields to the class body
        for f in dt.fields:
            py_type, default = self._field_to_zdc(f)
            annotations[f.name] = py_type
            defaults[f.name] = default

        # WI-2: Translate explicit pool declarations → ClaimPool pool fields.
        # pool [N] pad_r padring; becomes a zdc.pool() field with N pre-built
        # resource instances.  Wildcard bind (bind padring *;) is registered
        # with the pool metadata so PoolResolver can resolve ancestor pools.
        for pool in dt.pools:
            elem_cls = self.python_classes.get(pool.element_type_name)
            if elem_cls is None:
                continue
            cap = pool.capacity  # int or None
            if cap is None or cap <= 0:
                continue  # skip unbounded or zero-capacity pools for now
            # Build a factory that makes cap fresh resource instances at init time
            def _pool_factory(cls=elem_cls, n=cap):
                from zuspec.dataclasses.types import ClaimPool
                from zuspec.dataclasses.rt.resource_rt import make_resource
                items = []
                for i in range(n):
                    r = make_resource(cls)
                    r.instance_id = i
                    if hasattr(r, 'pad_id'):
                        r.pad_id = i
                    items.append(r)
                return ClaimPool.fromList(items)
            annotations[pool.name] = 'ClaimPool'
            defaults[pool.name] = zdc.pool(default_factory=_pool_factory)

        ns: Dict[str, Any] = {'__annotations__': annotations, **defaults}

        init_down = self._get_function(merged_dt, 'init_down')
        init_up   = self._get_function(merged_dt, 'init_up')
        # Both init_down and init_up run at component construction time.
        # init_down runs depth-first top-down; init_up runs bottom-up.
        # For simplicity we chain them both into __post_init__ in order.
        if init_down or init_up:
            _fns = [self._build_post_init(f) for f in [init_down, init_up] if f is not None]
            def _combined_init(self_comp, fns=_fns):
                for fn in fns:
                    fn(self_comp)
            ns['__post_init__'] = _combined_init

        # Also translate solve functions and other helper functions on the
        # component so that init_up/init_down can call them at runtime.
        SKIP = {'init_down', 'init_up'}
        for fn in merged_dt.functions:
            if fn.name in SKIP or fn.name in ns:
                continue
            ns[fn.name] = self._build_sync_fn(fn)

        cls = type(name, (comp_base,), ns)
        built = zdc.dataclass(cls)
        self._resolve_field_types(merged_dt)
        built._zdc_struct = merged_dt
        return built

    # ------------------------------------------------------------------
    # Action construction
    # ------------------------------------------------------------------

    def _build_action(self, dt: zdc_ir.DataTypeClass, parent_comp_name: str):
        comp_type = self.python_classes[parent_comp_name]

        # Resolve base action class for action inheritance
        base_py_cls, merged_dt = self._resolve_super(dt)
        if base_py_cls is not None:
            ActionBase = base_py_cls
        else:
            ActionBase = zdc.Action[comp_type]

        annotations: Dict[str, Any] = {}
        defaults: Dict[str, Any] = {}

        # Only add this action's *own* fields to the class body
        for f in dt.fields:
            py_type, default = self._field_to_zdc(f)
            annotations[f.name] = py_type
            defaults[f.name] = default

        ns: Dict[str, Any] = {'__annotations__': annotations, **defaults}

        body_fn = self._get_function(merged_dt, 'body')
        if body_fn:
            ns['body'] = self._build_body_fn(body_fn)

        pre_solve_fn = self._get_function(merged_dt, 'pre_solve')
        if pre_solve_fn:
            ns['pre_solve'] = self._build_sync_fn(pre_solve_fn)

        post_solve_fn = self._get_function(merged_dt, 'post_solve')
        if post_solve_fn:
            ns['post_solve'] = self._build_sync_fn(post_solve_fn)

        # After the solver picks values for rand X_id fields (constrained by
        # "x_id in comp.valid_list"), inject a post_solve that sets
        # _resource_filters['X'] = (r.pad_id == solved_x_id) so the pool
        # acquisition claims exactly the right resource.
        # Convention: rand field "X_id" pairs with lock field "X" (strip _id).
        lock_field_names = {
            f.name for f in merged_dt.fields
            if f.kind == zdc_ir.FieldKind.Lock
        }
        rand_id_pairs = [
            (f.name, f.name[:-3])     # ("in_pad_id", "in_pad")
            for f in merged_dt.fields
            if f.kind == zdc_ir.FieldKind.Field
            and getattr(f, 'rand_kind', None) is not None
            and f.name.endswith('_id')
            and f.name[:-3] in lock_field_names
        ]
        if rand_id_pairs:
            existing_post = ns.get('post_solve')

            def _make_filter_post_solve(pairs=rand_id_pairs, orig=existing_post):
                def post_solve(self):
                    if orig is not None:
                        orig(self)
                    filters = getattr(self, '_resource_filters', {})
                    for rand_name, lock_name in pairs:
                        val = getattr(self, rand_name, None)
                        if val is not None:
                            _v = int(val)
                            filters[lock_name] = lambda r, _i, v=_v: r.pad_id == v
                    self._resource_filters = filters
                return post_solve

            ns['post_solve'] = _make_filter_post_solve()


        cls = pytypes.new_class(
            dt.name,
            (ActionBase,),
            {},
            lambda d: d.update(ns),
        )
        cls = _stdlib_dc.dataclass(cls, kw_only=True)
        self._resolve_field_types(merged_dt)
        cls._zdc_struct = merged_dt
        # Collect soft constraint functions (PSS `constraint default`) and attach
        # to class so the constraint evaluator can treat them as lower-priority.
        soft_fns = [
            f for f in merged_dt.functions
            if f.name.startswith('_c_') and f.metadata.get('is_soft')
        ]
        if soft_fns:
            cls.__soft_constraints__ = [self._build_sync_fn(f) for f in soft_fns]
        # Attach covergroup IR list for Phase 3 coverage sampling
        if hasattr(dt, 'covergroups') and dt.covergroups:
            cls.__pss_covergroups__ = dt.covergroups
        if getattr(dt, "activity_ir", None) is not None:
            cls.__activity__ = dt.activity_ir
        return cls

    # ------------------------------------------------------------------
    # Callable builders (body / post_init / pre_solve / post_solve)
    # ------------------------------------------------------------------

    def _build_body_fn(self, func: zdc_ir.Function):
        stmts = func.body

        async def body(self_action):
            try:
                ObjectExecutor(self_action).execute_stmts(stmts)
            except _ReturnSignal:
                pass

        return body

    def _build_post_init(self, func: zdc_ir.Function):
        stmts = func.body
        # Try to compile to native Python for speed; fall back to interpreter.
        from zuspec.dataclasses.rt.ir_compiler import IRCompiler
        compiled = IRCompiler().compile(stmts, self_arg='self_comp')
        if compiled is not None:
            return compiled

        def __post_init__(self_comp):
            try:
                ObjectExecutor(self_comp).execute_stmts(stmts)
            except _ReturnSignal:
                pass

        return __post_init__

    def _build_sync_fn(self, func: zdc_ir.Function):
        stmts = func.body
        # Try to compile to native Python for speed; fall back to interpreter.
        from zuspec.dataclasses.rt.ir_compiler import IRCompiler
        compiled = IRCompiler().compile(stmts, self_arg='self_comp')
        if compiled is not None:
            return compiled

        def fn(self_action):
            try:
                return ObjectExecutor(self_action).execute_stmts(stmts)
            except _ReturnSignal as r:
                return r.value

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
            # Use explicit initial_value when set (e.g. `initial` field on state structs)
            default = 0
            if getattr(f, 'initial_value', None) is not None:
                iv = f.initial_value
                if hasattr(iv, 'value'):
                    default = py_type(iv.value)
            return py_type, default
        elif isinstance(dt, zdc_ir.DataTypeEnum):
            return int, 0
        elif isinstance(dt, (zdc_ir.DataTypeChandle,)):
            return int, 0
        elif isinstance(dt, zdc_ir.DataTypeList):
            return list, _stdlib_dc.field(default_factory=list)
        elif isinstance(dt, zdc_ir.DataTypeArray):
            n = dt.size if dt.size > 0 else 0
            return list, _stdlib_dc.field(default_factory=lambda _n=n: [0] * _n)
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
        # Flow-object input/output fields hold struct instances.
        # Set metadata so the activity runner can detect flow bindings.
        if f.kind in (zdc_ir.FieldKind.Input, zdc_ir.FieldKind.Output):
            direction = "input" if f.kind == zdc_ir.FieldKind.Input else "output"
            flow_meta = {"kind": "flow_ref", "direction": direction}
            if isinstance(dt, zdc_ir.DataTypeStruct):
                ref_cls = self.python_classes.get(dt.name)
                if ref_cls is not None:
                    return ref_cls, zdc.field(default=None, metadata=flow_meta)
            return int, zdc.field(default=None, metadata=flow_meta)
        # Resource lock/share claims: carry metadata for the activity runner
        if f.kind in (zdc_ir.FieldKind.Lock, zdc_ir.FieldKind.Share):
            claim_kind = "lock" if f.kind == zdc_ir.FieldKind.Lock else "share"
            res_meta = {"kind": "resource_ref", "claim": claim_kind}
            if isinstance(dt, zdc_ir.DataTypeStruct):
                ref_cls = self.python_classes.get(dt.name)
                if ref_cls is not None:
                    return ref_cls, zdc.field(default=None, metadata=res_meta)
            return int, zdc.field(default=None, metadata=res_meta)
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
            n = dt.size if dt.size > 0 else 0
            # WI-3: if the element type is a component, build a list of instances
            elem_dt = dt.element_type
            elem_cls = None
            if isinstance(elem_dt, zdc_ir.DataTypeComponent) and elem_dt.name:
                elem_cls = self.python_classes.get(elem_dt.name)
            elif isinstance(elem_dt, zdc_ir.DataTypeRef):
                elem_cls = self.python_classes.get(elem_dt.ref_name)
            if elem_cls is not None and isinstance(elem_cls, type) and issubclass(elem_cls, zdc.Component):
                return list, zdc.field(default_factory=lambda cls=elem_cls, _n=n: [cls() for _ in range(_n)])
            return list, zdc.field(default_factory=lambda _n=n: [0] * _n)
        elif isinstance(dt, zdc_ir.DataTypeMap):
            return dict, zdc.field(default_factory=dict)
        elif isinstance(dt, zdc_ir.DataTypeSet):
            return set, zdc.field(default_factory=set)
        elif isinstance(dt, zdc_ir.DataTypeString):
            return str, zdc.field()
        elif isinstance(dt, zdc_ir.DataTypeRef):
            ref_cls = self.python_classes.get(dt.ref_name)
            if ref_cls is None:
                # ref_name may be a short name; search by suffix
                for qname, py_cls in self.python_classes.items():
                    if qname.split('::')[-1] == dt.ref_name:
                        ref_cls = py_cls
                        break
            if ref_cls is not None:
                return ref_cls, zdc.field(default=None)
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

    def _resolve_activity_action_types(self) -> None:
        """Walk all __activity__ IR trees and populate action_type_cls on
        ActivityAnonTraversal nodes so the runner can find the Python class."""
        from zuspec.ir.core.activity import ActivityAnonTraversal as _AAT

        def _walk(node):
            if isinstance(node, _AAT) and node.action_type_cls is None:
                # Try exact match first, then search by short name
                cls = self.python_classes.get(node.action_type)
                if cls is None:
                    for qname, py_cls in self.python_classes.items():
                        # qname may be 'Comp::ActionName' — match by short name
                        if qname.split('::')[-1] == node.action_type:
                            cls = py_cls
                            break
                if cls is not None:
                    node.action_type_cls = cls
            # Recurse into child stmt lists
            for attr in ('stmts', 'body', 'if_body', 'else_body', 'branches'):
                for child in getattr(node, attr, []) or []:
                    if hasattr(child, 'stmts') or hasattr(child, 'body'):
                        _walk(child)
                    elif isinstance(child, _AAT):
                        _walk(child)
            if hasattr(node, 'branches'):
                from zuspec.ir.core.activity import SelectBranch as _SB
                for b in (node.branches or []):
                    if isinstance(b, _SB):
                        for s in b.body or []:
                            _walk(s)

        for cls in list(self.python_classes.values()):
            activity_ir = getattr(cls, '__activity__', None)
            if activity_ir is not None:
                for stmt in getattr(activity_ir, 'stmts', []) or []:
                    _walk(stmt)

    def _resolve_field_types(self, dt: zdc_ir.DataTypeStruct):
        """Walk all fields and replace DataTypeRef with the resolved IR type.

        This is necessary so the constraint solver's VariableExtractor can
        determine domains (e.g., for enums) without chasing forward references.
        """
        for f in dt.fields:
            if isinstance(f.datatype, zdc_ir.DataTypeRef):
                resolved = self.ctx.type_map.get(f.datatype.ref_name)
                if resolved is not None:
                    f.datatype = resolved
            # Also resolve nested struct fields recursively
            if isinstance(f.datatype, zdc_ir.DataTypeStruct):
                self._resolve_field_types(f.datatype)

    @staticmethod
    def _get_function(dt: zdc_ir.DataTypeStruct,
                      name: str) -> Optional[zdc_ir.Function]:
        return next((f for f in dt.functions if f.name == name), None)

    def _resolve_super(
        self, dt: zdc_ir.DataTypeStruct
    ) -> Tuple[Optional[type], zdc_ir.DataTypeStruct]:
        """Walk the super chain and return (base_py_cls, merged_dt).

        *base_py_cls* is the already-built Python class for the direct super
        type (or ``None`` if there is no super).  *merged_dt* is a
        ``DataTypeStruct`` whose ``fields`` and ``functions`` lists are the
        full flattened inheritance chain (base first), so the constraint
        solver sees every inherited field and constraint function.
        """
        if dt.super is None:
            return None, dt

        if isinstance(dt.super, zdc_ir.DataTypeRef):
            super_name = dt.super.ref_name
        else:
            super_name = getattr(dt.super, 'name', None)

        base_py_cls = self._lookup_class(super_name)

        # Build merged IR by walking the full chain (base-first) via the
        # already-merged _zdc_struct on the base Python class.
        if base_py_cls is not None and hasattr(base_py_cls, '_zdc_struct'):
            base_merged: zdc_ir.DataTypeStruct = base_py_cls._zdc_struct
            merged = zdc_ir.DataTypeStruct.__new__(zdc_ir.DataTypeStruct)
            # Copy scalar attributes from the child IR
            merged.__dict__.update(dt.__dict__)
            # Prepend base fields/functions so child overrides come last
            merged.fields = list(base_merged.fields) + list(dt.fields)
            merged.functions = list(base_merged.functions) + list(dt.functions)
        else:
            merged = dt

        return base_py_cls, merged

    def _lookup_class(self, name: Optional[str]) -> Optional[type]:
        """Look up a Python class by name, trying exact then short-name match."""
        if not name:
            return None
        cls = self.python_classes.get(name)
        if cls is not None:
            return cls
        # For qualified names like 'C::Base', the short name 'Base' may have
        # been stored as 'C::Base' — search by suffix.
        for qname, py_cls in self.python_classes.items():
            if qname == name or qname.split('::')[-1] == name:
                return py_cls
        return None

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
            # Visit super type before this type
            if dt.super is not None:
                super_name = (dt.super.ref_name
                              if isinstance(dt.super, zdc_ir.DataTypeRef)
                              else getattr(dt.super, 'name', None))
                if super_name:
                    visit(super_name)
            for f in dt.fields:
                if isinstance(f.datatype, zdc_ir.DataTypeRef):
                    visit(f.datatype.ref_name)
            result.append((name, dt))

        for name, _ in entries:
            visit(name)

        return result
