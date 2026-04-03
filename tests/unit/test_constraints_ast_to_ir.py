"""Tests for PSS constraint translation: AST → IR Function with _is_constraint metadata."""
import pytest
from zuspec.fe.pss import Parser
from pssparser.core import Factory
from zuspec.fe.pss.ast_to_ir import AstToIrTranslator
from zuspec.dataclasses import ir
from zuspec.dataclasses.ir.stmt import StmtExpr, StmtIf

Factory.inst()


def parse_and_translate(pss_text: str):
    parser = Parser()
    parser.parses([('test.pss', pss_text)])
    root = parser.link()
    translator = AstToIrTranslator()
    return translator.translate(root)


def get_constraint_funcs(type_obj):
    return [f for f in type_obj.functions if f.metadata.get('_is_constraint')]


# -------------------------------------------------------------------
# Basic action constraints
# -------------------------------------------------------------------

class TestActionConstraints:
    def test_unnamed_constraint_inline(self):
        ctx = parse_and_translate("""
            component C { action a { rand int x; constraint x > 0; } }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert len(cfuncs) == 1
        assert cfuncs[0].body

    def test_named_constraint_block(self):
        ctx = parse_and_translate("""
            component C { action a { rand int x; constraint c1 { x < 100; } } }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert len(cfuncs) == 1
        assert cfuncs[0].name == 'c1'

    def test_constraint_function_has_is_constraint_metadata(self):
        ctx = parse_and_translate("""
            component C { action a { rand int x; constraint x > 0; } }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert cfuncs[0].metadata.get('_is_constraint') is True

    def test_constraint_body_is_stmt_expr(self):
        ctx = parse_and_translate("""
            component C { action a { rand int x; constraint x > 0; } }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert len(cfuncs[0].body) == 1
        assert isinstance(cfuncs[0].body[0], StmtExpr)

    def test_constraint_expr_is_expr_bin(self):
        ctx = parse_and_translate("""
            component C { action a { rand int x; constraint x > 0; } }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        stmt = cfuncs[0].body[0]
        assert isinstance(stmt.expr, ir.ExprBin)

    def test_multiple_constraints_all_translated(self):
        ctx = parse_and_translate("""
            component C {
                action a {
                    rand int x;
                    constraint x > 0;
                    constraint c1 { x < 100; }
                    constraint c2 { x != 50; }
                }
            }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert len(cfuncs) == 3

    def test_constraint_not_async(self):
        ctx = parse_and_translate("""
            component C { action a { rand int x; constraint x > 0; } }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert cfuncs[0].is_async is False

    def test_unnamed_constraints_get_auto_names(self):
        ctx = parse_and_translate("""
            component C {
                action a {
                    rand int x;
                    rand int y;
                    constraint x > 0;
                    constraint y > 0;
                }
            }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert len(cfuncs) == 2
        # Both should have auto-generated names
        names = {f.name for f in cfuncs}
        assert '_c_0' in names

    def test_constraint_with_two_rand_fields(self):
        ctx = parse_and_translate("""
            component C {
                action a {
                    rand int x;
                    rand int y;
                    constraint x < y;
                }
            }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert len(cfuncs) == 1
        stmt = cfuncs[0].body[0]
        assert isinstance(stmt.expr, ir.ExprBin)


# -------------------------------------------------------------------
# Struct constraints
# -------------------------------------------------------------------

class TestStructConstraints:
    def test_struct_unnamed_constraint(self):
        ctx = parse_and_translate("""
            struct s { rand int a; constraint a > 0; }
        """)
        s = ctx.type_map['s']
        cfuncs = get_constraint_funcs(s)
        assert len(cfuncs) == 1

    def test_struct_named_constraint_block(self):
        ctx = parse_and_translate("""
            struct s { rand int a; constraint valid_a { a > 0; a < 256; } }
        """)
        s = ctx.type_map['s']
        cfuncs = get_constraint_funcs(s)
        assert len(cfuncs) == 1
        assert cfuncs[0].name == 'valid_a'
        assert len(cfuncs[0].body) == 2

    def test_struct_constraint_is_not_async(self):
        ctx = parse_and_translate("""
            struct s { rand int a; constraint a > 0; }
        """)
        s = ctx.type_map['s']
        cfuncs = get_constraint_funcs(s)
        assert cfuncs[0].is_async is False


# -------------------------------------------------------------------
# Implication constraints
# -------------------------------------------------------------------

class TestImplicationConstraints:
    def test_implication_constraint_translated(self):
        ctx = parse_and_translate("""
            component C {
                action a {
                    rand int x;
                    rand int y;
                    constraint c1 { x < y -> y > 5; }
                }
            }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert len(cfuncs) == 1
        # implication should produce a StmtExpr with an ExprCall(implies, ...)
        assert len(cfuncs[0].body) >= 1
        stmt = cfuncs[0].body[0]
        assert isinstance(stmt, StmtExpr)


# -------------------------------------------------------------------
# Conditional constraints
# -------------------------------------------------------------------

class TestConditionalConstraints:
    def test_if_constraint_translated(self):
        ctx = parse_and_translate("""
            component C {
                action a {
                    rand int x;
                    rand int y;
                    constraint c4 { if (x > 5) { y < 10; } }
                }
            }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert len(cfuncs) == 1
        # if constraint should produce a StmtIf
        assert len(cfuncs[0].body) >= 1
        stmt = cfuncs[0].body[0]
        assert isinstance(stmt, StmtIf)


# -------------------------------------------------------------------
# Foreach constraints
# -------------------------------------------------------------------

class TestForeachConstraints:
    def test_foreach_constraint_basic(self):
        """foreach constraint over a list generates StmtForeach in constraint body."""
        from zuspec.dataclasses.ir.stmt import StmtForeach
        from zuspec.dataclasses.ir.expr import ExprRefLocal, ExprBin, ExprAttribute

        ctx = parse_and_translate("""
            component C {
                action a {
                    rand list<int> vals;
                    constraint foreach (e:vals) { e > 0; }
                }
            }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert len(cfuncs) == 1
        assert len(cfuncs[0].body) == 1
        stmt = cfuncs[0].body[0]
        assert isinstance(stmt, StmtForeach)
        # Iterator variable
        assert isinstance(stmt.target, ExprRefLocal)
        assert stmt.target.name == 'e'
        # Collection is self.vals
        assert isinstance(stmt.iter, ExprAttribute)
        assert stmt.iter.attr == 'vals'
        # Body has one constraint
        assert len(stmt.body) == 1

    def test_foreach_constraint_body_uses_local_var(self):
        """Loop variable 'e' in foreach body resolves to ExprRefLocal, not self.e."""
        from zuspec.dataclasses.ir.stmt import StmtForeach
        from zuspec.dataclasses.ir.expr import ExprRefLocal, ExprBin

        ctx = parse_and_translate("""
            component C {
                action a {
                    rand list<int> vals;
                    constraint foreach (e:vals) { e > 0; }
                }
            }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        foreach_stmt = cfuncs[0].body[0]
        assert isinstance(foreach_stmt, StmtForeach)
        body_expr = foreach_stmt.body[0].expr
        assert isinstance(body_expr, ExprBin)
        assert isinstance(body_expr.lhs, ExprRefLocal)
        assert body_expr.lhs.name == 'e'

    def test_foreach_constraint_multiple_body_stmts(self):
        """foreach constraint with multiple body constraints generates multiple body stmts."""
        from zuspec.dataclasses.ir.stmt import StmtForeach

        ctx = parse_and_translate("""
            component C {
                action a {
                    rand list<int> vals;
                    constraint foreach (e:vals) { e > 0; e < 100; }
                }
            }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert len(cfuncs) == 1
        foreach_stmt = cfuncs[0].body[0]
        assert isinstance(foreach_stmt, StmtForeach)
        assert len(foreach_stmt.body) == 2

    def test_foreach_constraint_local_var_not_in_scope_outside(self):
        """After foreach, the loop variable 'e' is no longer a local; other refs use self."""
        from zuspec.dataclasses.ir.stmt import StmtForeach, StmtExpr
        from zuspec.dataclasses.ir.expr import ExprAttribute

        ctx = parse_and_translate("""
            component C {
                action a {
                    rand list<int> vals;
                    rand int limit;
                    constraint foreach (e:vals) { e > 0; }
                    constraint limit < 100;
                }
            }
        """)
        a = ctx.type_map['C::a']
        cfuncs = get_constraint_funcs(a)
        assert len(cfuncs) == 2
        # First constraint has the foreach
        assert isinstance(cfuncs[0].body[0], StmtForeach)
        # Second constraint: limit references self.limit (ExprAttribute), not ExprRefLocal
        second_body = cfuncs[1].body[0]
        assert isinstance(second_body, StmtExpr)
        # lhs should be ExprAttribute referencing self.limit
        assert isinstance(second_body.expr.lhs, ExprAttribute)
        assert second_body.expr.lhs.attr == 'limit'
