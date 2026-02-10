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
            
    def _translate_unit(self, ctx: AstToIrContext, unit):
        """Translate a global scope unit
        
        Args:
            ctx: Translation context
            unit: GlobalScope unit
        """
        # Use children() method which returns an iterable
        for child in unit.children():
            if child is None:
                continue
                
            if isinstance(child, pss_ast.Component):
                self._translate_component(ctx, child)
            elif isinstance(child, pss_ast.Action):
                self._translate_action(ctx, child)
            elif isinstance(child, pss_ast.Struct):
                self._translate_struct(ctx, child)
            # Skip other types for now
                
    def _translate_component(self, ctx: AstToIrContext, component: pss_ast.Component) -> ir.DataTypeComponent:
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
            
        if self.debug:
            self.logger.debug(f"Translating component: {comp_name}")
        
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
            comp = ir.DataTypeRegisterGroup(name=comp_name, super=None)
        else:
            comp = ir.DataTypeComponent(name=comp_name, super=None)
        
        # Register in type map
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
                # Nested action
                self._translate_action(ctx, child)
            elif isinstance(child, pss_ast.Struct):
                # Nested struct
                self._translate_struct(ctx, child)
        
        # Add built-in functions for register groups
        if is_register_group:
            self._add_register_group_functions(ctx, comp)
            # Compute register offsets
            self._compute_register_offsets(ctx, comp)
                
        # Pop scope
        ctx.pop_scope()
        
        return comp
        
    def _translate_action(self, ctx: AstToIrContext, action: pss_ast.Action) -> ir.DataTypeClass:
        """Translate a PSS action to IR DataTypeClass
        
        Args:
            ctx: Translation context
            action: PSS action AST node
            
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
        
        # Register in type map
        ctx.add_type(action_name, action_ir)
        
        # Push scope
        ctx.push_scope(action_ir)
        
        # Handle inheritance
        super_t = action.getSuper_t()
        if super_t is not None:
            if isinstance(super_t, pss_ast.ExprId):
                super_name = super_t.getId()
            else:
                super_name = str(super_t)
            action_ir.super = ir.DataTypeRef(ref_name=super_name)
            
        # Translate children (fields, etc.)
        for child in action.children():
            if child is None:
                continue
                
            if isinstance(child, pss_ast.Field):
                field = self._translate_field(ctx, child)
                if field:
                    action_ir.fields.append(field)
                    
        # Pop scope
        ctx.pop_scope()
        
        return action_ir
        
    def _translate_struct(self, ctx: AstToIrContext, struct: pss_ast.Struct) -> ir.DataTypeStruct:
        """Translate a PSS struct to IR DataTypeStruct
        
        Args:
            ctx: Translation context
            struct: PSS struct AST node
            
        Returns:
            IR DataTypeStruct
        """
        # Extract struct name
        name_node = struct.getName()
        if isinstance(name_node, pss_ast.ExprId):
            struct_name = name_node.getId()
        else:
            struct_name = str(name_node)
            
        if self.debug:
            self.logger.debug(f"Translating struct: {struct_name}")
            
        # Create IR struct
        struct_ir = ir.DataTypeStruct(name=struct_name, super=None)
        
        # Register in type map
        ctx.add_type(struct_name, struct_ir)
        
        # Push scope
        ctx.push_scope(struct_ir)
        
        # Handle inheritance
        super_t = struct.getSuper_t()
        if super_t is not None:
            if isinstance(super_t, pss_ast.ExprId):
                super_name = super_t.getId()
            else:
                super_name = str(super_t)
            struct_ir.super = ir.DataTypeRef(ref_name=super_name)
            
        # Translate children (fields)
        for child in struct.children():
            if child is None:
                continue
                
            if isinstance(child, pss_ast.Field):
                field = self._translate_field(ctx, child)
                if field:
                    struct_ir.fields.append(field)
                    
        # Pop scope
        ctx.pop_scope()
        
        return struct_ir
        
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
        ir_field = ir.Field(
            name=field_name,
            datatype=field_type,
            kind=ir.FieldKind.Field
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
                    params.append(ir.Arg(arg=param_name, annotation=param_type))
                    
        # Create Arguments structure
        args = ir.Arguments(args=params) if params else ir.Arguments(args=[])
        
        # Translate function body
        body_stmts = []
        body = function.getBody()
        if body:
            body_stmts = self._translate_exec_scope(ctx, body)
            
        # Create IR function
        ir_func = ir.Function(
            name=func_name,
            args=args,
            body=body_stmts,
            returns=return_type,
            is_async=False
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
        value = expr.getVal()
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
        
    def _translate_expr_ref(self, ctx: AstToIrContext, expr) -> ir.ExprRefUnresolved:
        """Translate a reference expression (variable, field)"""
        # Get the hierarchical ID
        hier_id = expr.getHier_id()
        if hier_id and hier_id.numElems() > 0:
            # Extract path elements
            path = []
            for i in range(hier_id.numElems()):
                elem = hier_id.getElem(i)
                if hasattr(elem, 'getId'):
                    id_obj = elem.getId()
                    if isinstance(id_obj, pss_ast.ExprId):
                        path.append(id_obj.getId())
                    else:
                        path.append(str(id_obj))
            return ir.ExprRefUnresolved(name='.'.join(path) if path else "unknown")
        else:
            return ir.ExprRefUnresolved(name="unknown")
        
    def _translate_expr_cast(self, ctx: AstToIrContext, expr) -> ir.ExprCast:
        """Translate a cast expression"""
        target_type = self._translate_data_type(ctx, expr.getTarget_t())
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
            
        else:
            if self.debug:
                self.logger.debug(f"Unsupported data type: {type(dtype_node).__name__}")
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
        
        # For other types, just create a reference
        # TODO: Handle other template specializations if needed
        return ir.DataTypeRef(ref_name=type_name)
    
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
