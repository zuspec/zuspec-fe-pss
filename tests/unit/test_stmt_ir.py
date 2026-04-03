"""
Unit tests for PSS statement IR classes (Phase 2)
Tests the new statement types added for PSS support
"""
import pytest
from zuspec.dataclasses import ir


class TestStmtRepeat:
    """Test StmtRepeat IR class"""
    
    def test_repeat_simple_count(self):
        """Test: repeat (10) { ... }"""
        stmt = ir.StmtRepeat(
            count=ir.ExprConstant(value=10),
            iterator=None,
            body=[
                ir.StmtExpr(expr=ir.ExprConstant(value=1))
            ]
        )
        assert stmt.count.value == 10
        assert stmt.iterator is None
        assert len(stmt.body) == 1
    
    def test_repeat_with_iterator(self):
        """Test: repeat (i : 10) { ... }"""
        stmt = ir.StmtRepeat(
            count=ir.ExprConstant(value=10),
            iterator=ir.ExprRefLocal(name="i"),
            body=[
                ir.StmtAssign(
                    targets=[ir.ExprRefLocal(name="x")],
                    value=ir.ExprRefLocal(name="i")
                )
            ]
        )
        assert stmt.count.value == 10
        assert isinstance(stmt.iterator, ir.ExprRefLocal)
        assert stmt.iterator.name == "i"
        assert len(stmt.body) == 1
    
    def test_repeat_with_expression_count(self):
        """Test: repeat (n * 2) { ... }"""
        stmt = ir.StmtRepeat(
            count=ir.ExprBin(
                lhs=ir.ExprRefLocal(name="n"),
                op=ir.BinOp.Mult,
                rhs=ir.ExprConstant(value=2)
            ),
            iterator=None,
            body=[]
        )
        assert isinstance(stmt.count, ir.ExprBin)
        assert stmt.count.op == ir.BinOp.Mult


class TestStmtRepeatWhile:
    """Test StmtRepeatWhile IR class"""
    
    def test_repeat_while_simple(self):
        """Test: repeat while (cond) { ... }"""
        stmt = ir.StmtRepeatWhile(
            condition=ir.ExprRefLocal(name="done"),
            body=[
                ir.StmtExpr(expr=ir.ExprConstant(value=1))
            ]
        )
        assert isinstance(stmt.condition, ir.ExprRefLocal)
        assert stmt.condition.name == "done"
        assert len(stmt.body) == 1
    
    def test_repeat_while_with_comparison(self):
        """Test: repeat while (x < 10) { ... }"""
        stmt = ir.StmtRepeatWhile(
            condition=ir.ExprCompare(
                left=ir.ExprRefLocal(name="x"),
                ops=[ir.CmpOp.Lt],
                comparators=[ir.ExprConstant(value=10)]
            ),
            body=[
                ir.StmtAssign(
                    targets=[ir.ExprRefLocal(name="x")],
                    value=ir.ExprBin(
                        lhs=ir.ExprRefLocal(name="x"),
                        op=ir.BinOp.Add,
                        rhs=ir.ExprConstant(value=1)
                    )
                )
            ]
        )
        assert isinstance(stmt.condition, ir.ExprCompare)
        assert len(stmt.body) == 1


class TestStmtForeach:
    """Test StmtForeach IR class"""
    
    def test_foreach_simple(self):
        """Test: foreach (item : array) { ... }"""
        stmt = ir.StmtForeach(
            target=ir.ExprRefLocal(name="item"),
            iter=ir.ExprRefLocal(name="array"),
            body=[
                ir.StmtExpr(expr=ir.ExprRefLocal(name="item"))
            ],
            index_var=None
        )
        assert stmt.target.name == "item"
        assert stmt.iter.name == "array"
        assert stmt.index_var is None
        assert len(stmt.body) == 1
    
    def test_foreach_with_index(self):
        """Test: foreach (item[idx] : array) { ... }"""
        stmt = ir.StmtForeach(
            target=ir.ExprRefLocal(name="item"),
            iter=ir.ExprRefLocal(name="array"),
            body=[
                ir.StmtAssign(
                    targets=[ir.ExprRefLocal(name="result")],
                    value=ir.ExprRefLocal(name="item")
                )
            ],
            index_var=ir.ExprRefLocal(name="idx")
        )
        assert stmt.target.name == "item"
        assert stmt.iter.name == "array"
        assert isinstance(stmt.index_var, ir.ExprRefLocal)
        assert stmt.index_var.name == "idx"
    
    def test_foreach_empty_body(self):
        """Test foreach with empty body"""
        stmt = ir.StmtForeach(
            target=ir.ExprRefLocal(name="item"),
            iter=ir.ExprRefLocal(name="collection"),
            body=[]
        )
        assert len(stmt.body) == 0


class TestStmtYield:
    """Test StmtYield IR class"""
    
    def test_yield_simple(self):
        """Test: yield;"""
        stmt = ir.StmtYield(value=None)
        assert stmt.value is None
    
    def test_yield_with_value(self):
        """Test: yield expression; (if supported)"""
        stmt = ir.StmtYield(value=ir.ExprConstant(value=42))
        assert stmt.value is not None
        assert stmt.value.value == 42


class TestStmtRandomize:
    """Test StmtRandomize IR class"""
    
    def test_randomize_simple(self):
        """Test: randomize(obj);"""
        stmt = ir.StmtRandomize(
            target=ir.ExprRefLocal(name="obj"),
            constraints=[]
        )
        assert isinstance(stmt.target, ir.ExprRefLocal)
        assert stmt.target.name == "obj"
        assert len(stmt.constraints) == 0
    
    def test_randomize_no_target(self):
        """Test: randomize(); (randomize self)"""
        stmt = ir.StmtRandomize(target=None, constraints=[])
        assert stmt.target is None
    
    def test_randomize_with_constraints(self):
        """Test: randomize(obj) with { ... }
        
        Note: Actual constraint IR not implemented yet, 
        using placeholder statements
        """
        stmt = ir.StmtRandomize(
            target=ir.ExprRefLocal(name="obj"),
            constraints=[
                # Placeholder - will be constraint statements in future
                ir.StmtExpr(expr=ir.ExprConstant(value=1))
            ]
        )
        assert stmt.target.name == "obj"
        assert len(stmt.constraints) == 1


class TestStmtMatchCase:
    """Test StmtMatch and pattern support (already existed, verify it works)"""
    
    def test_match_with_value_patterns(self):
        """Test: match (x) { 1: ...; 2: ...; }"""
        stmt = ir.StmtMatch(
            subject=ir.ExprRefLocal(name="x"),
            cases=[
                ir.StmtMatchCase(
                    pattern=ir.PatternValue(value=ir.ExprConstant(value=1)),
                    guard=None,
                    body=[ir.StmtPass()]
                ),
                ir.StmtMatchCase(
                    pattern=ir.PatternValue(value=ir.ExprConstant(value=2)),
                    guard=None,
                    body=[ir.StmtPass()]
                )
            ]
        )
        assert isinstance(stmt.subject, ir.ExprRefLocal)
        assert len(stmt.cases) == 2
        assert isinstance(stmt.cases[0].pattern, ir.PatternValue)
    
    def test_match_with_guard(self):
        """Test: match (x) { n if n > 0: ...; }"""
        stmt = ir.StmtMatch(
            subject=ir.ExprRefLocal(name="x"),
            cases=[
                ir.StmtMatchCase(
                    pattern=ir.PatternAs(name="n"),
                    guard=ir.ExprCompare(
                        left=ir.ExprRefLocal(name="n"),
                        ops=[ir.CmpOp.Gt],
                        comparators=[ir.ExprConstant(value=0)]
                    ),
                    body=[ir.StmtReturn(value=ir.ExprRefLocal(name="n"))]
                )
            ]
        )
        assert len(stmt.cases) == 1
        assert stmt.cases[0].guard is not None
        assert isinstance(stmt.cases[0].guard, ir.ExprCompare)


class TestStatementCombinations:
    """Test complex statement combinations"""
    
    def test_nested_repeat_in_foreach(self):
        """Test nested loops: foreach + repeat"""
        stmt = ir.StmtForeach(
            target=ir.ExprRefLocal(name="item"),
            iter=ir.ExprRefLocal(name="array"),
            body=[
                ir.StmtRepeat(
                    count=ir.ExprConstant(value=5),
                    iterator=ir.ExprRefLocal(name="i"),
                    body=[
                        ir.StmtExpr(expr=ir.ExprRefLocal(name="item"))
                    ]
                )
            ]
        )
        assert len(stmt.body) == 1
        assert isinstance(stmt.body[0], ir.StmtRepeat)
    
    def test_repeat_while_with_break(self):
        """Test: repeat while (cond) { if (x) break; }"""
        stmt = ir.StmtRepeatWhile(
            condition=ir.ExprRefLocal(name="cond"),
            body=[
                ir.StmtIf(
                    test=ir.ExprRefLocal(name="x"),
                    body=[ir.StmtBreak()],
                    orelse=[]
                )
            ]
        )
        assert len(stmt.body) == 1
        assert isinstance(stmt.body[0], ir.StmtIf)
        assert isinstance(stmt.body[0].body[0], ir.StmtBreak)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
