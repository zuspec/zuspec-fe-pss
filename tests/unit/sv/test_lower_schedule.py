"""Tests for schedule block analysis and lowering."""

import pytest
from zuspec.dataclasses import ir

from zuspec.fe.pss.sv.context import LoweringContext
from zuspec.fe.pss.sv.lower_schedule import analyze_schedule, lower_schedule, ScheduleError


@pytest.fixture
def ctx():
    return LoweringContext()


class TestAnalyzeSchedule:
    def test_no_bindings_single_stage(self):
        stmts = [ir.ActivityTraversal(handle="a1"), ir.ActivityTraversal(handle="a2")]
        stages = analyze_schedule(stmts)
        # No bindings: each statement in its own stage (independent)
        assert len(stages) == 2

    def test_sequential_binding(self):
        stmts = [
            ir.ActivityTraversal(handle="producer"),
            ir.ActivityTraversal(handle="consumer"),
        ]
        bindings = [(0, 1, "sequential")]  # producer before consumer
        stages = analyze_schedule(stmts, bindings)
        assert len(stages) == 2
        assert stages[0] == [0]
        assert stages[1] == [1]

    def test_concurrent_binding(self):
        stmts = [
            ir.ActivityTraversal(handle="a1"),
            ir.ActivityTraversal(handle="a2"),
        ]
        bindings = [(0, 1, "concurrent")]
        stages = analyze_schedule(stmts, bindings)
        # Both should be in same stage
        assert len(stages) == 1
        assert sorted(stages[0]) == [0, 1]

    def test_mixed_bindings(self):
        stmts = [
            ir.ActivityTraversal(handle="a0"),
            ir.ActivityTraversal(handle="a1"),
            ir.ActivityTraversal(handle="a2"),
        ]
        # a0 before a1, a1 concurrent with a2
        bindings = [(0, 1, "sequential"), (1, 2, "concurrent")]
        stages = analyze_schedule(stmts, bindings)
        assert len(stages) == 2
        assert stages[0] == [0]
        assert sorted(stages[1]) == [1, 2]

    def test_cycle_detection(self):
        stmts = [ir.ActivityTraversal(handle="a0"), ir.ActivityTraversal(handle="a1")]
        bindings = [(0, 1, "sequential"), (1, 0, "sequential")]
        with pytest.raises(ScheduleError, match="Cycle"):
            analyze_schedule(stmts, bindings)

    def test_conflict_detection(self):
        stmts = [ir.ActivityTraversal(handle="a0"), ir.ActivityTraversal(handle="a1")]
        bindings = [(0, 1, "sequential"), (0, 1, "concurrent")]
        with pytest.raises(ScheduleError, match="sequential and concurrent"):
            analyze_schedule(stmts, bindings)

    def test_empty_schedule(self):
        assert analyze_schedule([]) == []

    def test_three_stage_chain(self):
        stmts = [
            ir.ActivityTraversal(handle="a0"),
            ir.ActivityTraversal(handle="a1"),
            ir.ActivityTraversal(handle="a2"),
        ]
        bindings = [(0, 1, "sequential"), (1, 2, "sequential")]
        stages = analyze_schedule(stmts, bindings)
        assert len(stages) == 3
        assert stages[0] == [0]
        assert stages[1] == [1]
        assert stages[2] == [2]


class TestLowerSchedule:
    def test_single_stmt(self, ctx):
        sched = ir.ActivitySchedule(stmts=[ir.ActivityTraversal(handle="a1")])
        lines = lower_schedule(ctx, sched, "comp")
        text = "\n".join(lines)
        assert "a1.body();" in text

    def test_concurrent_stage_fork_join(self, ctx):
        sched = ir.ActivitySchedule(stmts=[
            ir.ActivityTraversal(handle="a1"),
            ir.ActivityTraversal(handle="a2"),
        ])
        bindings = [(0, 1, "concurrent")]
        lines = lower_schedule(ctx, sched, "comp", bindings)
        text = "\n".join(lines)
        assert "fork" in text
        assert "join" in text
        assert "a1.body();" in text
        assert "a2.body();" in text

    def test_sequential_stages_no_fork(self, ctx):
        sched = ir.ActivitySchedule(stmts=[
            ir.ActivityTraversal(handle="producer"),
            ir.ActivityTraversal(handle="consumer"),
        ])
        bindings = [(0, 1, "sequential")]
        lines = lower_schedule(ctx, sched, "comp", bindings)
        text = "\n".join(lines)
        assert "fork" not in text  # Sequential stages don't need fork
        assert "producer.body();" in text
        assert "consumer.body();" in text
        # Producer should come before consumer
        assert text.index("producer.body()") < text.index("consumer.body()")

    def test_empty_schedule(self, ctx):
        sched = ir.ActivitySchedule(stmts=[])
        lines = lower_schedule(ctx, sched, "comp")
        assert "empty schedule" in "\n".join(lines)
