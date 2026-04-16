"""End-to-end tests: control flow constructs.

Verifies that activity control-flow constructs (repeat, foreach,
if/else, select) lower correctly through the full pipeline.
"""

import pytest
from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv_emit import SVEmitter

from zuspec.fe.pss.ast_to_ir import AstToIrContext
from zuspec.fe.pss.sv.pss_to_sv import pss_to_sv
from zuspec.fe.pss.sv.lower_activities import lower_activity
from zuspec.fe.pss.sv.context import LoweringContext


@pytest.fixture
def emitter():
    return SVEmitter()


@pytest.fixture
def ctx():
    return LoweringContext()


class TestRepeat:
    def test_repeat_with_count(self, ctx):
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivityRepeat(
                count=ir.ExprConstant(value=4),
                body=[ir.ActivityAnonTraversal(action_type="my_c::act")],
            ),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)
        assert "repeat (4)" in text
        assert "my_c__act" in text
        assert "randomize()" in text

    def test_repeat_with_index(self, ctx):
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivityRepeat(
                count=ir.ExprConstant(value=8),
                index_var="i",
                body=[ir.ActivityAnonTraversal(action_type="item_act")],
            ),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)
        assert "for (int i = 0; i < 8; i++)" in text

    def test_repeat_in_full_pipeline(self, emitter):
        """Repeat in an action activity -> SV text via full pipeline."""
        action_dt = ir.DataTypeClass(
            name="rep_act", super=None, fields=[],
            activity_ir=ir.ActivitySequenceBlock(stmts=[
                ir.ActivityRepeat(
                    count=ir.ExprConstant(value=3),
                    body=[ir.ActivityAnonTraversal(action_type="inner_act")],
                ),
            ]),
        )
        ir_ctx = AstToIrContext()
        ir_ctx.add_type("rep_act", action_dt)
        sv_nodes = pss_to_sv(ir_ctx)
        text = emitter.emit_all(sv_nodes)
        assert "class rep_act" in text


class TestForeach:
    def test_foreach_basic(self, ctx):
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivityForeach(
                iterator="it",
                collection=ir.ExprRefLocal(name="items"),
                body=[ir.ActivityAnonTraversal(action_type="process_item")],
            ),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)
        assert "foreach (items[it])" in text
        assert "process_item" in text


class TestIfElse:
    def test_if_else_basic(self, ctx):
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivityIfElse(
                condition=ir.ExprRefLocal(name="mode"),
                if_body=[ir.ActivityAnonTraversal(action_type="fast_act")],
                else_body=[ir.ActivityAnonTraversal(action_type="slow_act")],
            ),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)
        assert "if (mode)" in text
        assert "fast_act" in text
        assert "else" in text
        assert "slow_act" in text

    def test_if_no_else(self, ctx):
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivityIfElse(
                condition=ir.ExprRefLocal(name="flag"),
                if_body=[ir.ActivityAnonTraversal(action_type="opt_act")],
                else_body=[],
            ),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)
        assert "if (flag)" in text
        assert "opt_act" in text


class TestSelect:
    def test_weighted_select(self, ctx):
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivitySelect(branches=[
                ir.SelectBranch(
                    weight=ir.ExprConstant(value=3),
                    body=[ir.ActivityAnonTraversal(action_type="common_act")],
                ),
                ir.SelectBranch(
                    weight=ir.ExprConstant(value=1),
                    body=[ir.ActivityAnonTraversal(action_type="rare_act")],
                ),
            ]),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)
        assert "_sel_weights" in text
        assert "3" in text
        assert "1" in text
        assert "common_act" in text
        assert "rare_act" in text
        assert "case" in text

    def test_select_with_guard(self, ctx):
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivitySelect(branches=[
                ir.SelectBranch(
                    weight=None,
                    guard=ir.ExprRefLocal(name="enabled"),
                    body=[ir.ActivityAnonTraversal(action_type="guarded_act")],
                ),
                ir.SelectBranch(
                    weight=None,
                    body=[ir.ActivityAnonTraversal(action_type="fallback_act")],
                ),
            ]),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)
        assert "if (enabled)" in text
        assert "guarded_act" in text
        assert "fallback_act" in text


class TestDoWhile:
    def test_do_while(self, ctx):
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivityDoWhile(
                condition=ir.ExprRefLocal(name="retry"),
                body=[ir.ActivityAnonTraversal(action_type="attempt_act")],
            ),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)
        assert "do begin" in text
        assert "end while (retry);" in text
        assert "attempt_act" in text


class TestWhileDo:
    def test_while_do(self, ctx):
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivityWhileDo(
                condition=ir.ExprRefLocal(name="running"),
                body=[ir.ActivityAnonTraversal(action_type="poll_act")],
            ),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)
        assert "while (running)" in text
        assert "poll_act" in text


class TestMatch:
    def test_match_case(self, ctx):
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivityMatch(
                subject=ir.ExprRefLocal(name="cmd"),
                cases=[
                    ir.MatchCase(
                        pattern=ir.ExprConstant(value=0),
                        body=[ir.ActivityAnonTraversal(action_type="read_act")],
                    ),
                    ir.MatchCase(
                        pattern=ir.ExprConstant(value=1),
                        body=[ir.ActivityAnonTraversal(action_type="write_act")],
                    ),
                ],
            ),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)
        assert "case (cmd)" in text
        assert "0:" in text
        assert "1:" in text
        assert "read_act" in text
        assert "write_act" in text
        assert "endcase" in text


class TestNestedControlFlow:
    def test_if_inside_repeat(self, ctx):
        """Nested control flow: if/else inside repeat."""
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivityRepeat(
                count=ir.ExprConstant(value=5),
                body=[
                    ir.ActivityIfElse(
                        condition=ir.ExprRefLocal(name="flag"),
                        if_body=[ir.ActivityAnonTraversal(action_type="a_act")],
                        else_body=[ir.ActivityAnonTraversal(action_type="b_act")],
                    ),
                ],
            ),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)
        assert "repeat (5)" in text
        assert "if (flag)" in text
        assert "a_act" in text
        assert "b_act" in text

    def test_parallel_inside_sequence(self, ctx):
        """Parallel block inside a sequence."""
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivityAnonTraversal(action_type="setup_act"),
            ir.ActivityParallel(stmts=[
                ir.ActivityAnonTraversal(action_type="branch_a"),
                ir.ActivityAnonTraversal(action_type="branch_b"),
            ]),
            ir.ActivityAnonTraversal(action_type="cleanup_act"),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)

        assert "setup_act" in text
        assert "fork" in text
        assert "branch_a" in text
        assert "branch_b" in text
        assert "join" in text
        assert "cleanup_act" in text

        # Order: setup before fork, fork before cleanup
        assert text.index("setup_act") < text.index("fork")
        assert text.index("join") < text.index("cleanup_act")
