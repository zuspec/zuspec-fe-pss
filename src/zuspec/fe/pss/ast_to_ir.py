"""
AST to IR Translation Module

Translates PSS AST nodes to Zuspec IR (Intermediate Representation).
"""
from __future__ import annotations
import logging
from typing import Dict, List, Optional, Any, Set, TYPE_CHECKING
from zuspec.dataclasses import ir

if TYPE_CHECKING:
    import pssparser.ast as pss_ast
else:
    import pssparser.ast as pss_ast


class AstToIrContext:
    """Context for AST to IR translation

    Maintains state during translation including:
    - Type registry (name -> IR DataType)
    - Symbol tables for scope resolution
    - Error collection
    - Current scope tracking
    """

    def __init__(self):
        self.type_map: Dict[str, ir.DataType] = {}
        self.symbol_table: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.scope_stack: List[ir.DataType] = []
        self.ir_context: Optional[ir.Context] = None
        # Maps qualified action name ('MyC::MyA') -> parent component name ('MyC')
        self.parent_comp_names: Dict[str, str] = {}
        # Set of local variable names in the current scope (e.g. foreach loop vars)
        self.local_vars: set = set()
        # Pending range constraints from `rand int in [range]` fields; flushed per type.
        self._pending_range_constraints: list = []

    def push_scope(self, scope: ir.DataType):
        """Push a new scope (component, struct, etc.)"""
        self.scope_stack.append(scope)

    def pop_scope(self) -> Optional[ir.DataType]:
        """Pop the current scope"""
        if self.scope_stack:
            return self.scope_stack.pop()
        return None

    def current_scope(self) -> Optional[ir.DataType]:
        """Get the current scope"""
        return self.scope_stack[-1] if self.scope_stack else None

    def add_type(self, name: str, dtype: ir.DataType):
        """Register a type in the type map"""
        self.type_map[name] = dtype

    def get_type(self, name: str) -> Optional[ir.DataType]:
        """Look up a type by name"""
        return self.type_map.get(name)

    def add_error(self, message: str):
        """Record a translation error"""
        self.errors.append(message)


class AstToIrTranslator:
    """Main translator from PSS AST to Zuspec IR

    Provides methods to translate:
    - Global scope (root node)
    - Components
    - Actions
    - Structs
    - Functions
    - Statements
    - Expressions
    - Data types
    """

    def __init__(self, debug: bool = False):
        """Initialize translator

        Args:
            debug: Enable debug logging
        """
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        # Annotation injection state (populated per translate() call)
        self._annotations: list = []
        self._type_chain_stack: list = []  # enclosing type names during traversal

    def translate(self, ast_root: pss_ast.GlobalScope, annotations=None) -> AstToIrContext:
        """Translate the entire AST to IR.

        Args:
            ast_root:    Root AST node (GlobalScope)
            annotations: Optional list of PssAnnotation from the two-pass Parser.
        Returns:
            Translation context with IR and type registry
        """
        self._annotations = list(annotations) if annotations else []
        self._type_chain_stack = []

        ctx = AstToIrContext()

        # Initialize built-in types
        self._init_builtin_types(ctx)

        # Translate global scope
        self._translate_global_scope(ctx, ast_root)

        return ctx

    def _init_builtin_types(self, ctx: AstToIrContext):
        """Initialize built-in types in the type registry"""
        # bool (represented as 1-bit unsigned int)
        bool_type = ir.DataTypeInt(name="bool", bits=1, signed=False)
        ctx.add_type("bool", bool_type)

        # int (32-bit signed)
        int_type = ir.DataTypeInt(name="int", bits=32, signed=True)
        ctx.add_type("int", int_type)

        # string
        string_type = ir.DataTypeString(name="string")
        ctx.add_type("string", string_type)

        # Common bit types
        for width in [8, 16, 32, 64]:
            bit_type = ir.DataTypeInt(name=f"bit[{width}]", bits=width, signed=False)
            ctx.add_type(f"bit[{width}]", bit_type)

            int_type = ir.DataTypeInt(name=f"int[{width}]", bits=width, signed=True)
            ctx.add_type(f"int[{width}]", int_type)

    def _translate_global_scope(self, ctx: AstToIrContext, global_scope):
        """Translate the global scope

        Args:
            ctx: Translation context
            global_scope: Root AST node (RootSymbolScope)
        """
        if self.debug:
            self.logger.debug("Translating global scope")

        # RootSymbolScope contains units (GlobalScope), iterate through them
        for i in range(global_scope.numUnits()):
            unit = global_scope.getUnit(i)
            self._translate_unit(ctx, unit)

    def _translate_unit(self, ctx: AstToIrContext, unit, namespace_prefix: str = ""):
        """Translate a global scope unit

        Args:
            ctx: Translation context
            unit: GlobalScope unit
            namespace_prefix: Dot-separated namespace prefix for types inside packages
        """
        # Use children() method which returns an iterable
        for child in unit.children():
            if child is None:
                continue

            if isinstance(child, pss_ast.PackageScope):
                self._translate_package(ctx, child, namespace_prefix)
            elif isinstance(child, pss_ast.Component):
                self._translate_component(ctx, child, namespace_prefix=namespace_prefix)
            elif isinstance(child, pss_ast.Action):
                self._translate_action(ctx, child, namespace_prefix=namespace_prefix)
            elif isinstance(child, pss_ast.Struct):
                self._translate_struct(ctx, child, namespace_prefix=namespace_prefix)
            elif isinstance(child, pss_ast.EnumDecl):
                self._translate_enum(ctx, child)
            elif isinstance(child, pss_ast.TypedefDeclaration):
                self._translate_typedef(ctx, child)
            elif isinstance(child, pss_ast.ExtendType):
                self._translate_extend(ctx, child)
            elif isinstance(child, pss_ast.ExtendEnum):
                self._translate_extend_enum(ctx, child)

    def _translate_extend(self, ctx: AstToIrContext, extend: pss_ast.ExtendType):
        """Translate a PSS extend declaration, adding fields/functions to the target IR type.

        PSS ``extend action C::a { rand int y; exec body {...} }`` adds new
        fields and exec blocks to the already-translated ``C::a`` DataTypeClass.
        """
        target_ti = extend.getTarget()
        if target_ti is None:
            return

        # Build the qualified name from TypeIdentifier elements
        parts = []
        for i in range(target_ti.numElems()):
            elem = target_ti.getElem(i)
            if elem is not None:
                id_node = elem.getId()
                if id_node is not None and hasattr(id_node, 'getId'):
                    parts.append(id_node.getId())

        if not parts:
            return

        # Look up the target IR type (try both qualified and short names)
        target_name = "::".join(parts)
        target_ir = ctx.type_map.get(target_name)
        if target_ir is None and len(parts) > 1:
            # Try without first part (component prefix): C::a → a
            target_ir = ctx.type_map.get("::".join(parts[1:]))

        if target_ir is None:
            if self.debug:
                self.logger.debug(f"extend: target type not found: {target_name}")
            return

        if self.debug:
            self.logger.debug(f"Translating extend for: {target_name}")

        ctx.push_scope(target_ir)

        for i in range(extend.numChildren()):
            child = extend.getChild(i)
            if child is None:
                continue

            if isinstance(child, pss_ast.Field):
                field = self._translate_field(ctx, child)
                if field:
                    target_ir.fields.append(field)
            elif isinstance(child, pss_ast.ExecBlock):
                kind = child.getKind()
                if kind == pss_ast.ExecKind.ExecKind_Body:
                    stmts = self._translate_exec_scope(ctx, child)
                    func = ir.Function(name='body', is_async=True, body=stmts)
                    target_ir.functions.append(func)
                elif kind == pss_ast.ExecKind.ExecKind_PreSolve:
                    stmts = self._translate_exec_scope(ctx, child)
                    func = ir.Function(name='pre_solve', is_async=False, body=stmts)
                    target_ir.functions.append(func)
                elif kind == pss_ast.ExecKind.ExecKind_PostSolve:
                    stmts = self._translate_exec_scope(ctx, child)
                    func = ir.Function(name='post_solve', is_async=False, body=stmts)
                    target_ir.functions.append(func)
            elif isinstance(child, pss_ast.ConstraintBlock):
                constraint_func = self._translate_constraint_block(ctx, child, target_ir)
                if constraint_func:
                    target_ir.functions.append(constraint_func)

        ctx.pop_scope()

    def _translate_extend_enum(self, ctx: AstToIrContext, extend: pss_ast.ExtendEnum):
        """Translate a PSS extend enum, appending new items to the existing IR DataTypeEnum."""
        target_ti = extend.getTarget()
        if target_ti is None:
            return

        parts = []
        for i in range(target_ti.numElems()):
            elem = target_ti.getElem(i)
            if elem is not None:
                id_node = elem.getId()
                if id_node is not None and hasattr(id_node, 'getId'):
                    parts.append(id_node.getId())

        if not parts:
            return

        target_name = "::".join(parts)
        target_ir = ctx.type_map.get(target_name)
        if target_ir is None:
            if self.debug:
                self.logger.debug(f"extend enum: target not found: {target_name}")
            return

        if not isinstance(target_ir, ir.DataTypeEnum):
            if self.debug:
                self.logger.debug(f"extend enum: target is not DataTypeEnum: {target_name}")
            return

        next_val = max(target_ir.items.values(), default=-1) + 1
        for i in range(extend.numItems()):
            item = extend.getItem(i)
            if item is None:
                continue
            item_name_node = item.getName()
            item_name = item_name_node.getId() if hasattr(item_name_node, 'getId') else str(item_name_node)
            val_node = item.getValue() if hasattr(item, 'getValue') else None
            if val_node is not None and hasattr(val_node, 'getValue'):
                next_val = val_node.getValue()
            target_ir.items[item_name] = next_val
            next_val += 1

    def _translate_package(self, ctx: AstToIrContext, pkg: pss_ast.PackageScope, parent_prefix: str = ""):
        """Translate a PSS package declaration.

        Types inside the package are registered with a namespace prefix:
        ``package my_pkg { component C {} }`` → type key ``my_pkg::C``.
        """
        parts = [pkg.getId(i).getId() for i in range(pkg.numId())]
        pkg_name = "::".join(parts)
        prefix = f"{parent_prefix}{pkg_name}::" if parent_prefix else f"{pkg_name}::"
        if self.debug:
            self.logger.debug(f"Translating package: {prefix}")
        # Recurse into package children using the same unit-level dispatch
        self._translate_unit(ctx, pkg, namespace_prefix=prefix)

    def _translate_component(self, ctx: AstToIrContext, component: pss_ast.Component, namespace_prefix: str = "") -> ir.DataTypeComponent:
        """Translate a PSS component to IR

        Args:
            ctx: Translation context
            component: PSS component AST node

        Returns:
            IR DataTypeComponent
        """
        # Extract component name
        name_node = component.getName()
        if isinstance(name_node, pss_ast.ExprId):
            comp_name = name_node.getId()
        else:
            comp_name = str(name_node)

        qualified_name = f"{namespace_prefix}{comp_name}"

        if self.debug:
            self.logger.debug(f"Translating component: {qualified_name}")

        # Check if this component inherits from reg_group_c
        # If so, create DataTypeRegisterGroup instead of DataTypeComponent
        is_register_group = False
        super_name = None
        super_t = component.getSuper_t()
        if super_t is not None:
            # Get super type name
            if isinstance(super_t, pss_ast.ExprId):
                super_name = super_t.getId()
                is_register_group = (super_name == "reg_group_c")
            elif isinstance(super_t, pss_ast.TypeIdentifier):
                # Handle TypeIdentifier case
                if super_t.numElems() > 0:
                    elem = super_t.getElem(0)
                    elem_id = elem.getId()
                    if isinstance(elem_id, pss_ast.ExprId):
                        super_name = elem_id.getId()
                        is_register_group = (super_name == "reg_group_c")
            else:
                super_name = str(super_t)

        # Create appropriate IR component type
        if is_register_group:
            comp = ir.DataTypeRegisterGroup(name=qualified_name, super=None)
        else:
            comp = ir.DataTypeComponent(name=qualified_name, super=None)

        # Register in type map (both short and qualified names)
        ctx.add_type(qualified_name, comp)
        if namespace_prefix:
            ctx.add_type(comp_name, comp)

        # Push scope and type-chain name for annotation matching
        ctx.push_scope(comp)
        self._type_chain_stack.append(comp_name)

        # Set super type reference if present
        if super_name:
            comp.super = ir.DataTypeRef(ref_name=super_name)

        # Translate children (fields, functions, nested types)
        for child in component.children():
            if child is None:
                continue

            if isinstance(child, pss_ast.Field):
                field = self._translate_field(ctx, child)
                if field:
                    comp.fields.append(field)
            elif isinstance(child, pss_ast.FunctionDefinition):
                func = self._translate_function(ctx, child)
                if func:
                    comp.functions.append(func)
            elif isinstance(child, pss_ast.Action):
                # Nested action — register under qualified name and track parent
                self._translate_action(ctx, child, parent_comp_name=qualified_name)
            elif isinstance(child, pss_ast.Struct):
                # Nested struct
                self._translate_struct(ctx, child)
            elif isinstance(child, pss_ast.EnumDecl):
                self._translate_enum(ctx, child)
            elif isinstance(child, pss_ast.ExecBlock):
                kind = child.getKind()
                if kind == pss_ast.ExecKind.ExecKind_InitDown:
                    stmts = self._translate_exec_scope(ctx, child)
                    func = ir.Function(name='init_down', is_async=False, body=stmts)
                    comp.functions.append(func)
                elif kind == pss_ast.ExecKind.ExecKind_InitUp:
                    stmts = self._translate_exec_scope(ctx, child)
                    func = ir.Function(name='init_up', is_async=False, body=stmts)
                    comp.functions.append(func)
                elif kind == pss_ast.ExecKind.ExecKind_RunStart:
                    stmts = self._translate_exec_scope(ctx, child)
                    func = ir.Function(name='run_start', is_async=False, body=stmts)
                    comp.functions.append(func)
                elif kind == pss_ast.ExecKind.ExecKind_RunEnd:
                    stmts = self._translate_exec_scope(ctx, child)
                    func = ir.Function(name='run_end', is_async=False, body=stmts)
                    comp.functions.append(func)

        # Pop type-chain name for component
        self._type_chain_stack.pop()

        # Add built-in functions for register groups
        if is_register_group:
            self._add_register_group_functions(ctx, comp)
            # Compute register offsets
            self._compute_register_offsets(ctx, comp)

        # Infer pools and pool-binds from flow-object fields in nested actions.
        # The PSS parser absorbs pool/bind declarations during link, so we
        # reconstruct them by scanning actions for input/output FieldRef fields
        # that reference flow-object types (buffer/stream/state/resource).
        self._infer_pools_and_binds(ctx, comp, qualified_name)

        # Pop scope
        ctx.pop_scope()

        return comp

    def _infer_pools_and_binds(self, ctx: AstToIrContext, comp: ir.DataTypeComponent, comp_name: str):
        """Infer pool and pool-bind declarations from flow-object field refs in nested actions.

        The PSS parser absorbs pool/bind AST nodes during link.  This method
        reconstructs them by scanning all actions registered under this
        component for input/output fields whose data types have a non-None
        flow_kind.  For each unique flow-object type, a Pool is created and
        a wildcard PoolBind is added (matching the ``bind pool_name *;``
        pattern commonly used in PSS examples).
        """
        seen_flow_types: dict[str, ir.DataTypeStruct] = {}
        prefix = f"{comp_name}::"

        for qname, dtype in ctx.type_map.items():
            if not qname.startswith(prefix):
                continue
            if not isinstance(dtype, ir.DataTypeClass):
                continue
            for field in dtype.fields:
                if field.kind in (ir.FieldKind.Input, ir.FieldKind.Output,
                                  ir.FieldKind.Lock, ir.FieldKind.Share):
                    fdt = field.datatype
                    if isinstance(fdt, ir.DataTypeStruct) and fdt.flow_kind is not None:
                        if fdt.name and fdt.name not in seen_flow_types:
                            seen_flow_types[fdt.name] = fdt

        for type_name, fdt in seen_flow_types.items():
            pool_name = f"{type_name}_pool"
            pool = ir.Pool(name=pool_name, element_type_name=type_name, element_type=fdt)
            comp.pools.append(pool)
            bind = ir.PoolBind(pool_name=pool_name, is_wildcard=True)
            comp.pool_binds.append(bind)

        # Also infer resource pools from lock/share fields in *all* actions
        # reachable from this component (including sub-components' actions).
        # PSS `pool [N] R name; bind name *;` is absorbed by the parser, so we
        # reconstruct it here.  Pool size defaults to 16 (sufficient for most
        # SoC pad rings and resource banks; override by subclassing if needed).
        seen_resource_types: dict[str, ir.DataTypeStruct] = {}

        def _collect_resource_types_for(comp_name_inner):
            """Recursively collect resource types from all actions under comp_name."""
            inner_prefix = f"{comp_name_inner}::"
            for qname2, dtype2 in ctx.type_map.items():
                if not qname2.startswith(inner_prefix):
                    continue
                if isinstance(dtype2, ir.DataTypeComponent):
                    # Recurse into sub-components
                    _collect_resource_types_for(dtype2.name)
                    continue
                if not isinstance(dtype2, ir.DataTypeClass):
                    continue
                for f2 in dtype2.fields:
                    if f2.kind in (ir.FieldKind.Lock, ir.FieldKind.Share):
                        fdt2 = f2.datatype
                        if isinstance(fdt2, ir.DataTypeStruct) and fdt2.flow_kind == "resource":
                            if fdt2.name and fdt2.name not in seen_resource_types:
                                seen_resource_types[fdt2.name] = fdt2

        # Collect from direct children actions and all sub-component actions
        _collect_resource_types_for(comp_name)
        for field in comp.fields:
            fdt = field.datatype
            # Handle direct component references
            sub_name = getattr(fdt, 'name', None) or getattr(fdt, 'ref_name', None)
            if sub_name and isinstance(ctx.type_map.get(sub_name), ir.DataTypeComponent):
                _collect_resource_types_for(sub_name)
            # Handle component array fields (DataTypeArray whose element is a component)
            elem_dt = getattr(fdt, 'element_type', None)
            if elem_dt is not None:
                elem_name = getattr(elem_dt, 'name', None) or getattr(elem_dt, 'ref_name', None)
                if elem_name and isinstance(ctx.type_map.get(elem_name), ir.DataTypeComponent):
                    _collect_resource_types_for(elem_name)

        for type_name, fdt in seen_resource_types.items():
            if any(p.element_type_name == type_name for p in comp.pools):
                continue  # already have a pool for this type
            pool_name = f"{type_name}_pool"
            pool = ir.Pool(name=pool_name, element_type_name=type_name,
                           element_type=fdt, capacity=16)
            comp.pools.append(pool)
            bind = ir.PoolBind(pool_name=pool_name, is_wildcard=True)
            comp.pool_binds.append(bind)

    def _translate_action(self, ctx: AstToIrContext, action: pss_ast.Action,
                          parent_comp_name: Optional[str] = None,
                          namespace_prefix: str = "") -> ir.DataTypeClass:
        """Translate a PSS action to IR DataTypeClass
        
        Args:
            ctx: Translation context
            action: PSS action AST node
            parent_comp_name: Name of enclosing component, if any
            namespace_prefix: Namespace prefix for package-scoped types
            
        Returns:
            IR DataTypeClass
        """
        # Extract action name
        name_node = action.getName()
        if isinstance(name_node, pss_ast.ExprId):
            action_name = name_node.getId()
        else:
            action_name = str(name_node)
            
        if self.debug:
            self.logger.debug(f"Translating action: {action_name}")
            
        # Create IR class for action
        action_ir = ir.DataTypeClass(name=action_name, super=None)
        
        # Register under qualified name if nested in a component, simple name otherwise
        if parent_comp_name:
            qname = f"{parent_comp_name}::{action_name}"
            ctx.add_type(qname, action_ir)
            ctx.parent_comp_names[qname] = parent_comp_name
        elif namespace_prefix:
            qname = f"{namespace_prefix}{action_name}"
            action_ir.name = qname
            ctx.add_type(qname, action_ir)
            ctx.add_type(action_name, action_ir)
        else:
            ctx.add_type(action_name, action_ir)
        
        # Push scope and type-chain name for annotation matching
        ctx.push_scope(action_ir)
        self._type_chain_stack.append(action_name)

        # Handle inheritance
        super_t = action.getSuper_t()
        if super_t is not None:
            super_name = self._type_identifier_name(super_t)
            if super_name:
                action_ir.super = ir.DataTypeRef(ref_name=super_name)

        # Handle abstract flag
        if hasattr(action, 'getIs_abstract') and action.getIs_abstract():
            action_ir.is_abstract = True
            
        # Translate children (fields, exec blocks, and constraints)
        for child in action.children():
            if child is None:
                continue
                
            if isinstance(child, pss_ast.Field):
                field = self._translate_field(ctx, child)
                if field:
                    action_ir.fields.append(field)
            elif isinstance(child, pss_ast.FieldRef):
                field = self._translate_field_ref(ctx, child)
                if field:
                    action_ir.fields.append(field)
            elif isinstance(child, pss_ast.FieldClaim):
                # lock/share resource claim (PSS LRM section 9.3)
                field = self._translate_field_claim(ctx, child)
                if field:
                    action_ir.fields.append(field)
            elif isinstance(child, pss_ast.ExecBlock):
                kind = child.getKind()
                if kind == pss_ast.ExecKind.ExecKind_Body:
                    stmts = self._translate_exec_scope(ctx, child)
                    func = ir.Function(name='body', is_async=True, body=stmts)
                    action_ir.functions.append(func)
                elif kind == pss_ast.ExecKind.ExecKind_PreSolve:
                    stmts = self._translate_exec_scope(ctx, child)
                    func = ir.Function(name='pre_solve', is_async=False, body=stmts)
                    action_ir.functions.append(func)
                elif kind == pss_ast.ExecKind.ExecKind_PostSolve:
                    stmts = self._translate_exec_scope(ctx, child)
                    func = ir.Function(name='post_solve', is_async=False, body=stmts)
                    action_ir.functions.append(func)
            elif isinstance(child, pss_ast.ConstraintBlock):
                constraint_func = self._translate_constraint_block(ctx, child, action_ir)
                if constraint_func:
                    action_ir.functions.append(constraint_func)
            elif isinstance(child, pss_ast.ActivityDecl):
                action_ir.activity_ir = self._translate_activity_body(ctx, child)
                     
        # Flush any pending `rand int in [range]` constraints as a constraint function.
        self._flush_range_constraints(ctx, action_ir)

        # Inject forall constraints, covergroups, and fill rewrites from PssAnnotation side-channel
        current_chain = list(self._type_chain_stack)
        for ann in self._annotations:
            if ann.type_chain == current_chain:
                if ann.kind == 'forall':
                    self._inject_forall_constraint(ctx, action_ir, ann)
                elif ann.kind == 'covergroup':
                    self._inject_covergroup(ctx, action_ir, ann)
                elif ann.kind == 'fill' and action_ir.activity_ir is not None:
                    self._inject_fill_in_activity(action_ir.activity_ir, ann)

        # Pop scope and type-chain name
        self._type_chain_stack.pop()
        ctx.pop_scope()
        
        return action_ir

    # ------------------------------------------------------------------
    # Activity body translation
    # ------------------------------------------------------------------

    def _translate_activity_body(
        self,
        ctx: 'AstToIrContext',
        activity_decl: 'pss_ast.ActivityDecl',
    ) -> 'ir.ActivitySequenceBlock':
        """Translate a PSS ActivityDecl to an IR ActivitySequenceBlock."""
        stmts = self._translate_activity_stmts(ctx, activity_decl.children())
        return ir.ActivitySequenceBlock(stmts=stmts)

    def _translate_activity_stmts(
        self,
        ctx: 'AstToIrContext',
        children,
    ) -> List['ir.ActivityStmt']:
        """Translate an iterable of PSS activity child nodes to IR ActivityStmt list."""
        result: List[ir.ActivityStmt] = []
        for child in children:
            if child is None:
                continue
            stmt = self._translate_activity_stmt(ctx, child)
            if stmt is not None:
                result.append(stmt)
        return result

    def _translate_activity_stmt(
        self,
        ctx: 'AstToIrContext',
        node,
    ) -> Optional['ir.ActivityStmt']:
        """Translate a single PSS activity AST node to an IR ActivityStmt."""

        if isinstance(node, (pss_ast.ActivitySequence, pss_ast.ActivityDecl)):
            stmts = self._translate_activity_stmts(ctx, node.children())
            return ir.ActivitySequenceBlock(stmts=stmts)

        if isinstance(node, pss_ast.ActivityParallel):
            stmts = self._translate_activity_stmts(ctx, node.children())
            join_spec = self._translate_join_spec(node.getJoin_spec())
            return ir.ActivityParallel(stmts=stmts, join_spec=join_spec)

        if isinstance(node, pss_ast.ActivitySchedule):
            stmts = self._translate_activity_stmts(ctx, node.children())
            return ir.ActivitySchedule(stmts=stmts)

        if isinstance(node, pss_ast.ActivityAtomicBlock):
            stmts = self._translate_activity_stmts(ctx, node.children())
            return ir.ActivityAtomic(stmts=stmts)

        if isinstance(node, pss_ast.ActivityActionHandleTraversal):
            return self._translate_handle_traversal(ctx, node)

        if isinstance(node, pss_ast.ActivityActionTypeTraversal):
            return self._translate_type_traversal(ctx, node)

        if isinstance(node, pss_ast.ActivitySuper):
            return ir.ActivitySuper()

        if isinstance(node, pss_ast.ActivityRepeatCount):
            count_expr = self._translate_expression(ctx, node.getCount())
            loop_var = node.getLoop_var()
            index_var = loop_var.getId() if loop_var and hasattr(loop_var, 'getId') else None
            body_stmts = self._translate_activity_stmts(ctx, _activity_body_children(node.getBody()))
            return ir.ActivityRepeat(count=count_expr, index_var=index_var, body=body_stmts)

        if isinstance(node, pss_ast.ActivityRepeatWhile):
            cond_expr = self._translate_expression(ctx, node.getCond())
            body_stmts = self._translate_activity_stmts(ctx, _activity_body_children(node.getBody()))
            return ir.ActivityDoWhile(condition=cond_expr, body=body_stmts)

        if isinstance(node, pss_ast.ActivityForeach):
            it_id = node.getIt_id()
            iterator = it_id.getId() if it_id else '_item'
            idx_id = node.getIdx_id()
            index_var = idx_id.getId() if idx_id else None
            target_expr = self._translate_expression(ctx, node.getTarget())
            body_stmts = self._translate_activity_stmts(ctx, _activity_body_children(node.getBody()))
            return ir.ActivityForeach(
                iterator=iterator, collection=target_expr,
                index_var=index_var, body=body_stmts,
            )

        if isinstance(node, pss_ast.ActivityIfElse):
            cond_expr = self._translate_expression(ctx, node.getCond())
            true_s = node.getTrue_s()
            false_s = node.getFalse_s()
            if_body: List[ir.ActivityStmt] = []
            else_body: List[ir.ActivityStmt] = []
            if true_s:
                s = self._translate_activity_stmt(ctx, true_s)
                if s:
                    if hasattr(s, 'stmts'):
                        if_body.extend(s.stmts)
                    else:
                        if_body.append(s)
            if false_s:
                s = self._translate_activity_stmt(ctx, false_s)
                if s:
                    if hasattr(s, 'stmts'):
                        else_body.extend(s.stmts)
                    else:
                        else_body.append(s)
            return ir.ActivityIfElse(condition=cond_expr, if_body=if_body, else_body=else_body)

        if isinstance(node, pss_ast.ActivitySelect):
            branches: List[ir.SelectBranch] = []
            for bi in range(node.numBranches()):
                b = node.getBranche(bi)
                if b is None:
                    continue
                guard = self._translate_expression(ctx, b.getGuard()) if b.getGuard() else None
                weight = self._translate_expression(ctx, b.getWeight()) if b.getWeight() else None
                body = b.getBody()
                body_stmts: List[ir.ActivityStmt] = []
                if body:
                    s = self._translate_activity_stmt(ctx, body)
                    if s:
                        if hasattr(s, 'stmts'):
                            body_stmts.extend(s.stmts)
                        else:
                            body_stmts.append(s)
                branches.append(ir.SelectBranch(guard=guard, weight=weight, body=body_stmts))
            return ir.ActivitySelect(branches=branches)

        if isinstance(node, pss_ast.ActivityReplicate):
            count_expr = self._translate_expression(ctx, node.getCount())
            loop_var = node.getLoop_var()
            index_var = loop_var.getId() if loop_var and hasattr(loop_var, 'getId') else None
            body_stmts = self._translate_activity_stmts(ctx, _activity_body_children(node.getBody()))
            return ir.ActivityReplicate(count=count_expr, index_var=index_var, body=body_stmts)

        if isinstance(node, pss_ast.ActivityMatch):
            cond_expr = self._translate_expression(ctx, node.getCond())
            cases: List[ir.MatchCase] = []
            for ci in range(node.numChoices()):
                choice = node.getChoice(ci)
                is_default = bool(choice.getIs_default())
                if is_default:
                    pattern = None
                else:
                    # Translate ExprOpenRangeList -> ExprRangeList
                    pattern = self._translate_open_range_list(ctx, choice.getCond())
                body = choice.getBody()
                body_stmts = self._translate_activity_stmts(
                    ctx, _activity_body_children(body))
                cases.append(ir.MatchCase(pattern=pattern, body=body_stmts))
            return ir.ActivityMatch(subject=cond_expr, cases=cases)

        if isinstance(node, pss_ast.ActivityConstraint):
            exprs: List[ir.Expr] = []
            c = node.getConstraint()
            if c is not None:
                stmts: List[ir.Stmt] = []
                self._collect_constraint_stmt(ctx, c, stmts)
                for s in stmts:
                    if isinstance(s, ir.StmtExpr):
                        exprs.append(s.expr)
            return ir.ActivityConstraint(constraints=exprs)

        if isinstance(node, pss_ast.ActivityBindStmt):
            # Translate the LHS (ExprHierarchicalId -> ExprAttribute chain)
            lhs_expr = self._hier_id_to_expr(node.getLhs())
            # Translate each RHS; emit one ActivityBind per RHS item
            if node.numRhs() == 0:
                return None
            if node.numRhs() == 1:
                rhs_expr = self._hier_id_to_expr(node.getRh(0))
                return ir.ActivityBind(src=lhs_expr, dst=rhs_expr)
            # Multiple RHS: wrap in a sequence block
            binds = []
            for i in range(node.numRhs()):
                rhs_expr = self._hier_id_to_expr(node.getRh(i))
                binds.append(ir.ActivityBind(src=lhs_expr, dst=rhs_expr))
            return ir.ActivitySequenceBlock(stmts=binds)

        if self.debug:
            self.logger.debug(f"Unhandled activity stmt type: {type(node).__name__}")
        return None

    def _translate_handle_traversal(
        self,
        ctx: 'AstToIrContext',
        node: 'pss_ast.ActivityActionHandleTraversal',
    ) -> Optional['ir.ActivityTraversal']:
        """Extract handle name from ExprRefPathContext and build ActivityTraversal."""
        target = node.getTarget()
        hier_id = target.getHier_id()
        parts: List[str] = []
        for i in range(hier_id.numElems()):
            elem = hier_id.getElem(i)
            if elem:
                id_obj = elem.getId()
                if id_obj and hasattr(id_obj, 'getId'):
                    parts.append(id_obj.getId())
        handle = '.'.join(parts) if parts else None
        if handle is None:
            return None
        inline_constraints = self._extract_inline_constraints(ctx, node)
        return ir.ActivityTraversal(handle=handle, inline_constraints=inline_constraints)

    def _translate_type_traversal(
        self,
        ctx: 'AstToIrContext',
        node: 'pss_ast.ActivityActionTypeTraversal',
    ) -> 'ir.ActivityAnonTraversal':
        """Extract action type name and optional label; build ActivityAnonTraversal."""
        target = node.getTarget()
        type_id = target.getType_id()
        parts: List[str] = []
        for i in range(type_id.numElems()):
            elem = type_id.getElem(i)
            if elem:
                id_obj = elem.getId()
                if hasattr(id_obj, 'getId'):
                    parts.append(id_obj.getId())
                elif hasattr(elem, 'getId'):
                    raw = elem.getId()
                    if hasattr(raw, 'getId'):
                        parts.append(raw.getId())
        action_type = '::'.join(parts) if parts else ''

        label = None
        label_node = node.getLabel()
        if label_node:
            label = label_node.getId() if hasattr(label_node, 'getId') else str(label_node)

        inline_constraints = self._extract_inline_constraints(ctx, node)
        # WI-6: detect and strip ``comp == expr`` from inline constraints.
        # PSS allows ``do T with comp == target;`` to route the traversal to a
        # specific component instance.  Extract it as comp_expr so the activity
        # runner can pass it as a comp_override to _traverse.
        comp_expr, filtered = self._extract_comp_expr(inline_constraints)
        return ir.ActivityAnonTraversal(
            action_type=action_type,
            label=label,
            inline_constraints=filtered,
            comp_expr=comp_expr,
        )

    def _extract_inline_constraints(self, ctx, node) -> list:
        """Extract `with` constraint expressions from a traversal node.

        PSS supports two forms:
          block:  do T with { expr1; expr2; }   -> ConstraintScope with numConstraints()
          single: do T with expr;               -> ConstraintStmtExpr with getExpr()
        """
        with_c = node.getWith_c() if hasattr(node, 'getWith_c') else None
        if not with_c:
            return []
        results = []
        # Block form: constraint scope containing multiple items
        if hasattr(with_c, 'numConstraints'):
            for ci in range(with_c.numConstraints()):
                cs = with_c.getConstraint(ci)
                if cs is None:
                    continue
                stmts: list = []
                self._collect_constraint_stmt(ctx, cs, stmts)
                for s in stmts:
                    if isinstance(s, ir.StmtExpr):
                        results.append(s.expr)
        # Single-expression form: do T with expr; -> ConstraintStmtExpr
        elif hasattr(with_c, 'getExpr'):
            expr_node = with_c.getExpr()
            if expr_node is not None:
                expr_ir = self._translate_expression(ctx, expr_node)
                if expr_ir is not None:
                    results.append(expr_ir)
        return results


    def _extract_comp_expr(self, constraints: list):
        """Separate a ``comp == expr`` equality from other inline constraints.

        Returns ``(comp_expr, remaining)`` where *comp_expr* is the RHS of the
        ``comp == <rhs>`` expression (or ``None`` if not present), and
        *remaining* is the list without that item.

        PSS ``do T with comp == target;`` produces an ExprCompare(CmpOp.Eq,
        ExprRefUnresolved("comp"), <rhs>) in the IR.
        """
        from zuspec.ir.core.expr import (
            ExprCompare, CmpOp, ExprBin, BinOp,
            ExprRefUnresolved, ExprAttribute,
        )

        def _is_comp_ref(e):
            return (isinstance(e, ExprRefUnresolved) and e.name == 'comp') or                    (isinstance(e, ExprAttribute) and e.attr == 'comp')

        comp_expr = None
        remaining = []
        for c in constraints:
            matched = False
            # Handle both ExprCompare (CmpOp.Eq) and ExprBin (BinOp.Eq)
            if isinstance(c, ExprCompare) and c.op == CmpOp.Eq:
                if _is_comp_ref(c.left):
                    comp_expr = c.right; matched = True
                elif _is_comp_ref(c.right):
                    comp_expr = c.left; matched = True
            elif isinstance(c, ExprBin) and c.op == BinOp.Eq:
                if _is_comp_ref(c.lhs):
                    comp_expr = c.rhs; matched = True
                elif _is_comp_ref(c.rhs):
                    comp_expr = c.lhs; matched = True
            if not matched:
                remaining.append(c)
        return comp_expr, remaining

    def _translate_open_range_list(self, ctx, range_list_node) -> 'ir.ExprRangeList':
        """Translate a PSS ExprOpenRangeList to an IR ExprRangeList."""
        ranges = []
        if range_list_node is None:
            return ir.ExprRangeList(ranges=[])
        for vi in range(range_list_node.numValues()):
            val = range_list_node.getValue(vi)
            lhs = val.getLhs()
            rhs = val.getRhs()
            lower = self._translate_expression(ctx, lhs) if lhs else None
            upper = self._translate_expression(ctx, rhs) if rhs else None
            if lower is not None:
                ranges.append(ir.ExprRange(lower=lower, upper=upper))
        return ir.ExprRangeList(ranges=ranges)

    def _translate_domain_range_list(self, ctx, domain_node) -> 'Optional[ir.ExprRangeList]':
        """Translate a PSS ExprDomainOpenRangeList to an IR ExprRangeList.

        Used for `rand int in [range]` domain constraint generation.
        """
        if domain_node is None:
            return None
        ranges = []
        for vi in range(domain_node.numValues()):
            val = domain_node.getValue(vi)
            lhs = val.getLhs()
            rhs = val.getRhs()
            lower = self._translate_expression(ctx, lhs) if lhs else None
            upper = self._translate_expression(ctx, rhs) if rhs else None
            if lower is not None:
                ranges.append(ir.ExprRange(lower=lower, upper=upper))
        if not ranges:
            return None
        return ir.ExprRangeList(ranges=ranges)

    def _flush_range_constraints(self, ctx: AstToIrContext, action_ir: ir.DataTypeStruct) -> None:
        """Convert pending range constraints into a constraint function and clear them."""
        if not ctx._pending_range_constraints:
            return
        body: List[ir.Stmt] = []
        for _fname, in_expr in ctx._pending_range_constraints:
            body.append(ir.StmtExpr(expr=in_expr))
        n = sum(1 for f in action_ir.functions if f.metadata.get('_is_constraint'))
        cfunc = ir.Function(
            name=f'_range_{n}',
            body=body,
            metadata={'_is_constraint': True},
        )
        action_ir.functions.append(cfunc)
        ctx._pending_range_constraints = []

    def _hier_id_to_expr(self, hier_id) -> 'ir.Expr':
        """Convert an ExprHierarchicalId to a chain of ExprAttribute nodes.

        Used for ``bind lhs rhs;`` statement LHS/RHS which are
        ``ExprMemberPathElem`` chains (e.g. ``p.out_data`` -> ``self.p.out_data``).
        """
        result: ir.Expr = ir.TypeExprRefSelf()
        if hier_id is None:
            return result
        for i in range(hier_id.numElems()):
            elem = hier_id.getElem(i)
            id_obj = elem.getId() if hasattr(elem, 'getId') else None
            if id_obj is None:
                continue
            name = id_obj.getId() if hasattr(id_obj, 'getId') else str(id_obj)
            result = ir.ExprAttribute(value=result, attr=name)
        return result

    def _translate_join_spec(self, join_spec) -> Optional['ir.JoinSpec']:
        """Convert a PSS ActivityJoinSpec to IR JoinSpec."""
        if join_spec is None:
            return None
        if isinstance(join_spec, pss_ast.ActivityJoinSpecBranch):
            return ir.JoinSpec(kind='branch')
        if isinstance(join_spec, pss_ast.ActivityJoinSpecFirst):
            count = self._translate_expression(None, join_spec.getCount()) if hasattr(join_spec, 'getCount') else None
            return ir.JoinSpec(kind='first', count=count)
        if isinstance(join_spec, pss_ast.ActivityJoinSpecNone):
            return ir.JoinSpec(kind='none')
        if isinstance(join_spec, pss_ast.ActivityJoinSpecSelect):
            count = self._translate_expression(None, join_spec.getCount()) if hasattr(join_spec, 'getCount') else None
            return ir.JoinSpec(kind='select', count=count)
        return ir.JoinSpec(kind='all')

    def _translate_field_ref(self, ctx: AstToIrContext, field_ref: pss_ast.FieldRef) -> Optional[ir.Field]:
        """Translate a PSS FieldRef (input/output flow-object reference) to IR Field."""
        name_node = field_ref.getName()
        field_name = name_node.getId() if hasattr(name_node, 'getId') else str(name_node)
        is_input = field_ref.getIs_input()
        flow_type = self._translate_data_type(ctx, field_ref.getType())
        kind = ir.FieldKind.Input if is_input else ir.FieldKind.Output
        return ir.Field(name=field_name, datatype=flow_type, kind=kind)

    def _translate_field_claim(self, ctx: 'AstToIrContext', field_claim: 'pss_ast.FieldClaim') -> Optional['ir.Field']:
        """Translate a PSS FieldClaim (lock/share resource reference) to an IR Field.

        ``lock T name;`` -> Field(kind=FieldKind.Lock)
        ``share T name;`` -> Field(kind=FieldKind.Share)
        """
        name_node = field_claim.getName()
        field_name = name_node.getId() if hasattr(name_node, 'getId') else str(name_node)
        resource_type = self._translate_data_type(ctx, field_claim.getType())
        kind = ir.FieldKind.Lock if field_claim.getIs_lock() else ir.FieldKind.Share
        return ir.Field(name=field_name, datatype=resource_type, kind=kind)

    def _translate_struct(self, ctx: AstToIrContext, struct: pss_ast.Struct, namespace_prefix: str = "") -> ir.DataTypeStruct:
        """Translate a PSS struct to IR DataTypeStruct

        Args:
            ctx: Translation context
            struct: PSS struct AST node
            namespace_prefix: Namespace prefix for package-scoped types

        Returns:
            IR DataTypeStruct
        """
        # Extract struct name
        name_node = struct.getName()
        if isinstance(name_node, pss_ast.ExprId):
            struct_name = name_node.getId()
        else:
            struct_name = str(name_node)

        qualified_name = f"{namespace_prefix}{struct_name}"

        if self.debug:
            self.logger.debug(f"Translating struct: {qualified_name}")

        # Create IR struct
        struct_ir = ir.DataTypeStruct(name=qualified_name, super=None)

        # Set flow_kind from StructKind (buffer/stream/state/resource)
        if hasattr(struct, 'getKind'):
            kind = struct.getKind()
            _flow_kind_map = {
                pss_ast.StructKind.Buffer:   "buffer",
                pss_ast.StructKind.Stream:   "stream",
                pss_ast.StructKind.State:    "state",
                pss_ast.StructKind.Resource: "resource",
            }
            struct_ir.flow_kind = _flow_kind_map.get(kind)

        # Register in type map
        ctx.add_type(qualified_name, struct_ir)
        if namespace_prefix:
            ctx.add_type(struct_name, struct_ir)

        # Push scope and type-chain name for annotation matching
        ctx.push_scope(struct_ir)
        self._type_chain_stack.append(struct_name)

        # Handle inheritance
        super_t = struct.getSuper_t()
        if super_t is not None:
            super_name = self._type_identifier_name(super_t)
            if super_name:
                struct_ir.super = ir.DataTypeRef(ref_name=super_name)

        # Translate children (fields, exec blocks, and constraints)
        for child in struct.children():
            if child is None:
                continue

            if isinstance(child, pss_ast.Field):
                field = self._translate_field(ctx, child)
                if field:
                    struct_ir.fields.append(field)
            elif isinstance(child, pss_ast.ExecBlock):
                kind = child.getKind()
                if kind == pss_ast.ExecKind.ExecKind_PreSolve:
                    stmts = self._translate_exec_scope(ctx, child)
                    func = ir.Function(name='pre_solve', is_async=False, body=stmts)
                    struct_ir.functions.append(func)
                elif kind == pss_ast.ExecKind.ExecKind_PostSolve:
                    stmts = self._translate_exec_scope(ctx, child)
                    func = ir.Function(name='post_solve', is_async=False, body=stmts)
                    struct_ir.functions.append(func)
            elif isinstance(child, pss_ast.ConstraintBlock):
                constraint_func = self._translate_constraint_block(ctx, child, struct_ir)
                if constraint_func:
                    struct_ir.functions.append(constraint_func)

        # Inject forall constraints from PssAnnotation side-channel
        current_chain = list(self._type_chain_stack)
        for ann in self._annotations:
            if ann.type_chain == current_chain:
                if ann.kind == 'forall':
                    self._inject_forall_constraint(ctx, struct_ir, ann)

        # Pop type-chain name for struct
        self._type_chain_stack.pop()

        # Tag state structs that use the `initial` built-in in a constraint implication.
        # The pre-processor injects `bool initial;` so the linker accepts `initial`,
        # and now we record whether any constraint body references it.
        if struct_ir.flow_kind == "state":
            struct_ir.has_initial_constraint = self._struct_references_initial(struct_ir)
            # Ensure `initial` field defaults to True (it is set False at runtime for
            # non-initial states; True is the correct starting value per PSS LRM).
            for f in struct_ir.fields:
                if f.name == "initial":
                    f.initial_value = ir.ExprConstant(value=1)
                    break

        # Pop scope
        ctx.pop_scope()

        return struct_ir

    def _struct_references_initial(self, struct_ir) -> bool:
        """Return True if any constraint in this state struct references the `initial` field.

        The pre-processor injects `bool initial;` into state struct bodies, so
        the constraint `constraint initial -> val == X;` becomes translatable.
        We check whether any constraint function body uses `initial` as a field ref.
        """
        from zuspec.ir.core.expr import ExprAttribute, TypeExprRefSelf, ExprRefUnresolved
        for fn in struct_ir.functions:
            if not fn.metadata.get('_is_constraint'):
                continue
            for stmt in fn.body:
                if self._expr_has_name(stmt, 'initial'):
                    return True
        return False

    def _expr_has_name(self, node, name: str) -> bool:
        """Recursively check whether any ExprAttribute/ExprRefUnresolved references `name`."""
        from zuspec.ir.core import expr as ir_expr
        if node is None:
            return False
        if isinstance(node, ir_expr.ExprAttribute) and node.attr == name:
            return True
        if isinstance(node, ir_expr.ExprRefUnresolved) and node.name == name:
            return True
        # Recurse into scalar child attributes
        for attr in ('expr', 'lhs', 'rhs', 'cond', 'value', 'func',
                     'test', 'body', 'orelse', 'operand', 'val'):
            child = getattr(node, attr, None)
            if child is not None and not isinstance(child, (str, int, float, bool)):
                if self._expr_has_name(child, name):
                    return True
        # Recurse into list child attributes
        for attr in ('stmts', 'body', 'args', 'elts', 'ranges', 'body_exprs'):
            lst = getattr(node, attr, None)
            if isinstance(lst, list):
                for item in lst:
                    if self._expr_has_name(item, name):
                        return True
        return False

    def _collect_constraint_stmt(
        self,
        ctx: AstToIrContext,
        stmt,
        body: List[ir.Stmt],
    ) -> None:
        """Translate a single PSS constraint statement and append IR stmts to body."""
        if isinstance(stmt, pss_ast.ConstraintStmtExpr):
            expr_node = stmt.getExpr()
            if expr_node is None:
                return
            ir_expr = self._translate_expression(ctx, expr_node)
            if ir_expr is not None:
                body.append(ir.StmtExpr(expr=ir_expr))

        elif isinstance(stmt, pss_ast.ConstraintStmtImplication):
            cond_node = stmt.getCond()
            if cond_node is None:
                return
            cond_expr = self._translate_expression(ctx, cond_node)
            if cond_expr is None:
                return
            for j in range(stmt.numConstraints()):
                sub = stmt.getConstraint(j)
                if sub and isinstance(sub, pss_ast.ConstraintStmtExpr):
                    sub_expr_node = sub.getExpr()
                    if sub_expr_node is not None:
                        sub_ir = self._translate_expression(ctx, sub_expr_node)
                        if sub_ir is not None:
                            body.append(ir.StmtExpr(expr=ir.ExprCall(
                                func=ir.ExprRefUnresolved(name='implies'),
                                args=[cond_expr, sub_ir],
                            )))

        elif isinstance(stmt, pss_ast.ConstraintStmtIf):
            cond_node = stmt.getCond()
            if cond_node is None:
                return
            cond_expr = self._translate_expression(ctx, cond_node)
            if cond_expr is None:
                return
            true_stmts: List[ir.Stmt] = []
            true_c = stmt.getTrue_c()
            if true_c is not None:
                for j in range(true_c.numConstraints()):
                    sub = true_c.getConstraint(j)
                    if sub and isinstance(sub, pss_ast.ConstraintStmtExpr):
                        sub_expr_node = sub.getExpr()
                        if sub_expr_node is not None:
                            sub_ir = self._translate_expression(ctx, sub_expr_node)
                            if sub_ir is not None:
                                true_stmts.append(ir.StmtExpr(expr=sub_ir))
            false_stmts: List[ir.Stmt] = []
            false_c = stmt.getFalse_c()
            if false_c is not None:
                for j in range(false_c.numConstraints()):
                    sub = false_c.getConstraint(j)
                    if sub and isinstance(sub, pss_ast.ConstraintStmtExpr):
                        sub_expr_node = sub.getExpr()
                        if sub_expr_node is not None:
                            sub_ir = self._translate_expression(ctx, sub_expr_node)
                            if sub_ir is not None:
                                false_stmts.append(ir.StmtExpr(expr=sub_ir))
            if true_stmts:
                body.append(ir.StmtIf(
                    test=cond_expr,
                    body=true_stmts,
                    orelse=false_stmts,
                ))

        # ConstraintStmtForeach is a subclass of ConstraintScope, so it MUST be
        # checked before the generic ConstraintScope branch.
        elif isinstance(stmt, pss_ast.ConstraintStmtForeach):
            it_node = stmt.getIt()   # element-style: foreach (e : data)
            idx_node = stmt.getIdx() # index-style:   foreach (data[i])
            if it_node is not None:
                var_name_obj = it_node.getName()
            elif idx_node is not None:
                var_name_obj = idx_node.getName()
            else:
                return
            if var_name_obj is None:
                return
            iter_var_name = (var_name_obj.getId()
                             if hasattr(var_name_obj, 'getId') else str(var_name_obj))

            collection_expr_node = stmt.getExpr()
            if collection_expr_node is None:
                return
            collection_ir = self._translate_expression(ctx, collection_expr_node)
            if collection_ir is None:
                return

            ctx.local_vars.add(iter_var_name)
            foreach_body: List[ir.Stmt] = []
            for j in range(stmt.numConstraints()):
                sub = stmt.getConstraint(j)
                if sub is not None:
                    self._collect_constraint_stmt(ctx, sub, foreach_body)
            ctx.local_vars.discard(iter_var_name)

            if foreach_body:
                body.append(ir.StmtForeach(
                    target=ir.ExprRefLocal(name=iter_var_name),
                    iter=collection_ir,
                    body=foreach_body,
                ))

        elif isinstance(stmt, pss_ast.ConstraintScope):
            for j in range(stmt.numConstraints()):
                sub = stmt.getConstraint(j)
                if sub is not None:
                    self._collect_constraint_stmt(ctx, sub, body)

        elif isinstance(stmt, pss_ast.ConstraintStmtUnique):
            var_names = []
            for j in range(stmt.numList()):
                hid = stmt.getList(j)
                if hid is not None and hid.numElems() > 0:
                    # Take the last element as the field name
                    last = hid.getElem(hid.numElems() - 1)
                    if hasattr(last, 'getId'):
                        id_obj = last.getId()
                        name = id_obj.getId() if isinstance(id_obj, pss_ast.ExprId) else str(id_obj)
                    else:
                        name = str(last)
                    var_names.append(name)
            if len(var_names) >= 2:
                body.append(ir.StmtUnique(vars=var_names))

        else:
            if self.debug:
                self.logger.debug(
                    f"Unsupported constraint stmt type: {type(stmt).__name__}; skipping"
                )

    def _translate_constraint_block(
        self,
        ctx: AstToIrContext,
        constraint_block: pss_ast.ConstraintBlock,
        owner: ir.DataTypeStruct,
    ) -> Optional[ir.Function]:
        """Translate a PSS ConstraintBlock to an IR Function marked as a constraint.

        Creates an `ir.Function` with `metadata={'_is_constraint': True}` whose body
        contains `StmtExpr` nodes for each translatable constraint statement.

        Args:
            ctx: Translation context
            constraint_block: PSS ConstraintBlock AST node
            owner: The enclosing struct/action IR type (used for auto-naming)

        Returns:
            IR Function if any constraint statements were translated, else None
        """
        # Determine the constraint function name
        raw_name = constraint_block.getName() if hasattr(constraint_block, 'getName') else None
        if raw_name:
            func_name = raw_name
        else:
            # Auto-generate a unique name based on position in owner's function list
            idx = sum(1 for f in owner.functions if f.metadata.get('_is_constraint'))
            func_name = f'_c_{idx}'

        # Detect soft/default constraints (PSS `constraint default ...`)
        is_soft = bool(getattr(constraint_block, 'getIs_dynamic', lambda: False)())

        body: List[ir.Stmt] = []

        for i in range(constraint_block.numConstraints()):
            stmt = constraint_block.getConstraint(i)
            if stmt is None:
                continue

            if isinstance(stmt, pss_ast.ConstraintStmtForeach):
                # foreach has special context management (iterator variable).
                # Element-style: foreach (e : data)  → getIt() returns the var
                # Index-style:   foreach (data[i])   → getIdx() returns the var
                it_node = stmt.getIt()
                idx_node = stmt.getIdx()
                if it_node is not None:
                    var_name_obj = it_node.getName()
                elif idx_node is not None:
                    var_name_obj = idx_node.getName()
                else:
                    continue
                if var_name_obj is None:
                    continue
                iter_var_name = var_name_obj.getId() if hasattr(var_name_obj, 'getId') else str(var_name_obj)

                collection_expr_node = stmt.getExpr()
                if collection_expr_node is None:
                    continue
                collection_ir = self._translate_expression(ctx, collection_expr_node)
                if collection_ir is None:
                    continue

                ctx.local_vars.add(iter_var_name)
                foreach_body: List[ir.Stmt] = []
                for j in range(stmt.numConstraints()):
                    sub = stmt.getConstraint(j)
                    if sub is not None:
                        self._collect_constraint_stmt(ctx, sub, foreach_body)
                ctx.local_vars.discard(iter_var_name)

                if foreach_body:
                    body.append(ir.StmtForeach(
                        target=ir.ExprRefLocal(name=iter_var_name),
                        iter=collection_ir,
                        body=foreach_body,
                    ))
            else:
                self._collect_constraint_stmt(ctx, stmt, body)

        if not body:
            return None

        meta = {'_is_constraint': True}
        if is_soft:
            meta['is_soft'] = True
        return ir.Function(
            name=func_name,
            is_async=False,
            body=body,
            metadata=meta,
        )

    def _translate_enum(self, ctx: AstToIrContext, enum_decl: pss_ast.EnumDecl) -> ir.DataTypeEnum:
        """Translate a PSS enum declaration to IR DataTypeEnum.

        Assigns auto-incrementing values to items without an explicit value,
        following PSS §7.5 semantics (first item defaults to 0).

        Args:
            ctx: Translation context
            enum_decl: PSS EnumDecl AST node

        Returns:
            IR DataTypeEnum registered in ctx.type_map
        """
        name_node = enum_decl.getName()
        enum_name = name_node.getId() if hasattr(name_node, 'getId') else str(name_node)

        if self.debug:
            self.logger.debug(f"Translating enum: {enum_name}")

        items: dict = {}
        next_val = 0
        for i in range(enum_decl.numItems()):
            item = enum_decl.getItem(i)
            item_name_node = item.getName()
            item_name = item_name_node.getId() if hasattr(item_name_node, 'getId') else str(item_name_node)
            val_node = item.getValue()
            if val_node is not None and hasattr(val_node, 'getValue'):
                next_val = val_node.getValue()
            items[item_name] = next_val
            next_val += 1

        enum_ir = ir.DataTypeEnum(name=enum_name, items=items)
        ctx.add_type(enum_name, enum_ir)
        return enum_ir

    def _translate_typedef(self, ctx: AstToIrContext, typedef_decl: pss_ast.TypedefDeclaration) -> Optional[ir.DataType]:
        """Translate a PSS typedef declaration by registering a type alias.

        Args:
            ctx: Translation context
            typedef_decl: PSS TypedefDeclaration AST node

        Returns:
            The aliased IR DataType (also registered under the alias name)
        """
        name_node = typedef_decl.getName()
        alias_name = name_node.getId() if hasattr(name_node, 'getId') else str(name_node)

        if self.debug:
            self.logger.debug(f"Translating typedef: {alias_name}")

        base_type = self._translate_data_type(ctx, typedef_decl.getType())
        if base_type is None:
            ctx.add_error(f"Failed to translate type for typedef '{alias_name}'")
            return None

        ctx.add_type(alias_name, base_type)
        return base_type

    def _translate_field(self, ctx: AstToIrContext, field: pss_ast.Field) -> Optional[ir.Field]:
        """Translate a PSS field to IR Field

        Args:
            ctx: Translation context
            field: PSS field AST node

        Returns:
            IR Field or None
        """
        # Extract field name
        name_node = field.getName()
        if isinstance(name_node, pss_ast.ExprId):
            field_name = name_node.getId()
        else:
            field_name = str(name_node)

        if self.debug:
            self.logger.debug(f"Translating field: {field_name}")

        # Get field type
        field_type = self._translate_data_type(ctx, field.getType())
        if not field_type:
            ctx.add_error(f"Failed to translate field type for {field_name}")
            return None

        # Create IR field
        rand_kind = None
        attr = field.getAttr()
        if attr & pss_ast.FieldAttr.Rand:
            rand_kind = 'rand'

        ir_field = ir.Field(
            name=field_name,
            datatype=field_type,
            kind=ir.FieldKind.Field,
            rand_kind=rand_kind,
        )

        # Extract `rand int in [range]` domain constraint (T-12).
        dtype_node = field.getType()
        if (isinstance(dtype_node, pss_ast.DataTypeInt)
                and hasattr(dtype_node, 'getIn_range')
                and dtype_node.getIn_range() is not None):
            domain = dtype_node.getIn_range()
            range_list = self._translate_domain_range_list(ctx, domain)
            if range_list is not None:
                field_ref = ir.ExprAttribute(value=ir.TypeExprRefSelf(), attr=field_name)
                in_expr = ir.ExprIn(value=field_ref, container=range_list)
                ctx._pending_range_constraints.append((field_name, in_expr))

        return ir_field

    def _translate_function(self, ctx: AstToIrContext, function) -> Optional[ir.Function]:
        """Translate a PSS function to IR Function

        Args:
            ctx: Translation context
            function: PSS FunctionDefinition AST node

        Returns:
            IR Function or None
        """
        # Get function prototype
        prototype = function.getProto()
        if not prototype:
            ctx.add_error("Function missing prototype")
            return None

        # Extract function name
        name_node = prototype.getName()
        if isinstance(name_node, pss_ast.ExprId):
            func_name = name_node.getId()
        else:
            func_name = str(name_node)

        if self.debug:
            self.logger.debug(f"Translating function: {func_name}")

        # Get return type (may be None for void)
        return_type_node = prototype.getRtype()
        return_type = None
        if return_type_node is not None:
            return_type = self._translate_data_type(ctx, return_type_node)

        # Get parameters
        params = []
        defaults = []
        vararg: Optional[ir.Arg] = None
        for i in range(prototype.numParameters()):
            param = prototype.getParameter(i)
            if param:
                # Extract param name and type
                param_name_node = param.getName()
                if isinstance(param_name_node, pss_ast.ExprId):
                    param_name = param_name_node.getId()
                else:
                    param_name = str(param_name_node)

                param_type = self._translate_data_type(ctx, param.getType())
                if param_type:
                    is_varargs = param.getIs_varargs() if hasattr(param, 'getIs_varargs') else False
                    arg_node = ir.Arg(arg=param_name, annotation=param_type)
                    if is_varargs:
                        vararg = arg_node
                    else:
                        params.append(arg_node)
                        dflt_node = param.getDflt() if hasattr(param, 'getDflt') else None
                        if dflt_node is not None:
                            dflt_ir = self._translate_expression(ctx, dflt_node)
                            if dflt_ir is not None:
                                defaults.append(dflt_ir)

        # Create Arguments structure
        args = ir.Arguments(args=params, vararg=vararg, defaults=defaults)

        # Translate function body
        body_stmts = []
        body = function.getBody()
        if body:
            body_stmts = self._translate_exec_scope(ctx, body)

        # Create IR function
        is_pure = prototype.getIs_pure() if hasattr(prototype, 'getIs_pure') else False
        is_solve = bool(prototype.getIs_solve()) if hasattr(prototype, 'getIs_solve') else False
        ir_func = ir.Function(
            name=func_name,
            args=args,
            body=body_stmts,
            returns=return_type,
            is_async=False,
            is_invariant=bool(is_pure),
            is_solve=is_solve,
        )

        return ir_func

    def _translate_exec_scope(self, ctx: AstToIrContext, exec_scope) -> List[ir.Stmt]:
        """Translate an execution scope (function body)

        Args:
            ctx: Translation context
            exec_scope: PSS ExecScope node

        Returns:
            List of IR statements
        """
        stmts = []

        for child in exec_scope.children():
            if child is None:
                continue
            stmt = self._translate_statement(ctx, child)
            if stmt:
                stmts.append(stmt)

        return stmts

    def _translate_statement(self, ctx: AstToIrContext, stmt_node: Any) -> Optional[ir.Stmt]:
        """Translate a statement node to IR

        Args:
            ctx: Translation context
            stmt_node: PSS statement AST node

        Returns:
            IR statement or None
        """
        if isinstance(stmt_node, pss_ast.ProceduralStmtReturn):
            return self._translate_stmt_return(ctx, stmt_node)
        elif isinstance(stmt_node, pss_ast.ProceduralStmtDataDeclaration):
            return self._translate_stmt_declaration(ctx, stmt_node)
        elif isinstance(stmt_node, pss_ast.ProceduralStmtAssignment):
            return self._translate_stmt_assignment(ctx, stmt_node)
        elif isinstance(stmt_node, pss_ast.ProceduralStmtIfElse):
            return self._translate_stmt_if(ctx, stmt_node)
        elif isinstance(stmt_node, pss_ast.ProceduralStmtWhile):
            return self._translate_stmt_while(ctx, stmt_node)
        elif isinstance(stmt_node, pss_ast.ProceduralStmtRepeat):
            return self._translate_stmt_repeat(ctx, stmt_node)
        elif isinstance(stmt_node, pss_ast.ProceduralStmtRepeatWhile):
            return self._translate_stmt_repeat_while(ctx, stmt_node)
        elif isinstance(stmt_node, pss_ast.ProceduralStmtBreak):
            return ir.StmtBreak()
        elif isinstance(stmt_node, pss_ast.ProceduralStmtContinue):
            return ir.StmtContinue()
        elif isinstance(stmt_node, pss_ast.ProceduralStmtExpr):
            expr_node = stmt_node.getExpr()
            if expr_node is not None:
                ir_expr = self._translate_expression(ctx, expr_node)
                if ir_expr is not None:
                    return ir.StmtExpr(expr=ir_expr)
            return None
        elif isinstance(stmt_node, pss_ast.ProceduralStmtYield):
            return ir.StmtYield()
        elif isinstance(stmt_node, pss_ast.ProceduralStmtForeach):
            return self._translate_stmt_foreach(ctx, stmt_node)
        elif isinstance(stmt_node, pss_ast.ProceduralStmtMatch):
            return self._translate_stmt_match(ctx, stmt_node)
        elif isinstance(stmt_node, pss_ast.ProceduralStmtFunctionCall):
            return self._translate_stmt_function_call(ctx, stmt_node)
        else:
            if self.debug:
                self.logger.debug(f"Unsupported statement type: {type(stmt_node).__name__}")
            return None

    def _translate_stmt_return(self, ctx: AstToIrContext, stmt: pss_ast.ProceduralStmtReturn) -> ir.StmtReturn:
        """Translate a return statement"""
        expr_node = stmt.getExpr()
        value = None
        if expr_node:
            value = self._translate_expression(ctx, expr_node)
        return ir.StmtReturn(value=value)

    def _translate_stmt_declaration(self, ctx: AstToIrContext, stmt: pss_ast.ProceduralStmtDataDeclaration) -> ir.StmtAnnAssign:
        """Translate a variable declaration statement"""
        # Get variable name
        name_node = stmt.getName()
        if isinstance(name_node, pss_ast.ExprId):
            var_name = name_node.getId()
        else:
            var_name = str(name_node)

        # Get variable type
        var_type = self._translate_data_type(ctx, stmt.getDatatype())

        # Get initial value (if any)
        init_expr = stmt.getInit()
        value = None
        if init_expr:
            value = self._translate_expression(ctx, init_expr)

        # Create name expression for target and register as local variable
        target = ir.ExprRefLocal(name=var_name)
        ctx.local_vars.add(var_name)

        return ir.StmtAnnAssign(target=target, annotation=var_type, value=value)

    def _translate_stmt_assignment(self, ctx: AstToIrContext, stmt: pss_ast.ProceduralStmtAssignment):
        """Translate an assignment or compound-assignment statement."""
        lhs = stmt.getLhs()
        target = self._translate_expression(ctx, lhs)
        rhs = stmt.getRhs()
        value = self._translate_expression(ctx, rhs)

        op = stmt.getOp()
        _aug_op_map = {
            pss_ast.AssignOp.AssignOp_PlusEq:  ir.AugOp.Add,
            pss_ast.AssignOp.AssignOp_MinusEq: ir.AugOp.Sub,
            pss_ast.AssignOp.AssignOp_ShlEq:   ir.AugOp.LShift,
            pss_ast.AssignOp.AssignOp_ShrEq:   ir.AugOp.RShift,
            pss_ast.AssignOp.AssignOp_OrEq:    ir.AugOp.BitOr,
            pss_ast.AssignOp.AssignOp_AndEq:   ir.AugOp.BitAnd,
        }
        if op in _aug_op_map:
            return ir.StmtAugAssign(target=target, op=_aug_op_map[op], value=value)
        return ir.StmtAssign(targets=[target], value=value)

    def _translate_stmt_if(self, ctx: AstToIrContext, stmt: pss_ast.ProceduralStmtIfElse) -> ir.StmtIf:
        """Translate an if / else-if / else chain into nested StmtIf nodes."""
        def _translate_body(scope):
            stmts = []
            if scope:
                for child in scope.children():
                    if child is None:
                        continue
                    s = self._translate_statement(ctx, child)
                    if s:
                        stmts.append(s)
            return stmts

        # Build the final else branch first
        else_body = _translate_body(stmt.getElse_then())

        # Walk if-then clauses from last to first, nesting each into the else of the previous
        num_clauses = stmt.numIf_then()
        result = else_body
        for i in range(num_clauses - 1, -1, -1):
            clause = stmt.getIf_then(i)
            cond = self._translate_expression(ctx, clause.getCond())
            then_body = _translate_body(clause.getBody())
            result = [ir.StmtIf(test=cond, body=then_body, orelse=result)]

        return result[0] if result else ir.StmtPass()

    def _translate_stmt_while(self, ctx: AstToIrContext, stmt) -> ir.StmtWhile:
        """Translate a while loop"""
        # Get condition
        cond = self._translate_expression(ctx, stmt.getExpr())

        # Get body
        body_scope = stmt.getBody()
        body = []
        if body_scope:
            for child in body_scope.children():
                if child is None:
                    continue
                stmt_ir = self._translate_statement(ctx, child)
                if stmt_ir:
                    body.append(stmt_ir)

        return ir.StmtWhile(test=cond, body=body)

    def _translate_stmt_repeat(self, ctx: AstToIrContext, stmt) -> ir.StmtFor:
        """Translate a repeat statement (PSS for loop)"""
        # Get count expression
        count_expr = self._translate_expression(ctx, stmt.getCount())

        # Get optional iterator variable: "repeat (i : 10)" has getIt_id() == "i"
        it_id = stmt.getIt_id()
        target = None
        iter_name = None
        if it_id is not None:
            iter_name = it_id.getId() if hasattr(it_id, 'getId') else str(it_id)
            target = ir.ExprRefLocal(name=iter_name)
            ctx.local_vars.add(iter_name)  # so body references become ExprRefLocal

        # Get body
        body_scope = stmt.getBody()
        body = []
        if body_scope:
            for child in body_scope.children():
                if child is None:
                    continue
                stmt_ir = self._translate_statement(ctx, child)
                if stmt_ir:
                    body.append(stmt_ir)

        if iter_name is not None:
            ctx.local_vars.discard(iter_name)

        return ir.StmtFor(target=target, iter=count_expr, body=body)

    def _translate_stmt_repeat_while(self, ctx: AstToIrContext, stmt) -> ir.StmtRepeatWhile:
        """Translate a repeat-while statement (PSS do-while: body executes at least once)."""
        cond = self._translate_expression(ctx, stmt.getExpr())

        body_scope = stmt.getBody()
        body = []
        if body_scope:
            for child in body_scope.children():
                if child is None:
                    continue
                stmt_ir = self._translate_statement(ctx, child)
                if stmt_ir:
                    body.append(stmt_ir)

        return ir.StmtRepeatWhile(condition=cond, body=body)

    def _translate_stmt_foreach(self, ctx: AstToIrContext, stmt: pss_ast.ProceduralStmtForeach) -> Optional[ir.StmtForeach]:
        """Translate a foreach statement: foreach (e : items) { ... }"""
        it_id = stmt.getIt_id()
        idx_id = stmt.getIdx_id()
        path = stmt.getPath()

        if it_id is None or path is None:
            if self.debug:
                self.logger.debug("foreach: missing iterator or path")
            return None

        iter_name = it_id.getId() if hasattr(it_id, 'getId') else str(it_id)
        target = ir.ExprRefLocal(name=iter_name)

        collection_ir = self._translate_expression(ctx, path)
        if collection_ir is None:
            return None

        index_var = None
        idx_name = None
        if idx_id is not None:
            idx_name = idx_id.getId() if hasattr(idx_id, 'getId') else str(idx_id)
            index_var = ir.ExprRefLocal(name=idx_name)

        # Register loop variables so body references resolve to ExprRefLocal
        ctx.local_vars.add(iter_name)
        if idx_name is not None:
            ctx.local_vars.add(idx_name)

        body_scope = stmt.getBody()
        body = []
        if body_scope:
            for child in body_scope.children():
                if child is None:
                    continue
                stmt_ir = self._translate_statement(ctx, child)
                if stmt_ir:
                    body.append(stmt_ir)

        ctx.local_vars.discard(iter_name)
        if idx_name is not None:
            ctx.local_vars.discard(idx_name)

        return ir.StmtForeach(target=target, iter=collection_ir, body=body, index_var=index_var)

    def _translate_stmt_match(self, ctx: AstToIrContext, stmt: pss_ast.ProceduralStmtMatch) -> Optional[ir.StmtMatch]:
        """Translate a match statement: match (expr) { [val]: { ... } default: { ... } }"""
        subject_node = stmt.getExpr()
        if subject_node is None:
            return None
        subject = self._translate_expression(ctx, subject_node)
        if subject is None:
            return None

        cases = []
        for i in range(stmt.numChoices()):
            choice = stmt.getChoice(i)
            if choice is None:
                continue
            body_scope = choice.getBody()
            body = []
            if body_scope:
                for child in body_scope.children():
                    if child is None:
                        continue
                    stmt_ir = self._translate_statement(ctx, child)
                    if stmt_ir:
                        body.append(stmt_ir)

            if choice.getIs_default():
                pattern = ir.PatternAs(pattern=None, name="_")
            else:
                cond_node = choice.getCond()
                if cond_node is not None:
                    cond_ir = self._translate_expression(ctx, cond_node)
                    pattern = ir.PatternValue(value=cond_ir) if cond_ir else ir.PatternAs(pattern=None, name="_")
                else:
                    pattern = ir.PatternAs(pattern=None, name="_")

            cases.append(ir.StmtMatchCase(pattern=pattern, body=body))

        return ir.StmtMatch(subject=subject, cases=cases)

    def _translate_stmt_function_call(self, ctx: AstToIrContext, stmt: pss_ast.ProceduralStmtFunctionCall) -> Optional[ir.StmtExpr]:
        """Translate a standalone function call statement."""
        # Build prefix (e.g. component path) + function name
        prefix = stmt.getPrefix()
        fn_name_parts = []
        if prefix:
            hier = prefix.getHier_id() if hasattr(prefix, 'getHier_id') else None
            if hier:
                for i in range(hier.numElems()):
                    e = hier.getElem(i)
                    fn_name_parts.append(e.getId().getId())

        args = []
        for i in range(stmt.numParams()):
            param = stmt.getParam(i)
            arg_ir = self._translate_expression(ctx, param)
            if arg_ir is not None:
                args.append(arg_ir)

        if fn_name_parts:
            func: ir.Expr = ir.TypeExprRefSelf()
            for part in fn_name_parts:
                func = ir.ExprAttribute(value=func, attr=part)
        else:
            # bare function — use prefix's params or name from getParams
            params_node = stmt.getParams()
            fn_id = params_node.getPrefix() if params_node and hasattr(params_node, 'getPrefix') else None
            name = fn_id.getId() if fn_id and hasattr(fn_id, 'getId') else "unknown"
            func = ir.ExprRefUnresolved(name=name)

        return ir.StmtExpr(expr=ir.ExprCall(func=func, args=args))

    def _translate_expression(self, ctx: AstToIrContext, expr_node: Any) -> Optional[ir.Expr]:
        """Translate an expression node to IR

        Args:
            ctx: Translation context
            expr_node: PSS expression AST node

        Returns:
            IR expression or None
        """
        if isinstance(expr_node, (pss_ast.ExprNumber, pss_ast.ExprSignedNumber, pss_ast.ExprUnsignedNumber)):
            return self._translate_expr_number(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprString):
            return self._translate_expr_string(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprBool):
            return self._translate_expr_bool(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprBin):
            return self._translate_expr_bin(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprUnary):
            return self._translate_expr_unary(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprCond):
            return self._translate_expr_cond(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprRefPathContext):
            return self._translate_expr_ref(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprCast):
            return self._translate_expr_cast(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprSubscript):
            return self._translate_expr_subscript(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprBitSlice):
            return self._translate_expr_bitslice(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprSubstring):
            return self._translate_expr_substring(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprAggrList):
            return self._translate_expr_aggr_list(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprAggrMap):
            return self._translate_expr_aggr_map(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprAggrStruct):
            return self._translate_expr_aggr_struct(ctx, expr_node)
        elif isinstance(expr_node, pss_ast.ExprAggrEmpty):
            return ir.ExprList(elts=[])
        elif isinstance(expr_node, pss_ast.ExprNull):
            return ir.ExprNull()
        elif isinstance(expr_node, pss_ast.ExprIn):
            return self._translate_expr_in(ctx, expr_node)
        else:
            if self.debug:
                self.logger.debug(f"Unsupported expression type: {type(expr_node).__name__}")
            return None

    def _translate_expr_number(self, ctx: AstToIrContext, expr: Any) -> ir.ExprConstant:
        """Translate a number literal"""
        value = expr.getValue()
        return ir.ExprConstant(value=value)

    def _translate_expr_string(self, ctx: AstToIrContext, expr: pss_ast.ExprString) -> ir.ExprConstant:
        """Translate a string literal"""
        value = expr.getValue()
        return ir.ExprConstant(value=value)

    def _translate_expr_bool(self, ctx: AstToIrContext, expr: pss_ast.ExprBool) -> ir.ExprConstant:
        """Translate a boolean literal"""
        value = expr.getValue()
        return ir.ExprConstant(value=value)

    def _translate_expr_bin(self, ctx: AstToIrContext, expr) -> ir.ExprBin:
        """Translate a binary expression"""
        # Get left and right operands
        lhs = self._translate_expression(ctx, expr.getLhs())
        rhs = self._translate_expression(ctx, expr.getRhs())

        # Get operator
        op = self._map_binop(expr.getOp())

        return ir.ExprBin(lhs=lhs, op=op, rhs=rhs)

    def _translate_expr_unary(self, ctx: AstToIrContext, expr: pss_ast.ExprUnary) -> ir.ExprUnary:
        """Translate a unary expression"""
        # Get operand
        operand = self._translate_expression(ctx, expr.getExpr())

        # Get operator
        op = self._map_unaryop(expr.getOp())

        return ir.ExprUnary(op=op, operand=operand)

    def _translate_expr_cond(self, ctx: AstToIrContext, expr) -> ir.ExprIfExp:
        """Translate a conditional (ternary) expression"""
        test = self._translate_expression(ctx, expr.getCond_e())
        body = self._translate_expression(ctx, expr.getTrue_e())
        orelse = self._translate_expression(ctx, expr.getFalse_e())

        return ir.ExprIfExp(test=test, body=body, orelse=orelse)

    def _translate_expr_in(self, ctx: AstToIrContext, expr) -> ir.ExprIn:
        """Translate a PSS 'in' expression to IR ExprIn.

        Two forms:
          Range-list: x in [0, 1, 2]     -> ExprIn(value, ExprRangeList([...]))
          Collection: x in comp.some_list -> ExprIn(value, <ExprAttribute chain>)

        The collection form is detected via getCollection() (non-None when the
        grammar matched collection_expression rather than open_range_list).
        """
        value = self._translate_expression(ctx, expr.getLhs())

        # Collection-reference form: x in comp.some_list
        coll_node = expr.getCollection() if hasattr(expr, 'getCollection') else None
        if coll_node is not None:
            container = self._translate_expression(ctx, coll_node)
            return ir.ExprIn(value=value, container=container)

        # Range-list form: x in [0, 1, 2] or x in [lo..hi]
        rhs = expr.getRhs()  # ExprOpenRangeList
        ranges = []
        if rhs is not None:
            for i in range(rhs.numValues()):
                v = rhs.getValue(i)
                lower = self._translate_expression(ctx, v.getLhs()) if v.getLhs() else None
                upper = self._translate_expression(ctx, v.getRhs()) if v.getRhs() else None
                ranges.append(ir.ExprRange(lower=lower, upper=upper))
        return ir.ExprIn(value=value, container=ir.ExprRangeList(ranges=ranges))

    def _translate_expr_ref(self, ctx: AstToIrContext, expr) -> ir.Expr:
        """Translate a reference expression (variable, field, or method call) to IR.

        For plain references like `a.b.c`, builds an ExprAttribute chain:
            self.a.b.c

        For method calls like `a.b.method(x, y)`, the final element has a
        MethodParameterList and is emitted as ExprCall:
            ExprCall(func=self.a.b.method, args=[x, y])
        """
        hier_id = expr.getHier_id()
        if not hier_id or hier_id.numElems() == 0:
            return ir.ExprRefUnresolved(name="unknown")

        elems = [hier_id.getElem(i) for i in range(hier_id.numElems())]

        # Check if the first element is a known local variable (e.g. foreach iterator 'p').
        # Single-element: return ExprRefLocal('p').
        # Multi-element: build ExprAttribute(ExprRefLocal('p'), 'x', ...) instead of
        #   ExprAttribute(TypeExprRefSelf(), 'p', 'x') so the solver can substitute 'p'.
        if elems and hasattr(elems[0], 'getId') and ctx is not None:
            first_id = elems[0].getId()
            first_name = first_id.getId() if isinstance(first_id, pss_ast.ExprId) else str(first_id)
            if first_name in ctx.local_vars:
                if len(elems) == 1:
                    return ir.ExprRefLocal(name=first_name)
                # Multi-element path rooted at a local variable (e.g. p.x, s.upper())
                result_lv: ir.Expr = ir.ExprRefLocal(name=first_name)
                for elem in elems[1:]:
                    if not hasattr(elem, 'getId'):
                        continue
                    id_obj = elem.getId()
                    attr = id_obj.getId() if isinstance(id_obj, pss_ast.ExprId) else str(id_obj)
                    result_lv = ir.ExprAttribute(value=result_lv, attr=attr)
                    n_sub = elem.numSubscript() if hasattr(elem, 'numSubscript') else 0
                    for si in range(n_sub):
                        sub_expr = elem.getSubscript(si)
                        if sub_expr is not None:
                            idx_ir = self._translate_expression(ctx, sub_expr)
                            if idx_ir is not None:
                                result_lv = ir.ExprSubscript(value=result_lv, slice=idx_ir)
                    # Handle method calls on this element (e.g. s.upper())
                    params = elem.getParams() if hasattr(elem, 'getParams') else None
                    if params is not None and hasattr(params, 'numParameters'):
                        args = []
                        for j in range(params.numParameters()):
                            arg_node = params.getParameter(j)
                            arg_ir = self._translate_expression(ctx, arg_node)
                            if arg_ir is not None:
                                args.append(arg_ir)
                        result_lv = ir.ExprCall(func=result_lv, args=args)
                return result_lv

        # If the first element refers to an enum constant, emit ExprConstant
        # so the constraint solver sees a literal value instead of a variable.
        if len(elems) == 1 and hasattr(elems[0], 'getId') and ctx is not None:
            id_obj = elems[0].getId()
            name = id_obj.getId() if isinstance(id_obj, pss_ast.ExprId) else str(id_obj)
            enum_val = self._resolve_enum_constant(ctx, name)
            if enum_val is not None:
                return ir.ExprConstant(value=enum_val)

        # Build the ExprAttribute chain starting from self.
        # Note: expr.getIs_super() is True for ALL scope-level references in the PSS
        # frontend (not just actual super.x references), so we cannot use it to
        # distinguish super calls. Both "x" and "super.x" produce identical AST.
        result: ir.Expr = ir.TypeExprRefSelf()
        for elem in elems:
            if not hasattr(elem, 'getId'):
                continue
            id_obj = elem.getId()
            name = id_obj.getId() if isinstance(id_obj, pss_ast.ExprId) else str(id_obj)
            result = ir.ExprAttribute(value=result, attr=name)

            # Apply any subscript indexes on this element: items[0] → result[0]
            n_sub = elem.numSubscript() if hasattr(elem, 'numSubscript') else 0
            for si in range(n_sub):
                sub_expr = elem.getSubscript(si)
                if sub_expr is not None:
                    index_ir = self._translate_expression(ctx, sub_expr)
                    if index_ir is not None:
                        result = ir.ExprSubscript(value=result, slice=index_ir)

            # If this element has method parameters, emit a call immediately
            params = elem.getParams() if hasattr(elem, 'getParams') else None
            if params is not None and hasattr(params, 'numParameters'):
                args = []
                for j in range(params.numParameters()):
                    arg_node = params.getParameter(j)
                    arg_ir = self._translate_expression(ctx, arg_node)
                    if arg_ir is not None:
                        args.append(arg_ir)
                result = ir.ExprCall(func=result, args=args)

        return result

    def _resolve_enum_constant(self, ctx: AstToIrContext, name: str) -> Optional[int]:
        """Check if *name* is an enum member across all registered enums.

        Returns the integer value if found, or None.
        """
        for dt in ctx.type_map.values():
            if isinstance(dt, ir.DataTypeEnum) and name in dt.items:
                return dt.items[name]
        return None

    def _translate_expr_cast(self, ctx: AstToIrContext, expr) -> ir.ExprCast:
        """Translate a cast expression.

        Handles both numeric casts ``(bit[N])val`` and enum casts ``(my_enum)val``.
        """
        target_type = self._translate_data_type(ctx, expr.getCasting_type())
        operand = self._translate_expression(ctx, expr.getExpr())

        return ir.ExprCast(target_type=target_type, value=operand)

    def _translate_expr_subscript(self, ctx: AstToIrContext, expr: pss_ast.ExprSubscript) -> ir.ExprSubscript:
        """Translate a subscript expression (array indexing)"""
        value = self._translate_expression(ctx, expr.getLhs())
        index = self._translate_expression(ctx, expr.getRhs())

        return ir.ExprSubscript(value=value, slice=index)

    def _translate_expr_bitslice(self, ctx: AstToIrContext, expr: pss_ast.ExprBitSlice) -> ir.ExprSlice:
        """Translate a bit slice expression"""
        value = self._translate_expression(ctx, expr.getLhs())
        lower = self._translate_expression(ctx, expr.getLower())
        upper = self._translate_expression(ctx, expr.getUpper())

        return ir.ExprSlice(lower=lower, upper=upper, step=None)

    def _translate_expr_substring(self, ctx: AstToIrContext, expr: pss_ast.ExprSubstring) -> ir.ExprSlice:
        """Translate a string sub-string expression s[start..end] → ExprSlice"""
        value = self._translate_expression(ctx, expr.getExpr())
        start = self._translate_expression(ctx, expr.getStart())
        end = self._translate_expression(ctx, expr.getEnd())
        return ir.ExprSlice(lower=start, upper=end, step=None)

    def _translate_expr_aggr_list(self, ctx: AstToIrContext, expr) -> ir.ExprList:
        """Translate a PSS aggregate list literal {1, 2, 3} to ExprList"""
        elts = []
        for i in range(expr.numElems() if hasattr(expr, 'numElems') else 0):
            elem = expr.getElem(i)
            ir_elem = self._translate_expression(ctx, elem)
            if ir_elem is not None:
                elts.append(ir_elem)
        return ir.ExprList(elts=elts)

    def _translate_expr_aggr_map(self, ctx: AstToIrContext, expr) -> ir.ExprDict:
        """Translate a PSS aggregate map literal {k1:v1, k2:v2} to ExprDict"""
        keys = []
        values = []
        for i in range(expr.numElems() if hasattr(expr, 'numElems') else 0):
            elem = expr.getElem(i)
            key_ir = self._translate_expression(ctx, elem.getLhs())
            val_ir = self._translate_expression(ctx, elem.getRhs())
            if key_ir is not None and val_ir is not None:
                keys.append(key_ir)
                values.append(val_ir)
        return ir.ExprDict(keys=keys, values=values)

    def _translate_expr_aggr_struct(self, ctx: AstToIrContext, expr) -> ir.ExprStructLiteral:
        """Translate a PSS struct aggregate literal {.a=1, .b=2} to ExprStructLiteral"""
        fields = []
        for i in range(expr.numElems() if hasattr(expr, 'numElems') else 0):
            elem = expr.getElem(i)
            name_node = elem.getName()
            field_name = name_node.getId() if isinstance(name_node, pss_ast.ExprId) else str(name_node)
            val_ir = self._translate_expression(ctx, elem.getValue())
            if val_ir is not None:
                fields.append(ir.ExprStructField(name=field_name, value=val_ir))
        return ir.ExprStructLiteral(fields=fields)

    def _map_binop(self, op: int) -> ir.BinOp:
        """Map PSS binary operator (integer) to IR operator"""
        # PSS operator values (discovered empirically)
        mapping = {
            0: ir.BinOp.Or,       # ||
            1: ir.BinOp.And,      # &&
            2: ir.BinOp.BitOr,    # |
            3: ir.BinOp.BitXor,   # ^
            4: ir.BinOp.BitAnd,   # &
            5: ir.BinOp.Lt,       # <
            6: ir.BinOp.LtE,      # <=
            7: ir.BinOp.Gt,       # >
            8: ir.BinOp.GtE,      # >=
            10: ir.BinOp.Mult,    # *
            11: ir.BinOp.Div,     # /
            12: ir.BinOp.Mod,     # %
            13: ir.BinOp.Add,     # +
            14: ir.BinOp.Sub,     # -
            15: ir.BinOp.LShift,  # <<
            16: ir.BinOp.RShift,  # >>
            17: ir.BinOp.Eq,      # ==
            18: ir.BinOp.NotEq,   # !=
        }
        return mapping.get(op, ir.BinOp.Add)

    def _map_unaryop(self, op: int) -> ir.UnaryOp:
        """Map PSS unary operator (integer) to IR operator"""
        # PSS unary operator values (best guess based on common conventions)
        mapping = {
            0: ir.UnaryOp.Not,      # !
            1: ir.UnaryOp.USub,     # -
            2: ir.UnaryOp.UAdd,     # +
            3: ir.UnaryOp.Invert,   # ~
        }
        return mapping.get(op, ir.UnaryOp.Not)

    def _translate_data_type(self, ctx: AstToIrContext, dtype_node: Any) -> Optional[ir.DataType]:
        """Translate a data type node to IR

        Args:
            ctx: Translation context
            dtype_node: PSS data type AST node

        Returns:
            IR DataType or None
        """
        if isinstance(dtype_node, pss_ast.DataTypeInt):
            # Get bit width and signedness
            width = dtype_node.getWidth()
            if width and hasattr(width, 'getValue'):
                bits = width.getValue()
            else:
                bits = 32  # Default

            is_signed = dtype_node.getIs_signed()
            return ir.DataTypeInt(bits=bits, signed=is_signed)

        elif isinstance(dtype_node, pss_ast.DataTypeUserDefined):
            # User-defined type - check if it's a template specialization or simple reference
            type_id = dtype_node.getType_id()

            # Check if this is a TypeIdentifier (template specialization)
            if isinstance(type_id, pss_ast.TypeIdentifier):
                return self._translate_type_identifier(ctx, type_id)
            elif isinstance(type_id, pss_ast.ExprId):
                type_name = type_id.getId()
            else:
                type_name = str(type_id)

            # Check if type exists in registry
            existing_type = ctx.get_type(type_name)
            if existing_type:
                return existing_type
            else:
                # Create reference for forward declaration
                return ir.DataTypeRef(ref_name=type_name)

        elif isinstance(dtype_node, pss_ast.DataTypeString):
            return ir.DataTypeString()

        elif isinstance(dtype_node, pss_ast.DataTypeBool):
            return ctx.get_type("bool")

        elif isinstance(dtype_node, pss_ast.DataTypeChandle):
            return ir.DataTypeChandle()

        else:
            if self.debug:
                self.logger.debug(f"Unsupported data type: {type(dtype_node).__name__}")
            return None

    def _type_identifier_name(self, node) -> Optional[str]:
        """Extract the (possibly package-qualified) type name from a TypeIdentifier or ExprId.

        For multi-element TypeIdentifiers like ``sys_pkg::base_a``, returns the
        full ``"::"``-joined name.  Single-element identifiers return the name directly.

        Args:
            node: pss_ast.TypeIdentifier or pss_ast.ExprId

        Returns:
            Type name string, or None if extraction fails
        """
        if isinstance(node, pss_ast.ExprId):
            return node.getId()
        if isinstance(node, pss_ast.TypeIdentifier) and node.numElems() > 0:
            parts = []
            for i in range(node.numElems()):
                elem_id = node.getElem(i).getId()
                nm = elem_id.getId() if isinstance(elem_id, pss_ast.ExprId) else str(elem_id)
                parts.append(nm)
            return "::".join(parts)
        return None

    def _translate_type_identifier(self, ctx: AstToIrContext, type_id: pss_ast.TypeIdentifier) -> Optional[ir.DataType]:
        """Translate a TypeIdentifier (potentially with template parameters)

        Args:
            ctx: Translation context
            type_id: TypeIdentifier AST node

        Returns:
            IR DataType (may be DataTypeRegister for reg_c specializations)
        """
        # TypeIdentifier has elems list - get the first element
        if type_id.numElems() == 0:
            return None

        elem = type_id.getElem(0)
        elem_id = elem.getId()

        # Get the base type name
        if isinstance(elem_id, pss_ast.ExprId):
            type_name = elem_id.getId()
        else:
            type_name = str(elem_id)

        # Check if this is a reg_c specialization
        if type_name == "reg_c":
            return self._translate_reg_c(ctx, elem)

        # Handle built-in collection types
        if type_name in ("list", "array", "map", "set"):
            return self._translate_collection_type(ctx, type_name, elem)

        # Build full qualified name for package-scoped types (e.g. sys_pkg::base_a)
        if type_id.numElems() > 1:
            parts = []
            for i in range(type_id.numElems()):
                e_id = type_id.getElem(i).getId()
                nm = e_id.getId() if isinstance(e_id, pss_ast.ExprId) else str(e_id)
                parts.append(nm)
            qualified_name = "::".join(parts)
        else:
            qualified_name = type_name

        # Check type_map first (handles enums, typedefs, structs, components)
        existing = ctx.get_type(qualified_name)
        if existing is not None:
            return existing
        # Fallback: try short name when only a suffix is available
        if "::" in qualified_name:
            short = qualified_name.split("::")[-1]
            existing = ctx.get_type(short)
            if existing is not None:
                return existing

        # Fall back to forward reference
        return ir.DataTypeRef(ref_name=qualified_name)

    def _translate_collection_type(
        self,
        ctx: AstToIrContext,
        coll_name: str,
        elem: pss_ast.TypeIdentifierElem,
    ) -> Optional[ir.DataType]:
        """Translate a built-in PSS collection type to the corresponding IR type.

        Supports ``list<T>``, ``array<T, N>``, ``map<K, V>``, and ``set<T>``.

        Args:
            ctx: Translation context
            coll_name: One of "list", "array", "map", "set"
            elem: TypeIdentifierElem carrying the template parameters

        Returns:
            DataTypeList | DataTypeArray | DataTypeMap | DataTypeSet
        """
        params = elem.getParams()
        if params is None:
            return None

        def get_type_param(index: int) -> Optional[ir.DataType]:
            """Extract a data-type template parameter at ``index``."""
            if index >= params.numValues():
                return None
            pv = params.getValue(index)
            inner = pv.getValue()
            if inner is None:
                return None
            return self._translate_data_type(ctx, inner)

        def get_int_param(index: int) -> int:
            """Extract an integer-valued template parameter at ``index``."""
            if index >= params.numValues():
                return -1
            pv = params.getValue(index)
            inner = pv.getValue()
            if inner is not None and hasattr(inner, 'getValue'):
                return inner.getValue()
            return -1

        if coll_name == "list":
            return ir.DataTypeList(element_type=get_type_param(0))

        elif coll_name == "array":
            return ir.DataTypeArray(
                element_type=get_type_param(0),
                size=get_int_param(1),
            )

        elif coll_name == "map":
            return ir.DataTypeMap(
                key_type=get_type_param(0),
                value_type=get_type_param(1),
            )

        elif coll_name == "set":
            return ir.DataTypeSet(element_type=get_type_param(0))

        return None

    def _translate_reg_c(self, ctx: AstToIrContext, elem: pss_ast.TypeIdentifierElem) -> ir.DataTypeRegister:
        """Translate a reg_c<R, ACC, SZ> template specialization to DataTypeRegister

        Args:
            ctx: Translation context
            elem: TypeIdentifierElem with template parameters

        Returns:
            DataTypeRegister IR node
        """
        # Extract template parameters
        params = elem.getParams()

        # Default values per PSS spec
        register_value_type = None
        access_mode = "READWRITE"
        size_bits = None
        template_args = []

        if params and params.numValues() > 0:
            # First parameter: R (type)
            param0 = params.getValue(0)
            if isinstance(param0, pss_ast.TemplateParamTypeValue):
                # Get the data type
                dtype = param0.getValue()
                register_value_type = self._translate_data_type(ctx, dtype)

                # Store template arg for completeness
                if register_value_type:
                    template_args.append(ir.TemplateArgType(
                        param_name="R",
                        type_value=register_value_type
                    ))

            # Second parameter: ACC (enum - access mode)
            # Note: This can be either TemplateParamTypeValue or TemplateParamExprValue
            if params.numValues() > 1:
                param1 = params.getValue(1)

                # Try both TemplateParamTypeValue and TemplateParamExprValue
                expr = None
                if isinstance(param1, pss_ast.TemplateParamTypeValue):
                    # READONLY/READWRITE/WRITEONLY might come as a type
                    dtype = param1.getValue()
                    # dtype should be DataTypeUserDefined with identifier READONLY etc
                    if isinstance(dtype, pss_ast.DataTypeUserDefined):
                        type_id_acc = dtype.getType_id()
                        if isinstance(type_id_acc, pss_ast.ExprId):
                            access_mode = type_id_acc.getId()
                        elif isinstance(type_id_acc, pss_ast.TypeIdentifier):
                            # Handle TypeIdentifier case
                            if type_id_acc.numElems() > 0:
                                elem_acc = type_id_acc.getElem(0)
                                elem_id_acc = elem_acc.getId()
                                if isinstance(elem_id_acc, pss_ast.ExprId):
                                    access_mode = elem_id_acc.getId()
                elif isinstance(param1, pss_ast.TemplateParamExprValue):
                    # Get the expression (should be an identifier like READONLY)
                    expr = param1.getValue()

                    if isinstance(expr, pss_ast.ExprId):
                        access_mode = expr.getId()
                    elif isinstance(expr, pss_ast.ExprRefPathStatic):
                        # Handle hierarchical references like addr_reg_pkg::READONLY
                        if expr.numBase() > 0:
                            last_elem = expr.getBase(expr.numBase() - 1)
                            if isinstance(last_elem, pss_ast.TypeIdentifierElem):
                                elem_id = last_elem.getId()
                                if isinstance(elem_id, pss_ast.ExprId):
                                    access_mode = elem_id.getId()
                    elif hasattr(expr, 'getLeaf'):
                        # Try ExprRefPathContext or similar
                        leaf = expr.getLeaf()
                        if leaf and hasattr(leaf, 'getId'):
                            access_mode = leaf.getId()
                    elif hasattr(expr, 'getId'):
                        # Fallback: try direct getId
                        access_mode = expr.getId()

                template_args.append(ir.TemplateArgEnum(
                    param_name="ACC",
                    enum_value=access_mode
                ))

            # Third parameter: SZ2 (int - size in bits)
            if params.numValues() > 2:
                param2 = params.getValue(2)
                if isinstance(param2, pss_ast.TemplateParamExprValue):
                    expr = param2.getValue()
                    if isinstance(expr, pss_ast.ExprNumber):
                        size_bits = expr.getValue()

                        template_args.append(ir.TemplateArgValue(
                            param_name="SZ2",
                            value_expr=ir.ExprConstant(value=size_bits)
                        ))

        # Calculate size_bits if not explicitly provided
        if size_bits is None and register_value_type:
            # Default: 8 * sizeof(R), rounded to byte boundary
            if isinstance(register_value_type, ir.DataTypeInt):
                size_bits = register_value_type.bits
            else:
                size_bits = 32  # Conservative default

        if size_bits is None:
            size_bits = 32  # Absolute fallback

        # Ensure we have register_value_type
        if register_value_type is None:
            # Fallback for missing type parameter
            register_value_type = ir.DataTypeInt(bits=size_bits, signed=False)

        # Create DataTypeRegister
        reg = ir.DataTypeRegister(
            name=f"reg_c<{register_value_type.name if hasattr(register_value_type, 'name') else 'T'}>",
            super=None,  # reg_c doesn't have explicit super type
            register_value_type=register_value_type,
            access_mode=access_mode,
            size_bits=size_bits,
            template_args=template_args
        )

        # Add built-in register functions
        self._add_register_functions(ctx, reg)

        # Extract fields if register uses a struct
        self._extract_register_fields(ctx, reg)

        return reg

    def _add_register_functions(self, ctx: AstToIrContext, reg: ir.DataTypeRegister):
        """Add built-in functions to a register (read, write, read_val, write_val)

        Args:
            ctx: Translation context
            reg: Register to add functions to
        """
        # read() - returns the register value type
        read_func = ir.Function(
            name="read",
            args=ir.Arguments(args=[]),  # No arguments
            body=[],  # import target has no body
            returns=reg.register_value_type,
            is_async=False,
            is_import=True,
            is_target=True
        )
        reg.functions.append(read_func)

        # write(val) - takes register value type, returns void
        write_arg = ir.Arg(
            arg="r",  # Parameter name per PSS spec
            annotation=None  # Type info in DataType, not Expr
        )
        write_func = ir.Function(
            name="write",
            args=ir.Arguments(args=[write_arg]),
            body=[],
            returns=None,  # void
            is_async=False,
            is_import=True,
            is_target=True
        )
        reg.functions.append(write_func)

        # read_val() - returns raw integer
        read_val_func = ir.Function(
            name="read_val",
            args=ir.Arguments(args=[]),
            body=[],
            returns=ir.DataTypeInt(bits=reg.size_bits, signed=False),
            is_async=False,
            is_import=True,
            is_target=True
        )
        reg.functions.append(read_val_func)

        # write_val(val) - takes raw integer
        write_val_arg = ir.Arg(
            arg="r",  # Parameter name per PSS spec
            annotation=None
        )
        write_val_func = ir.Function(
            name="write_val",
            args=ir.Arguments(args=[write_val_arg]),
            body=[],
            returns=None,
            is_async=False,
            is_import=True,
            is_target=True
        )
        reg.functions.append(write_val_func)

    def _extract_register_fields(self, ctx: AstToIrContext, reg: ir.DataTypeRegister):
        """Extract fields from register value type if it's a struct

        Args:
            ctx: Translation context
            reg: Register to extract fields into
        """
        # If register_value_type is a struct, copy its fields to the register
        value_type = reg.register_value_type

        # Handle DataTypeRef - resolve to actual type
        if isinstance(value_type, ir.DataTypeRef):
            resolved = ctx.get_type(value_type.ref_name)
            if resolved:
                value_type = resolved

        # If it's a struct, copy its fields
        if isinstance(value_type, ir.DataTypeStruct):
            for field in value_type.fields:
                reg.fields.append(field)

    def _add_register_group_functions(self, ctx: AstToIrContext, reg_group: ir.DataTypeRegisterGroup):
        """Add built-in functions to a register group

        Args:
            ctx: Translation context
            reg_group: Register group to add functions to
        """
        # get_offset_of_instance(string name) -> bit[64]
        name_arg = ir.Arg(
            arg="name",
            annotation=None
        )
        offset_func = ir.Function(
            name="get_offset_of_instance",
            args=ir.Arguments(args=[name_arg]),
            body=[],
            returns=ir.DataTypeInt(bits=64, signed=False),
            is_async=False
        )
        reg_group.functions.append(offset_func)

        # get_offset_of_instance_array(string name, bit[32] index) -> bit[64]
        index_arg = ir.Arg(
            arg="index",
            annotation=None
        )
        offset_array_func = ir.Function(
            name="get_offset_of_instance_array",
            args=ir.Arguments(args=[name_arg, index_arg]),
            body=[],
            returns=ir.DataTypeInt(bits=64, signed=False),
            is_async=False
        )
        reg_group.functions.append(offset_array_func)

    def _compute_register_offsets(self, ctx: AstToIrContext, reg_group: ir.DataTypeRegisterGroup):
        """Compute sequential offsets for registers in a register group

        Args:
            ctx: Translation context
            reg_group: Register group to compute offsets for
        """
        current_offset = 0

        for field in reg_group.fields:
            # Check if this field is a register
            field_type = field.datatype

            # Resolve DataTypeRef if needed
            if isinstance(field_type, ir.DataTypeRef):
                resolved = ctx.get_type(field_type.ref_name)
                if resolved:
                    field_type = resolved

            # Only process register fields
            if isinstance(field_type, ir.DataTypeRegister):
                # Store offset for this register
                reg_group.offset_map[field.name] = current_offset

                # Compute size in bytes (round up to nearest byte)
                size_bytes = (field_type.size_bits + 7) // 8

                # Apply 4-byte alignment (minimum alignment for registers)
                aligned_size = ((size_bytes + 3) // 4) * 4

                # Advance offset
                current_offset += aligned_size


    def _inject_fill_in_activity(self, activity_ir, ann) -> None:
        """Wrap matching ActivityAnonTraversal nodes in ActivityFill.

        The preprocessor normalises ``fill { do action ...; }`` to
        ``do action;``, which the AST-to-IR translator converts to an
        ``ActivityAnonTraversal``.  This method replaces that traversal with
        ``ActivityFill(body=[traversal], max_iters=ann.data['max_iters'])``.

        Only the *first* matching traversal in the body (recursively) is
        replaced.  Subsequent fill blocks in the same activity would each
        have their own annotation entry.
        """
        from zuspec.ir.core.activity import ActivityFill, ActivityAnonTraversal, ActivitySequenceBlock
        action_name: str = ann.data.get('action_name', '')
        max_iters: int = ann.data.get('max_iters', 1000)
        if not action_name:
            return
        _replace_traversal_with_fill(activity_ir, action_name, max_iters)


    # ---------------------------------------------------------------------------
    # Annotation injection helpers
    # ---------------------------------------------------------------------------

    def _inject_forall_constraint(self, ctx: AstToIrContext, owner_ir, ann) -> None:
        """Inject a forall constraint into *owner_ir* from a PssAnnotation.

        Translates the pre-link body AST nodes captured during pass 1 into IR
        StmtForeach nodes, wrapped in a constraint Function appended to
        *owner_ir*.functions.  The collection path is built as an ExprAttribute
        chain rooted at TypeExprRefSelf.
        """
        import pssparser.ast as pss_ast
        iterator: str = ann.data.get('iterator', '')
        coll_path: list = ann.data.get('collection', [])
        body_ast: list = ann.data.get('body_ast', [])

        if not iterator or not coll_path or not body_ast:
            return

        # Build collection expression: self.pkts (or self.comp.pkts for chained paths)
        coll_expr: ir.Expr = ir.TypeExprRefSelf()
        for part in coll_path:
            coll_expr = ir.ExprAttribute(value=coll_expr, attr=part)

        # Translate body with the iterator variable in scope
        ctx.local_vars.add(iterator)
        foreach_body: list = []
        for stmt in body_ast:
            if stmt is None:
                continue
            if isinstance(stmt, pss_ast.ConstraintStmtExpr):
                expr_ir = self._translate_expression(ctx, stmt.getExpr())
                if expr_ir is not None:
                    foreach_body.append(ir.StmtExpr(expr=expr_ir))
        ctx.local_vars.discard(iterator)

        if not foreach_body:
            return

        idx = sum(1 for f in owner_ir.functions if f.metadata.get('_is_constraint'))
        owner_ir.functions.append(ir.Function(
            name=f'_c_{idx}',
            is_async=False,
            metadata={'_is_constraint': True},
            body=[ir.StmtForeach(
                target=ir.ExprRefLocal(name=iterator),
                iter=coll_expr,
                body=foreach_body,
            )],
        ))

    def _inject_covergroup(self, ctx: AstToIrContext, owner_ir, ann) -> None:
        """Inject a PssCoverGroup into *owner_ir*.covergroups from a PssAnnotation."""
        from zuspec.ir.core.coverage import PssCoverGroup, PssCoverPoint, PssCoverCross

        instance_name: str = ann.data.get('instance_name', 'cg')
        cp_data_list: list = ann.data.get('coverpoints', [])
        cx_data_list: list = ann.data.get('crosses', [])

        coverpoints = []
        for cp_data in cp_data_list:
            target_name = cp_data.get('target', '')
            if not target_name:
                continue
            target_expr = ir.ExprAttribute(value=ir.TypeExprRefSelf(), attr=target_name)
            coverpoints.append(PssCoverPoint(
                name=cp_data.get('name', target_name),
                target_expr=target_expr,
            ))

        crosses = []
        for cx_data in cx_data_list:
            crosses.append(PssCoverCross(
                name=cx_data.get('name', 'cross'),
                coverpoint_names=list(cx_data.get('coverpoint_names', [])),
            ))

        owner_ir.covergroups.append(PssCoverGroup(
            instance_name=instance_name,
            coverpoints=coverpoints,
            crosses=crosses,
        ))


def _activity_body_children(body):
    """Return an iterable of children for an activity body scope (or empty)."""
    if body is None:
        return []
    if hasattr(body, 'children'):
        return body.children()
    return []


def _replace_traversal_with_fill(stmt_or_block, action_name: str, max_iters: int) -> bool:
    """Recursively find the first ActivityAnonTraversal matching *action_name* in
    *stmt_or_block* and replace it with ActivityFill(body=[traversal]).

    Returns True if a replacement was made (so callers can stop recursing).
    """
    from zuspec.ir.core.activity import (
        ActivityFill, ActivityAnonTraversal, ActivitySequenceBlock,
        ActivityParallel, ActivitySchedule, ActivityAtomic,
        ActivityRepeat, ActivityForeach, ActivityIfElse,
    )

    if not hasattr(stmt_or_block, 'stmts'):
        return False
    stmts = stmt_or_block.stmts
    for idx, stmt in enumerate(stmts):
        if isinstance(stmt, ActivityAnonTraversal):
            # Check if this traversal matches the fill target
            at = stmt.action_type or ''
            if at == action_name or at.endswith(f'::{action_name}'):
                stmts[idx] = ActivityFill(body=[stmt], max_iters=max_iters)
                return True
        # Recurse into nested blocks
        if hasattr(stmt, 'stmts'):
            if _replace_traversal_with_fill(stmt, action_name, max_iters):
                return True
        if hasattr(stmt, 'body') and hasattr(stmt.body, '__iter__'):
            class _Wrapper:
                def __init__(self, s):
                    self.stmts = s
            if _replace_traversal_with_fill(_Wrapper(stmt.body), action_name, max_iters):
                return True
    return False
