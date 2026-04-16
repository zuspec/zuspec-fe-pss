"""Lower PSS activity IR to SV task body lines.

Walks the activity IR tree and produces SV task body lines (strings).
Each activity IR node maps to a SV code pattern as specified in the
design document.
"""
from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv import SVLineDirective

from .lower_exprs import lower_expr

if TYPE_CHECKING:
    from .context import LoweringContext


def lower_activity(
    ctx: LoweringContext,
    activity: ir.ActivitySequenceBlock,
    comp_expr: str = "comp",
) -> List[str]:
    """Lower an activity sequence block to SV task body lines.

    Args:
        ctx: Lowering context.
        activity: The top-level activity sequence block.
        comp_expr: SV expression for the component reference.

    Returns:
        List of SV statement lines forming the activity task body.
    """
    lines: List[str] = []
    for stmt in activity.stmts:
        lines.extend(_lower_activity_stmt(ctx, stmt, comp_expr))
    return lines


def _lower_activity_stmt(
    ctx: LoweringContext,
    stmt: ir.ActivityStmt,
    comp_expr: str,
) -> List[str]:
    """Lower a single activity statement to SV lines."""

    if isinstance(stmt, ir.ActivitySequenceBlock):
        lines: List[str] = ["begin"]
        for s in stmt.stmts:
            for l in _lower_activity_stmt(ctx, s, comp_expr):
                lines.append(f"  {l}")
        lines.append("end")
        return lines

    if isinstance(stmt, ir.ActivityTraversal):
        return _lower_traversal(ctx, stmt, comp_expr)

    if isinstance(stmt, ir.ActivityAnonTraversal):
        return _lower_anon_traversal(ctx, stmt, comp_expr)

    if isinstance(stmt, ir.ActivityRepeat):
        return _lower_repeat(ctx, stmt, comp_expr)

    if isinstance(stmt, ir.ActivityDoWhile):
        return _lower_do_while(ctx, stmt, comp_expr)

    if isinstance(stmt, ir.ActivityWhileDo):
        return _lower_while_do(ctx, stmt, comp_expr)

    if isinstance(stmt, ir.ActivityForeach):
        return _lower_foreach(ctx, stmt, comp_expr)

    if isinstance(stmt, ir.ActivityIfElse):
        return _lower_if_else(ctx, stmt, comp_expr)

    if isinstance(stmt, ir.ActivityMatch):
        return _lower_match(ctx, stmt, comp_expr)

    if isinstance(stmt, ir.ActivitySelect):
        return _lower_select(ctx, stmt, comp_expr)

    if isinstance(stmt, ir.ActivityAtomic):
        return _lower_atomic(ctx, stmt, comp_expr)

    if isinstance(stmt, ir.ActivitySuper):
        return ["super.activity();"]

    if isinstance(stmt, ir.ActivityParallel):
        return _lower_parallel(ctx, stmt, comp_expr)

    if isinstance(stmt, ir.ActivityConstraint):
        # Inline constraints in activity context are informational
        return [f"// activity constraint (handled at randomize time)"]

    if isinstance(stmt, ir.ActivityBind):
        src = lower_expr(ctx, stmt.src)
        dst = lower_expr(ctx, stmt.dst)
        return [f"// bind {src} -> {dst}"]

    return [f"// unsupported activity: {type(stmt).__name__}"]


def _lower_traversal(
    ctx: LoweringContext,
    trav: ir.ActivityTraversal,
    comp_expr: str,
) -> List[str]:
    """Lower a named handle traversal to the full lifecycle pattern.

    Pattern:
        begin
            act.comp = <comp_expr>;
            act.pre_solve();
            if (!act.randomize() [with { ... }])
                $fatal(1, "randomize failed: <handle>");
            act.post_solve();
            act.body();
        end
    """
    handle = trav.handle
    lines = ["begin"]

    # Source location tracking
    if hasattr(trav, 'loc') and trav.loc is not None:
        lines.insert(0, f'// traversal: {handle}')

    lines.append(f"  {handle}.comp = {comp_expr};")
    lines.append(f"  {handle}.pre_solve();")

    # Randomize with optional inline constraints
    if trav.inline_constraints:
        constraint_strs = [lower_expr(ctx, c) for c in trav.inline_constraints]
        with_body = "; ".join(constraint_strs)
        lines.append(f"  if (!{handle}.randomize() with {{ {with_body}; }})")
    else:
        lines.append(f"  if (!{handle}.randomize())")
    lines.append(f'    $fatal(1, "randomize failed: {handle}");')

    lines.append(f"  {handle}.post_solve();")
    lines.append(f"  {handle}.body();")
    lines.append("end")
    return lines


def _lower_anon_traversal(
    ctx: LoweringContext,
    trav: ir.ActivityAnonTraversal,
    comp_expr: str,
) -> List[str]:
    """Lower an anonymous traversal (do Type) to the full lifecycle.

    Pattern:
        begin
            TypeName act = new();
            act.comp = <comp_expr>;
            act.pre_solve();
            if (!act.randomize() [with { ... }])
                $fatal(1, "randomize failed: TypeName");
            act.post_solve();
            act.body();
        end
    """
    type_name = ctx.mangle_name(trav.action_type)
    var_name = trav.label if trav.label else f"_anon_{type_name}"

    lines = ["begin"]
    lines.append(f"  {type_name} {var_name} = new();")
    lines.append(f"  {var_name}.comp = {comp_expr};")
    lines.append(f"  {var_name}.pre_solve();")

    if trav.inline_constraints:
        constraint_strs = [lower_expr(ctx, c) for c in trav.inline_constraints]
        with_body = "; ".join(constraint_strs)
        lines.append(f"  if (!{var_name}.randomize() with {{ {with_body}; }})")
    else:
        lines.append(f"  if (!{var_name}.randomize())")
    lines.append(f'    $fatal(1, "randomize failed: {type_name}");')

    lines.append(f"  {var_name}.post_solve();")
    lines.append(f"  {var_name}.body();")
    lines.append("end")
    return lines


def _lower_repeat(
    ctx: LoweringContext,
    repeat: ir.ActivityRepeat,
    comp_expr: str,
) -> List[str]:
    """Lower ActivityRepeat to ``repeat (N) begin ... end``."""
    count = lower_expr(ctx, repeat.count)
    if repeat.index_var:
        lines = [f"for (int {repeat.index_var} = 0; {repeat.index_var} < {count}; {repeat.index_var}++) begin"]
    else:
        lines = [f"repeat ({count}) begin"]
    for s in repeat.body:
        for l in _lower_activity_stmt(ctx, s, comp_expr):
            lines.append(f"  {l}")
    lines.append("end")
    return lines


def _lower_do_while(
    ctx: LoweringContext,
    dw: ir.ActivityDoWhile,
    comp_expr: str,
) -> List[str]:
    """Lower ActivityDoWhile to ``do begin ... end while (cond);``."""
    cond = lower_expr(ctx, dw.condition)
    lines = ["do begin"]
    for s in dw.body:
        for l in _lower_activity_stmt(ctx, s, comp_expr):
            lines.append(f"  {l}")
    lines.append(f"end while ({cond});")
    return lines


def _lower_while_do(
    ctx: LoweringContext,
    wd: ir.ActivityWhileDo,
    comp_expr: str,
) -> List[str]:
    """Lower ActivityWhileDo to ``while (cond) begin ... end``."""
    cond = lower_expr(ctx, wd.condition)
    lines = [f"while ({cond}) begin"]
    for s in wd.body:
        for l in _lower_activity_stmt(ctx, s, comp_expr):
            lines.append(f"  {l}")
    lines.append("end")
    return lines


def _lower_foreach(
    ctx: LoweringContext,
    fe: ir.ActivityForeach,
    comp_expr: str,
) -> List[str]:
    """Lower ActivityForeach to ``foreach (collection[iter]) begin ... end``."""
    collection = lower_expr(ctx, fe.collection)
    lines = [f"foreach ({collection}[{fe.iterator}]) begin"]
    for s in fe.body:
        for l in _lower_activity_stmt(ctx, s, comp_expr):
            lines.append(f"  {l}")
    lines.append("end")
    return lines


def _lower_if_else(
    ctx: LoweringContext,
    ie: ir.ActivityIfElse,
    comp_expr: str,
) -> List[str]:
    """Lower ActivityIfElse to ``if (cond) begin ... end else begin ... end``."""
    cond = lower_expr(ctx, ie.condition)
    lines = [f"if ({cond}) begin"]
    for s in ie.if_body:
        for l in _lower_activity_stmt(ctx, s, comp_expr):
            lines.append(f"  {l}")
    if ie.else_body:
        lines.append("end else begin")
        for s in ie.else_body:
            for l in _lower_activity_stmt(ctx, s, comp_expr):
                lines.append(f"  {l}")
    lines.append("end")
    return lines


def _lower_match(
    ctx: LoweringContext,
    match: ir.ActivityMatch,
    comp_expr: str,
) -> List[str]:
    """Lower ActivityMatch to ``case (subject) ... endcase``."""
    subj = lower_expr(ctx, match.subject)
    lines = [f"case ({subj})"]
    for case in match.cases:
        pat = lower_expr(ctx, case.pattern)
        lines.append(f"  {pat}: begin")
        for s in case.body:
            for l in _lower_activity_stmt(ctx, s, comp_expr):
                lines.append(f"    {l}")
        lines.append("  end")
    lines.append("endcase")
    return lines


def _lower_select(
    ctx: LoweringContext,
    sel: ir.ActivitySelect,
    comp_expr: str,
) -> List[str]:
    """Lower ActivitySelect to weighted random branch selection.

    Pattern:
        begin
            int _sel_idx;
            int _weights[N] = '{w0, w1, ...};
            // compute cumulative weights, pick random
            _sel_idx = ...;
            case (_sel_idx)
                0: begin ... end
                1: begin ... end
                ...
            endcase
        end
    """
    n = len(sel.branches)
    if n == 0:
        return ["// empty select"]

    lines = ["begin"]

    # Build weight array
    weights = []
    for b in sel.branches:
        if b.weight is not None:
            weights.append(lower_expr(ctx, b.weight))
        else:
            weights.append("1")

    lines.append(f"  int _sel_weights [{n}] = '{{ {', '.join(weights)} }};")
    lines.append(f"  int _sel_total = 0;")
    lines.append(f"  int _sel_idx;")
    lines.append(f"  int _sel_pick;")

    # Sum weights
    lines.append(f"  for (int _i = 0; _i < {n}; _i++)")
    lines.append(f"    _sel_total += _sel_weights[_i];")

    # Random pick
    lines.append(f"  _sel_pick = $urandom_range(0, _sel_total - 1);")
    lines.append(f"  _sel_idx = 0;")
    lines.append(f"  for (int _i = 0; _i < {n}; _i++) begin")
    lines.append(f"    if (_sel_pick < _sel_weights[_i]) begin")
    lines.append(f"      _sel_idx = _i;")
    lines.append(f"      break;")
    lines.append(f"    end")
    lines.append(f"    _sel_pick -= _sel_weights[_i];")
    lines.append(f"  end")

    # Branch execution with optional guards
    lines.append(f"  case (_sel_idx)")
    for i, branch in enumerate(sel.branches):
        if branch.guard is not None:
            guard = lower_expr(ctx, branch.guard)
            lines.append(f"    {i}: if ({guard}) begin")
        else:
            lines.append(f"    {i}: begin")
        for s in branch.body:
            for l in _lower_activity_stmt(ctx, s, comp_expr):
                lines.append(f"      {l}")
        lines.append(f"    end")
    lines.append(f"  endcase")
    lines.append("end")
    return lines


def _lower_atomic(
    ctx: LoweringContext,
    atomic: ir.ActivityAtomic,
    comp_expr: str,
) -> List[str]:
    """Lower ActivityAtomic with semaphore get/put around body."""
    lines = [f"{comp_expr}.atomic_sem.get(1);"]
    lines.append("begin")
    for s in atomic.stmts:
        for l in _lower_activity_stmt(ctx, s, comp_expr):
            lines.append(f"  {l}")
    lines.append("end")
    lines.append(f"{comp_expr}.atomic_sem.put(1);")
    return lines


def _lower_parallel(
    ctx: LoweringContext,
    par: ir.ActivityParallel,
    comp_expr: str,
) -> List[str]:
    """Lower ActivityParallel to ``fork ... join``.

    Join semantics depend on join_spec (Phase 5 handles complex cases;
    Phase 4 implements basic fork/join).
    """
    join_kw = "join"
    if par.join_spec is not None:
        kind = par.join_spec.kind
        if kind == "none":
            join_kw = "join_none"
        elif kind == "first":
            join_kw = "join_any"
        # "all" (default) -> join

    lines = ["fork"]
    for i, s in enumerate(par.stmts):
        branch_lines = _lower_activity_stmt(ctx, s, comp_expr)
        # Wrap each branch in begin/end if not already
        if len(branch_lines) == 1 and not branch_lines[0].startswith("begin"):
            lines.append(f"  begin")
            lines.append(f"    {branch_lines[0]}")
            lines.append(f"  end")
        else:
            for l in branch_lines:
                lines.append(f"  {l}")
    lines.append(join_kw)
    return lines
