"""Tests for general-purpose expression lowering to SV strings."""

import pytest
from zuspec.dataclasses import ir

from zuspec.fe.pss.sv.context import LoweringContext
from zuspec.fe.pss.sv.lower_exprs import lower_expr


@pytest.fixture
def ctx():
    return LoweringContext()


class TestBinaryOps:
    def test_add(self, ctx):
        e = ir.ExprBin(lhs=ir.ExprRefLocal(name="a"), op=ir.BinOp.Add, rhs=ir.ExprConstant(value=1))
        assert lower_expr(ctx, e) == "(a + 1)"

    def test_sub(self, ctx):
        e = ir.ExprBin(lhs=ir.ExprRefLocal(name="x"), op=ir.BinOp.Sub, rhs=ir.ExprRefLocal(name="y"))
        assert lower_expr(ctx, e) == "(x - y)"

    def test_mult(self, ctx):
        e = ir.ExprBin(lhs=ir.ExprRefLocal(name="a"), op=ir.BinOp.Mult, rhs=ir.ExprConstant(value=2))
        assert lower_expr(ctx, e) == "(a * 2)"

    def test_bitwise_and(self, ctx):
        e = ir.ExprBin(lhs=ir.ExprRefLocal(name="a"), op=ir.BinOp.BitAnd, rhs=ir.ExprConstant(value=0xFF))
        assert lower_expr(ctx, e) == "(a & 255)"

    def test_shift_left(self, ctx):
        e = ir.ExprBin(lhs=ir.ExprRefLocal(name="a"), op=ir.BinOp.LShift, rhs=ir.ExprConstant(value=4))
        assert lower_expr(ctx, e) == "(a << 4)"


class TestComparisons:
    def test_eq(self, ctx):
        e = ir.ExprCompare(
            left=ir.ExprRefLocal(name="x"),
            ops=[ir.CmpOp.Eq],
            comparators=[ir.ExprConstant(value=0)],
        )
        assert lower_expr(ctx, e) == "(x == 0)"

    def test_chain(self, ctx):
        e = ir.ExprCompare(
            left=ir.ExprRefLocal(name="x"),
            ops=[ir.CmpOp.GtE, ir.CmpOp.LtE],
            comparators=[ir.ExprConstant(value=0), ir.ExprConstant(value=100)],
        )
        result = lower_expr(ctx, e)
        assert ">=" in result
        assert "<=" in result


class TestBoolOps:
    def test_and(self, ctx):
        e = ir.ExprBool(op=ir.BoolOp.And, values=[ir.ExprRefLocal(name="a"), ir.ExprRefLocal(name="b")])
        assert lower_expr(ctx, e) == "a && b"

    def test_or(self, ctx):
        e = ir.ExprBool(op=ir.BoolOp.Or, values=[ir.ExprRefLocal(name="a"), ir.ExprRefLocal(name="b")])
        assert lower_expr(ctx, e) == "a || b"


class TestUnaryOps:
    def test_not(self, ctx):
        e = ir.ExprUnary(op=ir.UnaryOp.Not, operand=ir.ExprRefLocal(name="valid"))
        assert lower_expr(ctx, e) == "!(valid)"

    def test_invert(self, ctx):
        e = ir.ExprUnary(op=ir.UnaryOp.Invert, operand=ir.ExprRefLocal(name="mask"))
        assert lower_expr(ctx, e) == "~(mask)"

    def test_negate(self, ctx):
        e = ir.ExprUnary(op=ir.UnaryOp.USub, operand=ir.ExprRefLocal(name="val"))
        assert lower_expr(ctx, e) == "-(val)"


class TestReferences:
    def test_local_ref(self, ctx):
        e = ir.ExprRefLocal(name="my_var")
        assert lower_expr(ctx, e) == "my_var"

    def test_self_ref(self, ctx):
        e = ir.TypeExprRefSelf()
        assert lower_expr(ctx, e) == "this"

    def test_attribute(self, ctx):
        e = ir.ExprAttribute(value=ir.ExprRefLocal(name="pkt"), attr="addr")
        assert lower_expr(ctx, e) == "pkt.addr"

    def test_attribute_on_self(self, ctx):
        """self.field -> field (self stripped to empty)."""
        e = ir.ExprAttribute(value=ir.TypeExprRefSelf(), attr="data")
        # TypeExprRefSelf -> "this", so this.data
        assert lower_expr(ctx, e) == "data"

    def test_subscript(self, ctx):
        e = ir.ExprSubscript(value=ir.ExprRefLocal(name="arr"), slice=ir.ExprConstant(value=3))
        assert lower_expr(ctx, e) == "arr[3]"

    def test_bit_slice(self, ctx):
        e = ir.ExprSubscript(
            value=ir.ExprRefLocal(name="reg"),
            slice=ir.ExprSlice(lower=ir.ExprConstant(value=0), upper=ir.ExprConstant(value=7)),
        )
        assert lower_expr(ctx, e) == "reg[7:0]"

    def test_hierarchical(self, ctx):
        e = ir.ExprHierarchical(elements=[
            ir.ExprHierarchicalElem(name="comp"),
            ir.ExprHierarchicalElem(name="sub"),
            ir.ExprHierarchicalElem(name="field"),
        ])
        assert lower_expr(ctx, e) == "comp.sub.field"

    def test_hierarchical_with_subscript(self, ctx):
        e = ir.ExprHierarchical(elements=[
            ir.ExprHierarchicalElem(name="arr", subscript=ir.ExprConstant(value=2)),
            ir.ExprHierarchicalElem(name="data"),
        ])
        assert lower_expr(ctx, e) == "arr[2].data"


class TestConstants:
    def test_int(self, ctx):
        assert lower_expr(ctx, ir.ExprConstant(value=42)) == "42"

    def test_negative_int(self, ctx):
        assert lower_expr(ctx, ir.ExprConstant(value=-5)) == "-5"

    def test_bool_true(self, ctx):
        assert lower_expr(ctx, ir.ExprConstant(value=True)) == "1'b1"

    def test_bool_false(self, ctx):
        assert lower_expr(ctx, ir.ExprConstant(value=False)) == "1'b0"

    def test_string(self, ctx):
        assert lower_expr(ctx, ir.ExprConstant(value="hello")) == '"hello"'

    def test_null(self, ctx):
        assert lower_expr(ctx, ir.ExprNull()) == "null"


class TestFunctionCalls:
    def test_simple_call(self, ctx):
        e = ir.ExprCall(func=ir.ExprRefLocal(name="func"), args=[ir.ExprConstant(value=1)])
        assert lower_expr(ctx, e) == "func(1)"

    def test_call_no_args(self, ctx):
        e = ir.ExprCall(func=ir.ExprRefLocal(name="get_val"), args=[])
        assert lower_expr(ctx, e) == "get_val()"

    def test_implication(self, ctx):
        e = ir.ExprCall(
            func=ir.ExprRefUnresolved(name='implies'),
            args=[ir.ExprRefLocal(name="cond"), ir.ExprRefLocal(name="body")],
        )
        assert lower_expr(ctx, e) == "(cond -> body)"

    def test_await(self, ctx):
        e = ir.ExprAwait(value=ir.ExprCall(func=ir.ExprRefLocal(name="read"), args=[]))
        assert lower_expr(ctx, e) == "read()"
