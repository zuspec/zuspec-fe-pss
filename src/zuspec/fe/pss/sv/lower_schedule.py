"""Lower PSS schedule blocks to staged fork/join SV code.

A schedule block is analyzed at lowering time to determine the
execution ordering based on flow-object bindings:
- Buffer/state bindings induce sequential edges (producer before consumer)
- Stream bindings induce concurrent edges (producer || consumer)

The analysis builds a constraint graph, detects conflicts/cycles,
forms concurrent groups, and topologically sorts into stages.
"""
from __future__ import annotations

import dataclasses as dc
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from zuspec.dataclasses import ir

from .lower_activities import _lower_activity_stmt

if TYPE_CHECKING:
    from .context import LoweringContext


class ScheduleError(Exception):
    """Raised when schedule analysis detects a conflict or cycle."""
    pass


@dc.dataclass
class ScheduleNode:
    """A node in the schedule constraint graph.

    Attributes:
        index:     Index of the statement in the schedule block.
        stmt:      The activity statement.
        seq_after: Set of node indices that must execute before this one.
        concurrent_with: Set of node indices that must execute concurrently.
    """
    index: int
    stmt: ir.ActivityStmt
    seq_after: Set[int] = dc.field(default_factory=set)
    concurrent_with: Set[int] = dc.field(default_factory=set)


def analyze_schedule(
    stmts: List[ir.ActivityStmt],
    bindings: Optional[List[Tuple[int, int, str]]] = None,
) -> List[List[int]]:
    """Analyze a schedule block and produce execution stages.

    Args:
        stmts: Activity statements in the schedule block.
        bindings: Optional list of (producer_idx, consumer_idx, kind) tuples
                  where kind is "sequential" or "concurrent". If None, all
                  statements are treated as independent (single concurrent stage).

    Returns:
        List of stages, where each stage is a list of statement indices
        that can execute concurrently. Stages are in topological order.

    Raises:
        ScheduleError: If a cycle is detected or sequential/concurrent conflict.
    """
    n = len(stmts)
    if n == 0:
        return []

    nodes = [ScheduleNode(index=i, stmt=stmts[i]) for i in range(n)]

    if bindings:
        for prod_idx, cons_idx, kind in bindings:
            if kind == "sequential":
                nodes[cons_idx].seq_after.add(prod_idx)
            elif kind == "concurrent":
                nodes[prod_idx].concurrent_with.add(cons_idx)
                nodes[cons_idx].concurrent_with.add(prod_idx)

        # Check for sequential/concurrent conflicts
        for node in nodes:
            conflict = node.seq_after & node.concurrent_with
            if conflict:
                raise ScheduleError(
                    f"Node {node.index} has both sequential and concurrent "
                    f"edges to node(s) {conflict}"
                )

    # Form concurrent groups using Union-Find
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    if bindings:
        for node in nodes:
            for peer in node.concurrent_with:
                union(node.index, peer)

    # Build group map
    groups: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    # Build inter-group dependency graph for topological sort
    group_id = {i: find(i) for i in range(n)}
    unique_groups = list(groups.keys())
    group_order: Dict[int, Set[int]] = defaultdict(set)  # group -> set of predecessor groups

    if bindings:
        for node in nodes:
            my_group = group_id[node.index]
            for pred in node.seq_after:
                pred_group = group_id[pred]
                if pred_group != my_group:
                    group_order[my_group].add(pred_group)

    # Topological sort (Kahn's algorithm)
    in_degree: Dict[int, int] = {g: 0 for g in unique_groups}
    adj: Dict[int, List[int]] = defaultdict(list)
    for g, preds in group_order.items():
        for p in preds:
            adj[p].append(g)
            in_degree[g] += 1

    queue = deque(g for g in unique_groups if in_degree[g] == 0)
    sorted_groups: List[int] = []

    while queue:
        g = queue.popleft()
        sorted_groups.append(g)
        for succ in adj[g]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    if len(sorted_groups) != len(unique_groups):
        raise ScheduleError("Cycle detected in schedule dependency graph")

    # Build stages from sorted groups
    stages: List[List[int]] = []
    for g in sorted_groups:
        stages.append(sorted(groups[g]))

    return stages


def lower_schedule(
    ctx: LoweringContext,
    sched: ir.ActivitySchedule,
    comp_expr: str,
    bindings: Optional[List[Tuple[int, int, str]]] = None,
) -> List[str]:
    """Lower an ActivitySchedule to staged fork/join blocks.

    Args:
        ctx: Lowering context.
        sched: Schedule activity node.
        comp_expr: SV expression for the component.
        bindings: Optional binding constraints. If None, all statements
                  execute in a single concurrent stage.

    Returns:
        List of SV statement lines.
    """
    stmts = sched.stmts
    if not stmts:
        return ["// empty schedule"]

    try:
        stages = analyze_schedule(stmts, bindings)
    except ScheduleError as e:
        return [f'$fatal(1, "schedule error: {e}");']

    lines: List[str] = []

    for stage in stages:
        if len(stage) == 1:
            # Single statement -- execute sequentially
            lines.extend(_lower_activity_stmt(ctx, stmts[stage[0]], comp_expr))
        else:
            # Multiple statements -- fork/join
            lines.append("fork")
            for idx in stage:
                branch_lines = _lower_activity_stmt(ctx, stmts[idx], comp_expr)
                if len(branch_lines) == 1 and not branch_lines[0].startswith("begin"):
                    lines.append("  begin")
                    lines.append(f"    {branch_lines[0]}")
                    lines.append("  end")
                else:
                    for l in branch_lines:
                        lines.append(f"  {l}")
            lines.append("join")

    return lines
