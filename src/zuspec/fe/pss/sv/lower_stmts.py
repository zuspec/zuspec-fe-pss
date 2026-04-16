"""Lower Zuspec IR statements to SV statement strings.

Translates IR statement nodes (StmtAssign, StmtIf, StmtWhile, etc.)
to SV statement strings. Used for exec block bodies (body, pre_solve,
post_solve, init_down).
"""
from __future__ import annotations

from typing import List, TYPE_CHECKING

from zuspec.dataclasses import ir

from .lower_exprs import lower_expr, _AUGOP_MAP

if TYPE_CHECKING:
    from .context import LoweringContext


def lower_stmts(ctx: LoweringContext, stmts: List[ir.Stmt]) -> List[str]:
    """Lower a list of IR statements to SV statement strings.

    Returns a flat list of SV lines (no trailing semicolons on block
    constructs; semicolons on simple statements).
    """
    lines: List[str] = []
    for stmt in stmts:
        lines.extend(lower_stmt(ctx, stmt))
    return lines


def lower_stmt(ctx: LoweringContext, stmt: ir.Stmt) -> List[str]:
    """Lower a single IR statement to SV statement line(s)."""

    if isinstance(stmt, ir.StmtExpr):
        expr_str = lower_expr(ctx, stmt.expr)
        if expr_str:
            return [f"{expr_str};"]
        return []

    if isinstance(stmt, ir.StmtAssign):
        val = lower_expr(ctx, stmt.value)
        targets = [lower_expr(ctx, t) for t in stmt.targets]
        lines = []
        for t in targets:
            lines.append(f"{t} = {val};")
        return lines

    if isinstance(stmt, ir.StmtAugAssign):
        target = lower_expr(ctx, stmt.target)
        val = lower_expr(ctx, stmt.value)
        op = _AUGOP_MAP.get(stmt.op, "+=")
        return [f"{target} {op} {val};"]

    if isinstance(stmt, ir.StmtReturn):
        if stmt.value is not None:
            val = lower_expr(ctx, stmt.value)
            return [f"return {val};"]
        return ["return;"]

    if isinstance(stmt, ir.StmtIf):
        cond = lower_expr(ctx, stmt.test)
        lines = [f"if ({cond}) begin"]
        for s in stmt.body:
            for l in lower_stmt(ctx, s):
                lines.append(f"  {l}")
        if stmt.orelse:
            lines.append("end else begin")
            for s in stmt.orelse:
                for l in lower_stmt(ctx, s):
                    lines.append(f"  {l}")
        lines.append("end")
        return lines

    if isinstance(stmt, ir.StmtWhile):
        cond = lower_expr(ctx, stmt.test)
        lines = [f"while ({cond}) begin"]
        for s in stmt.body:
            for l in lower_stmt(ctx, s):
                lines.append(f"  {l}")
        lines.append("end")
        return lines

    if isinstance(stmt, ir.StmtFor):
        # StmtFor maps to a foreach or counted loop depending on context
        target = lower_expr(ctx, stmt.target)
        iter_expr = lower_expr(ctx, stmt.iter)
        lines = [f"foreach ({iter_expr}[{target}]) begin"]
        for s in stmt.body:
            for l in lower_stmt(ctx, s):
                lines.append(f"  {l}")
        lines.append("end")
        return lines

    if isinstance(stmt, ir.StmtForeach):
        target = lower_expr(ctx, stmt.target)
        collection = lower_expr(ctx, stmt.iter)
        lines = [f"foreach ({collection}[{target}]) begin"]
        for s in stmt.body:
            for l in lower_stmt(ctx, s):
                lines.append(f"  {l}")
        lines.append("end")
        return lines

    if isinstance(stmt, ir.StmtRepeat):
        count = lower_expr(ctx, stmt.count)
        lines = [f"repeat ({count}) begin"]
        for s in stmt.body:
            for l in lower_stmt(ctx, s):
                lines.append(f"  {l}")
        lines.append("end")
        return lines

    if isinstance(stmt, ir.StmtRepeatWhile):
        cond = lower_expr(ctx, stmt.condition)
        lines = ["do begin"]
        for s in stmt.body:
            for l in lower_stmt(ctx, s):
                lines.append(f"  {l}")
        lines.append(f"end while ({cond});")
        return lines

    if isinstance(stmt, ir.StmtBreak):
        return ["break;"]

    if isinstance(stmt, ir.StmtContinue):
        return ["continue;"]

    if isinstance(stmt, ir.StmtPass):
        return []  # No SV equivalent; omit

    if isinstance(stmt, ir.StmtRaise):
        if stmt.exc is not None:
            msg = lower_expr(ctx, stmt.exc)
            return [f'$fatal(1, {msg});']
        return ['$fatal(1, "error");']

    if isinstance(stmt, ir.StmtAssert):
        cond = lower_expr(ctx, stmt.test)
        if stmt.msg is not None:
            msg = lower_expr(ctx, stmt.msg)
            return [f"assert ({cond}) else $error({msg});"]
        return [f"assert ({cond});"]

    if isinstance(stmt, ir.StmtMatch):
        subj = lower_expr(ctx, stmt.subject)
        lines = [f"case ({subj})"]
        for case in stmt.cases:
            pat = _lower_pattern(ctx, case.pattern)
            lines.append(f"  {pat}: begin")
            for s in case.body:
                for l in lower_stmt(ctx, s):
                    lines.append(f"    {l}")
            lines.append("  end")
        lines.append("endcase")
        return lines

    # Fallback
    return [f"// unsupported stmt: {type(stmt).__name__}"]


def _lower_pattern(ctx: LoweringContext, pattern: ir.Pattern) -> str:
    """Lower a match pattern to an SV case label."""
    if isinstance(pattern, ir.PatternValue):
        return lower_expr(ctx, pattern.value)
    if isinstance(pattern, ir.PatternAs):
        if pattern.pattern is None:
            return "default"
        return _lower_pattern(ctx, pattern.pattern)
    if isinstance(pattern, ir.PatternOr):
        parts = [_lower_pattern(ctx, p) for p in pattern.patterns]
        return ", ".join(parts)
    return "default"
