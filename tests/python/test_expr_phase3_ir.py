"""
Unit tests for Phase 3 advanced expression IR classes
Tests the new advanced expression types
"""
import pytest
from zuspec.dataclasses import ir


class TestExprCast:
    """Test ExprCast IR class"""
    
    def test_simple_cast(self):
        """Test: (int)value"""
        expr = ir.ExprCast(
            target_type=ir.DataTypeInt(name="int", bits=32, signed=True),
            value=ir.ExprConstant(value=3.14)
        )
        assert isinstance(expr.target_type, ir.DataTypeInt)
        assert expr.value.value == 3.14
    
    def test_cast_expression(self):
        """Test cast of complex expression"""
        expr = ir.ExprCast(
            target_type=ir.DataTypeInt(name="int", bits=32, signed=True),
            value=ir.ExprBin(
                lhs=ir.ExprConstant(value=10),
                op=ir.BinOp.Div,
                rhs=ir.ExprConstant(value=3)
            )
        )
        assert isinstance(expr.value, ir.ExprBin)


class TestExprStringMethod:
    """Test ExprStringMethod IR class"""
    
    def test_string_size(self):
        """Test: str.size()"""
        expr = ir.ExprStringMethod(
            base=ir.ExprRefLocal(name="str"),
            method="size",
            args=[]
        )
        assert expr.base.name == "str"
        assert expr.method == "size"
        assert len(expr.args) == 0
    
    def test_string_find(self):
        """Test: text.find("pattern")"""
        expr = ir.ExprStringMethod(
            base=ir.ExprRefLocal(name="text"),
            method="find",
            args=[ir.ExprConstant(value="pattern")]
        )
        assert expr.method == "find"
        assert len(expr.args) == 1
        assert expr.args[0].value == "pattern"
    
    def test_string_split(self):
        """Test: str.split(",")"""
        expr = ir.ExprStringMethod(
            base=ir.ExprRefLocal(name="str"),
            method="split",
            args=[ir.ExprConstant(value=",")]
        )
        assert expr.method == "split"


class TestExprHierarchical:
    """Test ExprHierarchical IR class"""
    
    def test_simple_hierarchy(self):
        """Test: top.cpu.regs"""
        expr = ir.ExprHierarchical(elements=[
            ir.ExprHierarchicalElem(name="top"),
            ir.ExprHierarchicalElem(name="cpu"),
            ir.ExprHierarchicalElem(name="regs")
        ])
        assert len(expr.elements) == 3
        assert expr.elements[0].name == "top"
        assert expr.elements[1].name == "cpu"
        assert expr.elements[2].name == "regs"
        assert not expr.is_super
    
    def test_hierarchy_with_subscript(self):
        """Test: comp.array[i].field"""
        expr = ir.ExprHierarchical(elements=[
            ir.ExprHierarchicalElem(name="comp"),
            ir.ExprHierarchicalElem(
                name="array",
                subscript=ir.ExprRefLocal(name="i")
            ),
            ir.ExprHierarchicalElem(name="field")
        ])
        assert len(expr.elements) == 3
        assert expr.elements[1].subscript is not None
        assert expr.elements[1].subscript.name == "i"
    
    def test_super_reference(self):
        """Test: super.method()"""
        expr = ir.ExprHierarchical(
            elements=[ir.ExprHierarchicalElem(name="method")],
            is_super=True
        )
        assert expr.is_super
        assert len(expr.elements) == 1


class TestExprStaticRef:
    """Test ExprStaticRef IR class"""
    
    def test_global_reference(self):
        """Test: ::pkg::Type"""
        expr = ir.ExprStaticRef(
            is_global=True,
            path=["pkg", "Type"]
        )
        assert expr.is_global
        assert len(expr.path) == 2
        assert expr.path[0] == "pkg"
        assert expr.path[1] == "Type"
    
    def test_static_method(self):
        """Test: MyClass::method"""
        expr = ir.ExprStaticRef(
            is_global=False,
            path=["MyClass", "method"]
        )
        assert not expr.is_global
        assert len(expr.path) == 2
    
    def test_package_qualified(self):
        """Test: std_pkg::sync_c"""
        expr = ir.ExprStaticRef(
            is_global=False,
            path=["std_pkg", "sync_c"]
        )
        assert len(expr.path) == 2
        assert expr.path[0] == "std_pkg"


class TestExprCompileHas:
    """Test ExprCompileHas IR class"""
    
    def test_compile_has_field(self):
        """Test: compile has field_name"""
        expr = ir.ExprCompileHas(
            target=ir.ExprRefLocal(name="field_name")
        )
        assert isinstance(expr.target, ir.ExprRefLocal)
        assert expr.target.name == "field_name"
    
    def test_compile_has_complex(self):
        """Test: compile has obj.field"""
        expr = ir.ExprCompileHas(
            target=ir.ExprAttribute(
                value=ir.ExprRefLocal(name="obj"),
                attr="field"
            )
        )
        assert isinstance(expr.target, ir.ExprAttribute)


class TestExprNull:
    """Test ExprNull IR class"""
    
    def test_null_literal(self):
        """Test null value"""
        expr = ir.ExprNull()
        assert isinstance(expr, ir.ExprNull)
        assert isinstance(expr, ir.Expr)


class TestExprSliceBitSlicing:
    """Test enhanced ExprSlice with bit slicing support"""
    
    def test_bit_slice(self):
        """Test: data[7:0]"""
        expr = ir.ExprSlice(
            lower=ir.ExprConstant(value=0),
            upper=ir.ExprConstant(value=7),
            step=None,
            is_bit_slice=True
        )
        assert expr.is_bit_slice
        assert expr.lower.value == 0
        assert expr.upper.value == 7
    
    def test_array_slice(self):
        """Test: array[1:10]"""
        expr = ir.ExprSlice(
            lower=ir.ExprConstant(value=1),
            upper=ir.ExprConstant(value=10),
            step=None,
            is_bit_slice=False
        )
        assert not expr.is_bit_slice
    
    def test_bit_slice_with_expressions(self):
        """Test: data[width-1:0]"""
        expr = ir.ExprSlice(
            lower=ir.ExprConstant(value=0),
            upper=ir.ExprBin(
                lhs=ir.ExprRefLocal(name="width"),
                op=ir.BinOp.Sub,
                rhs=ir.ExprConstant(value=1)
            ),
            is_bit_slice=True
        )
        assert expr.is_bit_slice
        assert isinstance(expr.upper, ir.ExprBin)


class TestAdvancedExpressionCombinations:
    """Test combinations of advanced expressions"""
    
    def test_cast_hierarchical(self):
        """Test: (int)obj.field"""
        expr = ir.ExprCast(
            target_type=ir.DataTypeInt(name="int", bits=32, signed=True),
            value=ir.ExprAttribute(
                value=ir.ExprRefLocal(name="obj"),
                attr="field"
            )
        )
        assert isinstance(expr.value, ir.ExprAttribute)
    
    def test_static_ref_with_method(self):
        """Test calling static methods"""
        call_expr = ir.ExprCall(
            func=ir.ExprStaticRef(
                is_global=False,
                path=["MyClass", "static_method"]
            ),
            args=[ir.ExprConstant(value=42)],
            keywords=[]
        )
        assert isinstance(call_expr.func, ir.ExprStaticRef)
    
    def test_null_comparison(self):
        """Test: if (handle == null)"""
        expr = ir.ExprCompare(
            left=ir.ExprRefLocal(name="handle"),
            ops=[ir.CmpOp.Eq],
            comparators=[ir.ExprNull()]
        )
        assert isinstance(expr.comparators[0], ir.ExprNull)
    
    def test_compile_has_in_conditional(self):
        """Test: compile if (compile has field)"""
        # This would be used in a conditional context
        condition = ir.ExprCompileHas(
            target=ir.ExprRefLocal(name="optional_field")
        )
        stmt = ir.StmtIf(
            test=condition,
            body=[ir.StmtPass()],
            orelse=[]
        )
        assert isinstance(stmt.test, ir.ExprCompileHas)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
