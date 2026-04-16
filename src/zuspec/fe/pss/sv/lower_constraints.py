"""Lower PSS constraint IR to SV constraint expression strings.

Walks the Zuspec constraint IR expression tree and produces SV
constraint expression strings suitable for ``SVConstraintBlock.exprs``.
"""
from __future__ import annotations

from typing import List, Optional

from zuspec.dataclasses import ir

from .context import LoweringContext


# Mapping from IR BinOp to SV operator string
_BINOP_MAP = {
    ir.BinOp.Add: "+",
    ir.BinOp.Sub: "-",
    ir.BinOp.Mult: "*",
    ir.BinOp.Div: "/",
    ir.BinOp.Mod: "%",
    ir.BinOp.BitAnd: "&",
    ir.BinOp.BitOr: "|",
    ir.BinOp.BitXor: "^",
    ir.BinOp.LShift: "<<",
    ir.BinOp.RShift: ">>",
    ir.BinOp.Eq: "==",
    ir.BinOp.NotEq: "!=",
    ir.BinOp.Lt: "<",
    ir.BinOp.LtE: "<=",
    ir.BinOp.Gt: ">",
    ir.BinOp.GtE: ">=",
    ir.BinOp.And: "&&",
    ir.BinOp.Or: "||",
}

_UNARYOP_MAP = {
    ir.UnaryOp.Not: "!",
    ir.UnaryOp.Invert: "~",
    ir.UnaryOp.USub: "-",
    ir.UnaryOp.UAdd: "+",
}

_CMPOP_MAP = {
    ir.CmpOp.Eq: "==",
    ir.CmpOp.NotEq: "!=",
    ir.CmpOp.Lt: "<",
    ir.CmpOp.LtE: "<=",
    ir.CmpOp.Gt: ">",
    ir.CmpOp.GtE: ">=",
}


def lower_constraint_func(
    ctx: LoweringContext,
    func: ir.Function,
) -> Optional[List[str]]:
    """Lower an IR constraint Function to a list of SV constraint expression strings.

    Constraint functions are IR Functions with ``metadata['_is_constraint'] == True``.
    Each statement in the body is a ``StmtExpr`` wrapping a constraint expression.

    Returns:
        List of SV constraint expression strings, or None if not a constraint.
    """
    if not func.metadata.get("_is_constraint"):
        return None

    exprs: List[str] = []
    for stmt in func.body:
        _lower_constraint_stmt(ctx, stmt, exprs)
    return exprs


def _lower_constraint_stmt(
    ctx: LoweringContext,
    stmt: ir.Stmt,
    out: List[str],
) -> None:
    """Lower one constraint statement to SV expression strings."""
    if isinstance(stmt, ir.StmtExpr):
        sv = _lower_expr(ctx, stmt.expr)
        if sv:
            out.append(sv)

    elif isinstance(stmt, ir.StmtIf):
        cond = _lower_expr(ctx, stmt.test)
        if_body: List[str] = []
        for s in stmt.body:
            _lower_constraint_stmt(ctx, s, if_body)
        if stmt.orelse:
            else_body: List[str] = []
            for s in stmt.orelse:
                _lower_constraint_stmt(ctx, s, else_body)
            body_str = " ".join(f"{e};" for e in if_body)
            else_str = " ".join(f"{e};" for e in else_body)
            out.append(f"if ({cond}) {{ {body_str} }} else {{ {else_str} }}")
        else:
            body_str = " ".join(f"{e};" for e in if_body)
            out.append(f"if ({cond}) {{ {body_str} }}")

    elif isinstance(stmt, ir.StmtForeach):
        iter_name = _lower_expr(ctx, stmt.target)
        coll_name = _lower_expr(ctx, stmt.iter)
        inner: List[str] = []
        for s in stmt.body:
            _lower_constraint_stmt(ctx, s, inner)
        inner_str = " ".join(f"{e};" for e in inner)
        out.append(f"foreach ({coll_name}[{iter_name}]) {{ {inner_str} }}")

    elif isinstance(stmt, ir.StmtUnique):
        var_list = ", ".join(stmt.vars)
        out.append(f"unique {{{var_list}}}")


def _lower_expr(ctx: LoweringContext, expr: ir.Expr) -> str:
    """Lower one IR expression to an SV expression string."""
    if isinstance(expr, ir.ExprConstant):
        return _format_constant(expr)

    if isinstance(expr, ir.ExprBin):
        lhs = _lower_expr(ctx, expr.lhs)
        rhs = _lower_expr(ctx, expr.rhs)
        op = _BINOP_MAP.get(expr.op, "??")
        # Implication: PSS uses '->' but IR stores as BinOp (custom)
        return f"({lhs} {op} {rhs})"

    if isinstance(expr, ir.ExprUnary):
        operand = _lower_expr(ctx, expr.operand)
        op = _UNARYOP_MAP.get(expr.op, "!")
        return f"{op}({operand})"

    if isinstance(expr, ir.ExprCompare):
        # ExprCompare uses Python AST style: left, ops[], comparators[]
        left = _lower_expr(ctx, expr.left)
        parts = [left]
        for op, comp in zip(expr.ops, expr.comparators):
            parts.append(_CMPOP_MAP.get(op, "=="))
            parts.append(_lower_expr(ctx, comp))
        return f"({' '.join(parts)})"

    if isinstance(expr, ir.ExprBool):
        op = "&&" if expr.op == ir.BoolOp.And else "||"
        parts = [_lower_expr(ctx, v) for v in expr.values]
        return f" {op} ".join(parts)

    if isinstance(expr, ir.ExprIn):
        val = _lower_expr(ctx, expr.value)
        container = _lower_expr(ctx, expr.container)
        return f"{val} inside {{{container}}}"

    if isinstance(expr, ir.ExprRangeList):
        parts = []
        for r in expr.ranges:
            parts.append(_lower_range(ctx, r))
        return ", ".join(parts)

    if isinstance(expr, ir.ExprRange):
        return _lower_range(ctx, expr)

    if isinstance(expr, ir.ExprAttribute):
        val = _lower_expr(ctx, expr.value)
        if val in ("", "self", "this"):
            return expr.attr
        return f"{val}.{expr.attr}"

    if isinstance(expr, ir.ExprRefLocal):
        return expr.name

    if isinstance(expr, ir.TypeExprRefSelf):
        # 'self' references are stripped in SV constraint context
        return ""

    if isinstance(expr, ir.ExprRefField):
        base = _lower_expr(ctx, expr.base)
        # ExprRefField uses index; we need the field name from context
        # For now, use index notation -- the caller should resolve names
        if base == "" or base == "self":
            # Strip self prefix for class-scope constraints
            return f"field_{expr.index}"
        return f"{base}.field_{expr.index}"

    if isinstance(expr, ir.ExprSubscript):
        val = _lower_expr(ctx, expr.value)
        if isinstance(expr.slice, ir.ExprSlice):
            # Bit-slice: value[hi:lo]
            lo = _lower_expr(ctx, expr.slice.lower) if expr.slice.lower else "0"
            hi = _lower_expr(ctx, expr.slice.upper) if expr.slice.upper else ""
            return f"{val}[{hi}:{lo}]"
        idx = _lower_expr(ctx, expr.slice)
        return f"{val}[{idx}]"

    if isinstance(expr, ir.ExprSlice):
        # ExprSlice only has lower/upper (no value); value comes from ExprSubscript
        lo = _lower_expr(ctx, expr.lower) if expr.lower else "0"
        hi = _lower_expr(ctx, expr.upper) if expr.upper else ""
        return f"[{hi}:{lo}]"

    if isinstance(expr, ir.ExprCall):
        # Implication: IR stores as ExprCall(func=ExprRefUnresolved(name='implies'), args=[cond, body])
        if (isinstance(expr.func, ir.ExprRefUnresolved)
                and expr.func.name == 'implies'
                and len(expr.args) == 2):
            cond = _lower_expr(ctx, expr.args[0])
            body = _lower_expr(ctx, expr.args[1])
            return f"({cond} -> {body})"
        func = _lower_expr(ctx, expr.func)
        args = ", ".join(_lower_expr(ctx, a) for a in expr.args)
        return f"{func}({args})"

    if isinstance(expr, ir.ExprHierarchical):
        parts = []
        for elem in expr.elements:
            part = elem.name
            if elem.subscript is not None:
                part += f"[{_lower_expr(ctx, elem.subscript)}]"
            parts.append(part)
        return ".".join(parts)

    if isinstance(expr, ir.ExprNull):
        return "null"

    # Fallback
    return f"/* unsupported: {type(expr).__name__} */"


def _lower_range(ctx: LoweringContext, r: ir.ExprRange) -> str:
    """Format a single range expression."""
    lo = _lower_expr(ctx, r.lower)
    if r.upper is not None:
        hi = _lower_expr(ctx, r.upper)
        return f"[{lo}:{hi}]"
    return lo


def _format_constant(expr: ir.ExprConstant) -> str:
    """Format a constant value as an SV literal."""
    v = expr.value
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        if v < 0:
            return str(v)
        return str(v)
    if isinstance(v, str):
        return f'"{v}"'
    return str(v)
