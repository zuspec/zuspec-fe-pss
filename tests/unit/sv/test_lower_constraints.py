"""Tests for PSS constraint lowering to SV constraint strings."""

import pytest
from zuspec.dataclasses import ir

from zuspec.fe.pss.sv.context import LoweringContext
from zuspec.fe.pss.sv.lower_constraints import lower_constraint_func


@pytest.fixture
def ctx():
    return LoweringContext()


def _make_constraint(name, body):
    """Helper to create an IR constraint Function."""
    return ir.Function(
        name=name,
        body=body,
        metadata={"_is_constraint": True},
    )


class TestConstraintExpressions:
    def test_comparison(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprCompare(
                left=ir.ExprRefLocal(name="addr"),
                ops=[ir.CmpOp.GtE],
                comparators=[ir.ExprConstant(value=4096)],
            )),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert len(exprs) == 1
        assert "addr" in exprs[0]
        assert ">=" in exprs[0]
        assert "4096" in exprs[0]

    def test_binary_op(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprBin(
                lhs=ir.ExprRefLocal(name="x"),
                op=ir.BinOp.Add,
                rhs=ir.ExprConstant(value=1),
            )),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert "+" in exprs[0]

    def test_logical_and(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprBool(
                op=ir.BoolOp.And,
                values=[
                    ir.ExprRefLocal(name="a"),
                    ir.ExprRefLocal(name="b"),
                ],
            )),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert "&&" in exprs[0]

    def test_unary_not(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprUnary(
                op=ir.UnaryOp.Not,
                operand=ir.ExprRefLocal(name="valid"),
            )),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert "!" in exprs[0]
        assert "valid" in exprs[0]

    def test_constant_int(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprConstant(value=42)),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert exprs[0] == "42"

    def test_in_range(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprIn(
                value=ir.ExprRefLocal(name="addr"),
                container=ir.ExprRangeList(ranges=[
                    ir.ExprRange(lower=ir.ExprConstant(value=0),
                                 upper=ir.ExprConstant(value=255)),
                ]),
            )),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert "inside" in exprs[0]
        assert "addr" in exprs[0]

    def test_multiple_constraints(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprRefLocal(name="a")),
            ir.StmtExpr(expr=ir.ExprRefLocal(name="b")),
            ir.StmtExpr(expr=ir.ExprRefLocal(name="c")),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert len(exprs) == 3


class TestConstraintControlFlow:
    def test_if_constraint(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtIf(
                test=ir.ExprRefLocal(name="mode"),
                body=[ir.StmtExpr(expr=ir.ExprRefLocal(name="x"))],
            ),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert len(exprs) == 1
        assert "if (mode)" in exprs[0]

    def test_if_else_constraint(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtIf(
                test=ir.ExprRefLocal(name="mode"),
                body=[ir.StmtExpr(expr=ir.ExprRefLocal(name="x"))],
                orelse=[ir.StmtExpr(expr=ir.ExprRefLocal(name="y"))],
            ),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert "if (mode)" in exprs[0]
        assert "else" in exprs[0]

    def test_foreach_constraint(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtForeach(
                target=ir.ExprRefLocal(name="i"),
                iter=ir.ExprRefLocal(name="data"),
                body=[ir.StmtExpr(expr=ir.ExprRefLocal(name="i"))],
            ),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert "foreach" in exprs[0]
        assert "data" in exprs[0]

    def test_unique_constraint(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtUnique(vars=["a", "b", "c"]),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert "unique" in exprs[0]
        assert "a" in exprs[0]


class TestNonConstraint:
    def test_non_constraint_returns_none(self, ctx):
        func = ir.Function(name="body", body=[], metadata={})
        result = lower_constraint_func(ctx, func)
        assert result is None


class TestImplication:
    def test_implication_constraint(self, ctx):
        """Implication is stored as ExprCall(func=ExprRefUnresolved(name='implies'), ...)."""
        func = _make_constraint("impl_c", [
            ir.StmtExpr(expr=ir.ExprCall(
                func=ir.ExprRefUnresolved(name='implies'),
                args=[
                    ir.ExprRefLocal(name="mode"),
                    ir.ExprCompare(
                        left=ir.ExprRefLocal(name="addr"),
                        ops=[ir.CmpOp.Eq],
                        comparators=[ir.ExprConstant(value=0)],
                    ),
                ],
            )),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert len(exprs) == 1
        assert "->" in exprs[0]
        assert "mode" in exprs[0]
        assert "addr" in exprs[0]


class TestExpressionEdgeCases:
    def test_attribute_expr(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprAttribute(
                value=ir.ExprRefLocal(name="pkt"),
                attr="addr",
            )),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert exprs[0] == "pkt.addr"

    def test_subscript_expr(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprSubscript(
                value=ir.ExprRefLocal(name="data"),
                slice=ir.ExprConstant(value=3),
            )),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert exprs[0] == "data[3]"

    def test_slice_expr(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprSubscript(
                value=ir.ExprRefLocal(name="addr"),
                slice=ir.ExprSlice(
                    lower=ir.ExprConstant(value=0),
                    upper=ir.ExprConstant(value=7),
                ),
            )),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert "addr[7:0]" in exprs[0]

    def test_hierarchical_expr(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprHierarchical(
                elements=[
                    ir.ExprHierarchicalElem(name="comp"),
                    ir.ExprHierarchicalElem(name="sub"),
                    ir.ExprHierarchicalElem(name="field"),
                ],
            )),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert exprs[0] == "comp.sub.field"

    def test_null_expr(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprNull()),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert exprs[0] == "null"

    def test_self_ref_stripped(self, ctx):
        """TypeExprRefSelf lowers to empty string, which is filtered out."""
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.TypeExprRefSelf()),
        ])
        exprs = lower_constraint_func(ctx, func)
        # Empty-string results are excluded by the constraint lowering
        assert len(exprs) == 0

    def test_constant_bool(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprConstant(value=True)),
            ir.StmtExpr(expr=ir.ExprConstant(value=False)),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert exprs[0] == "1"
        assert exprs[1] == "0"

    def test_constant_string(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprConstant(value="hello")),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert exprs[0] == '"hello"'

    def test_function_call(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprCall(
                func=ir.ExprRefLocal(name="$clog2"),
                args=[ir.ExprRefLocal(name="size")],
            )),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert "$clog2(size)" in exprs[0]

    def test_in_with_single_value(self, ctx):
        func = _make_constraint("c0", [
            ir.StmtExpr(expr=ir.ExprIn(
                value=ir.ExprRefLocal(name="x"),
                container=ir.ExprRangeList(ranges=[
                    ir.ExprRange(lower=ir.ExprConstant(value=5), upper=None),
                ]),
            )),
        ])
        exprs = lower_constraint_func(ctx, func)
        assert "inside" in exprs[0]
        assert "5" in exprs[0]
