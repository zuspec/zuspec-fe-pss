"""
AST to IR Translation Module

Translates PSS AST nodes to Zuspec IR (Intermediate Representation).
"""
from __future__ import annotations
import logging
from typing import Dict, List, Optional, Any, Set, TYPE_CHECKING
from zuspec.dataclasses import ir

if TYPE_CHECKING:
    from zuspec.fe.pss import ast as pss_ast
else:
    from zuspec.fe.pss import ast as pss_ast


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

    def translate(self, ast_root: pss_ast.GlobalScope) -> AstToIrContext:
        """Translate the entire AST to IR

        Args:
            ast_root: Root AST node (GlobalScope)

        Returns:
            Translation context with IR and type registry
        """
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

        # Push scope
        ctx.push_scope(comp)

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

        # Add built-in functions for register groups
        if is_register_group:
            self._add_register_group_functions(ctx, comp)
            # Compute register offsets
            self._compute_register_offsets(ctx, comp)

        # Pop scope
        ctx.pop_scope()

        return comp

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
        
        # Push scope
        ctx.push_scope(action_ir)
        
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
                     
        # Pop scope
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
            for b in node.getBranches():
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
            # Bind statements are structural; skip for now
            return None

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
        return ir.ActivityTraversal(handle=handle, inline_constraints=[])

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

        return ir.ActivityAnonTraversal(
            action_type=action_type,
            label=label,
            inline_constraints=[],
        )

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

        # Register in type map
        ctx.add_type(qualified_name, struct_ir)
        if namespace_prefix:
            ctx.add_type(struct_name, struct_ir)

        # Push scope
        ctx.push_scope(struct_ir)

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

        # Pop scope
        ctx.pop_scope()

        return struct_ir

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

        return ir.Function(
            name=func_name,
            is_async=False,
            body=body,
            metadata={'_is_constraint': True},
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
        ir_func = ir.Function(
            name=func_name,
            args=args,
            body=body_stmts,
            returns=return_type,
            is_async=False,
            is_invariant=bool(is_pure)
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

        # Create name expression for target
        target = ir.ExprRefLocal(name=var_name)

        return ir.StmtAnnAssign(target=target, annotation=var_type, value=value)

    def _translate_stmt_assignment(self, ctx: AstToIrContext, stmt: pss_ast.ProceduralStmtAssignment) -> ir.StmtAssign:
        """Translate an assignment statement"""
        # Get left-hand side
        lhs = stmt.getLhs()
        target = self._translate_expression(ctx, lhs)

        # Get right-hand side
        rhs = stmt.getRhs()
        value = self._translate_expression(ctx, rhs)

        return ir.StmtAssign(targets=[target], value=value)

    def _translate_stmt_if(self, ctx: AstToIrContext, stmt: pss_ast.ProceduralStmtIfElse) -> ir.StmtIf:
        """Translate an if-else statement"""
        # Get condition from first if clause
        if_clause = stmt.getIf_then(0)
        cond = self._translate_expression(ctx, if_clause.getCond())

        # Get then body
        then_body_scope = if_clause.getBody()
        then_body = []
        if then_body_scope:
            for child in then_body_scope.children():
                if child is None:
                    continue
                stmt_ir = self._translate_statement(ctx, child)
                if stmt_ir:
                    then_body.append(stmt_ir)

        # Get else body (if present)
        else_body = []
        else_clause = stmt.getElse_then()
        if else_clause:
            for child in else_clause.children():
                if child is None:
                    continue
                stmt_ir = self._translate_statement(ctx, child)
                if stmt_ir:
                    else_body.append(stmt_ir)

        return ir.StmtIf(test=cond, body=then_body, orelse=else_body)

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

        # Create a for loop with count as the iterator
        # For simplicity, use count_expr as the iter
        return ir.StmtFor(target=None, iter=count_expr, body=body)

    def _translate_stmt_repeat_while(self, ctx: AstToIrContext, stmt) -> ir.StmtWhile:
        """Translate a repeat-while statement (do-while)"""
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

        # Note: IR StmtWhile doesn't have a do-while flag, so we just use while
        # The semantics difference would need to be handled at a higher level
        return ir.StmtWhile(test=cond, body=body)

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
        if idx_id is not None:
            idx_name = idx_id.getId() if hasattr(idx_id, 'getId') else str(idx_id)
            index_var = ir.ExprRefLocal(name=idx_name)

        body_scope = stmt.getBody()
        body = []
        if body_scope:
            for child in body_scope.children():
                if child is None:
                    continue
                stmt_ir = self._translate_statement(ctx, child)
                if stmt_ir:
                    body.append(stmt_ir)

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
        """Translate a PSS 'x in [...]' expression to IR ExprIn.

        Converts ExprOpenRangeList to ExprRangeList with ExprRange items.
        Single values become ExprRange(lower=v, upper=None).
        Ranges become ExprRange(lower=lo, upper=hi).
        """
        value = self._translate_expression(ctx, expr.getLhs())
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

        # Check if the first (and only) element is a known local variable (e.g. foreach loop var).
        # If so, emit ExprRefLocal rather than self.x.
        if len(elems) == 1 and hasattr(elems[0], 'getId'):
            id_obj = elems[0].getId()
            name = id_obj.getId() if isinstance(id_obj, pss_ast.ExprId) else str(id_obj)
            if name in ctx.local_vars:
                return ir.ExprRefLocal(name=name)

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
        """Extract the base type name string from a TypeIdentifier or ExprId node.

        Args:
            node: pss_ast.TypeIdentifier or pss_ast.ExprId

        Returns:
            Type name string, or None if extraction fails
        """
        if isinstance(node, pss_ast.ExprId):
            return node.getId()
        if isinstance(node, pss_ast.TypeIdentifier) and node.numElems() > 0:
            elem_id = node.getElem(0).getId()
            if isinstance(elem_id, pss_ast.ExprId):
                return elem_id.getId()
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

        # Check type_map first (handles enums, typedefs, structs, components)
        existing = ctx.get_type(type_name)
        if existing is not None:
            return existing

        # Fall back to forward reference
        return ir.DataTypeRef(ref_name=type_name)

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


def _activity_body_children(body):
    """Return an iterable of children for an activity body scope (or empty)."""
    if body is None:
        return []
    if hasattr(body, 'children'):
        return body.children()
    return []
