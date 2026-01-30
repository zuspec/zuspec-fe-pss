"""
Unit tests for expression IR classes
Tests the new expression types added in Phase 1
"""
import pytest
from zuspec.dataclasses import ir


class TestExprRange:
    """Test ExprRange IR class"""
    
    def test_single_value(self):
        """Test single value range (no upper bound)"""
        expr = ir.ExprRange(lower=ir.ExprConstant(value=42))
        assert expr.lower.value == 42
        assert expr.upper is None
    
    def test_bounded_range(self):
        """Test bounded range [lo..hi]"""
        expr = ir.ExprRange(
            lower=ir.ExprConstant(value=1),
            upper=ir.ExprConstant(value=10)
        )
        assert expr.lower.value == 1
        assert expr.upper.value == 10
    
    def test_range_with_expressions(self):
        """Test range with complex expressions"""
        expr = ir.ExprRange(
            lower=ir.ExprBin(
                lhs=ir.ExprConstant(value=5),
                op=ir.BinOp.Sub,
                rhs=ir.ExprConstant(value=2)
            ),
            upper=ir.ExprConstant(value=10)
        )
        assert expr.lower.op == ir.BinOp.Sub
        assert expr.upper.value == 10


class TestExprRangeList:
    """Test ExprRangeList IR class"""
    
    def test_empty_range_list(self):
        """Test empty range list"""
        expr = ir.ExprRangeList(ranges=[])
        assert len(expr.ranges) == 0
    
    def test_single_range(self):
        """Test range list with one range"""
        expr = ir.ExprRangeList(ranges=[
            ir.ExprRange(
                lower=ir.ExprConstant(value=1),
                upper=ir.ExprConstant(value=10)
            )
        ])
        assert len(expr.ranges) == 1
        assert expr.ranges[0].lower.value == 1
        assert expr.ranges[0].upper.value == 10
    
    def test_mixed_ranges_and_values(self):
        """Test {[1..10], 20, [30..40]}"""
        expr = ir.ExprRangeList(ranges=[
            ir.ExprRange(lower=ir.ExprConstant(value=1), upper=ir.ExprConstant(value=10)),
            ir.ExprRange(lower=ir.ExprConstant(value=20), upper=None),
            ir.ExprRange(lower=ir.ExprConstant(value=30), upper=ir.ExprConstant(value=40))
        ])
        assert len(expr.ranges) == 3
        assert expr.ranges[0].upper.value == 10  # Range
        assert expr.ranges[1].upper is None      # Single value
        assert expr.ranges[2].upper.value == 40  # Range


class TestExprIn:
    """Test ExprIn (membership test) IR class"""
    
    def test_in_range_list(self):
        """Test: x in [0..10]"""
        expr = ir.ExprIn(
            value=ir.ExprRefLocal(name="x"),
            container=ir.ExprRangeList(ranges=[
                ir.ExprRange(
                    lower=ir.ExprConstant(value=0),
                    upper=ir.ExprConstant(value=10)
                )
            ])
        )
        assert isinstance(expr.value, ir.ExprRefLocal)
        assert isinstance(expr.container, ir.ExprRangeList)
        assert len(expr.container.ranges) == 1
    
    def test_in_list(self):
        """Test: status in {IDLE, READY, DONE}"""
        expr = ir.ExprIn(
            value=ir.ExprRefLocal(name="status"),
            container=ir.ExprList(elts=[
                ir.ExprConstant(value="IDLE"),
                ir.ExprConstant(value="READY"),
                ir.ExprConstant(value="DONE")
            ])
        )
        assert isinstance(expr.container, ir.ExprList)
        assert len(expr.container.elts) == 3


class TestExprIfExp:
    """Test ExprIfExp (ternary/conditional) IR class"""
    
    def test_simple_ternary(self):
        """Test: x > 0 ? x : -x"""
        expr = ir.ExprIfExp(
            test=ir.ExprCompare(
                left=ir.ExprRefLocal(name="x"),
                ops=[ir.CmpOp.Gt],
                comparators=[ir.ExprConstant(value=0)]
            ),
            body=ir.ExprRefLocal(name="x"),
            orelse=ir.ExprUnary(op=ir.UnaryOp.USub, operand=ir.ExprRefLocal(name="x"))
        )
        assert isinstance(expr.test, ir.ExprCompare)
        assert isinstance(expr.body, ir.ExprRefLocal)
        assert isinstance(expr.orelse, ir.ExprUnary)
    
    def test_nested_ternary(self):
        """Test nested ternary expressions"""
        expr = ir.ExprIfExp(
            test=ir.ExprConstant(value=True),
            body=ir.ExprConstant(value=1),
            orelse=ir.ExprIfExp(
                test=ir.ExprConstant(value=False),
                body=ir.ExprConstant(value=2),
                orelse=ir.ExprConstant(value=3)
            )
        )
        assert isinstance(expr.orelse, ir.ExprIfExp)


class TestExprList:
    """Test ExprList (array/list literal) IR class"""
    
    def test_empty_list(self):
        """Test empty list: []"""
        expr = ir.ExprList(elts=[])
        assert len(expr.elts) == 0
    
    def test_integer_list(self):
        """Test: [1, 2, 3, 4, 5]"""
        expr = ir.ExprList(elts=[
            ir.ExprConstant(value=i) for i in range(1, 6)
        ])
        assert len(expr.elts) == 5
        assert expr.elts[0].value == 1
        assert expr.elts[4].value == 5
    
    def test_mixed_expression_list(self):
        """Test list with different expression types"""
        expr = ir.ExprList(elts=[
            ir.ExprConstant(value=1),
            ir.ExprRefLocal(name="x"),
            ir.ExprBin(
                lhs=ir.ExprConstant(value=2),
                op=ir.BinOp.Add,
                rhs=ir.ExprConstant(value=3)
            )
        ])
        assert len(expr.elts) == 3
        assert isinstance(expr.elts[0], ir.ExprConstant)
        assert isinstance(expr.elts[1], ir.ExprRefLocal)
        assert isinstance(expr.elts[2], ir.ExprBin)


class TestExprDict:
    """Test ExprDict (map literal) IR class"""
    
    def test_empty_dict(self):
        """Test empty map: {}"""
        expr = ir.ExprDict(keys=[], values=[])
        assert len(expr.keys) == 0
        assert len(expr.values) == 0
    
    def test_string_int_map(self):
        """Test: {"a": 1, "b": 2}"""
        expr = ir.ExprDict(
            keys=[
                ir.ExprConstant(value="a"),
                ir.ExprConstant(value="b")
            ],
            values=[
                ir.ExprConstant(value=1),
                ir.ExprConstant(value=2)
            ]
        )
        assert len(expr.keys) == 2
        assert len(expr.values) == 2
        assert expr.keys[0].value == "a"
        assert expr.values[0].value == 1


class TestExprStructLiteral:
    """Test ExprStructLiteral IR class"""
    
    def test_empty_struct(self):
        """Test empty struct literal: {}"""
        expr = ir.ExprStructLiteral(fields=[])
        assert len(expr.fields) == 0
    
    def test_struct_with_fields(self):
        """Test: {.x = 10, .y = 20}"""
        expr = ir.ExprStructLiteral(fields=[
            ir.ExprStructField(name="x", value=ir.ExprConstant(value=10)),
            ir.ExprStructField(name="y", value=ir.ExprConstant(value=20))
        ])
        assert len(expr.fields) == 2
        assert expr.fields[0].name == "x"
        assert expr.fields[0].value.value == 10
        assert expr.fields[1].name == "y"
        assert expr.fields[1].value.value == 20


class TestBinOpExponentiation:
    """Test Exp operator addition to BinOp enum"""
    
    def test_exp_operator_exists(self):
        """Test that Exp operator is available"""
        assert hasattr(ir.BinOp, 'Exp')
    
    def test_exp_expression(self):
        """Test: 2 ** 8"""
        expr = ir.ExprBin(
            lhs=ir.ExprConstant(value=2),
            op=ir.BinOp.Exp,
            rhs=ir.ExprConstant(value=8)
        )
        assert expr.op == ir.BinOp.Exp
        assert expr.lhs.value == 2
        assert expr.rhs.value == 8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
