"""
Tests for aggregate literal translation: value list, map, struct, empty.

Covers: AST→IR translation of ExprAggrList, ExprAggrMap, ExprAggrStruct, ExprAggrEmpty.
"""
import unittest

from zuspec.fe.pss import Parser
from zuspec.fe.pss.core import Factory
from zuspec.fe.pss.ast_to_ir import AstToIrTranslator, AstToIrContext
from zuspec.dataclasses import ir


class TestAggregateLiterals(unittest.TestCase):
    """Aggregate literal AST→IR translation tests."""

    def setUp(self):
        self.factory = Factory.inst()
        self.parser = Parser()
        self.translator = AstToIrTranslator(debug=False)

    def parse_and_translate(self, pss_code: str) -> AstToIrContext:
        self.parser.parses([("test.pss", pss_code)])
        ast_root = self.parser.link()
        return self.translator.translate(ast_root)

    def _get_exec_body_stmts(self, ctx, comp_name, action_name):
        """Helper: get statements from exec body of an action."""
        action = ctx.type_map.get(f"{comp_name}::{action_name}")
        if action is None:
            # Try without component prefix
            action = ctx.type_map.get(action_name)
        self.assertIsNotNone(action, f"Action not found: {action_name}")
        body_fn = next((f for f in action.functions if f.name == "body"), None)
        self.assertIsNotNone(body_fn, "No body function found")
        return body_fn.body

    # ---- Empty aggregate literal {}  ----

    def test_empty_aggregate_literal_translates(self):
        """Empty aggregate {} translates to ExprList with no elements."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    list<int> items;
                    exec body { items = {}; }
                }
            }
        """)
        stmts = self._get_exec_body_stmts(ctx, "C", "a")
        assign = next((s for s in stmts if isinstance(s, ir.StmtAssign)), None)
        self.assertIsNotNone(assign, "No assignment found")
        self.assertIsInstance(assign.value, ir.ExprList)
        self.assertEqual(len(assign.value.elts), 0)

    # ---- Value list literal {1, 2, 3}  ----

    def test_value_list_literal_translates(self):
        """{1, 2, 3} translates to ExprList with three elements."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    list<int> items;
                    exec body { items = {1, 2, 3}; }
                }
            }
        """)
        stmts = self._get_exec_body_stmts(ctx, "C", "a")
        assign = next((s for s in stmts if isinstance(s, ir.StmtAssign)), None)
        self.assertIsNotNone(assign)
        self.assertIsInstance(assign.value, ir.ExprList)
        self.assertEqual(len(assign.value.elts), 3)

    def test_value_list_elements_are_expressions(self):
        """Each element of a list literal is an IR expression."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    list<int> items;
                    exec body { items = {10, 20}; }
                }
            }
        """)
        stmts = self._get_exec_body_stmts(ctx, "C", "a")
        assign = next((s for s in stmts if isinstance(s, ir.StmtAssign)), None)
        self.assertIsNotNone(assign)
        self.assertIsInstance(assign.value, ir.ExprList)
        for elt in assign.value.elts:
            self.assertIsInstance(elt, ir.Expr)

    def test_value_list_single_element(self):
        """{42} translates to ExprList with one element."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    list<int> items;
                    exec body { items = {42}; }
                }
            }
        """)
        stmts = self._get_exec_body_stmts(ctx, "C", "a")
        assign = next((s for s in stmts if isinstance(s, ir.StmtAssign)), None)
        self.assertIsNotNone(assign)
        self.assertIsInstance(assign.value, ir.ExprList)
        self.assertEqual(len(assign.value.elts), 1)

    # ---- Map literal {k:v, ...}  ----

    def test_map_literal_translates(self):
        """{1:true, 2:false} translates to ExprDict."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    map<int, bool> m;
                    exec body { m = {1:true, 2:false}; }
                }
            }
        """)
        stmts = self._get_exec_body_stmts(ctx, "C", "a")
        assign = next((s for s in stmts if isinstance(s, ir.StmtAssign)), None)
        self.assertIsNotNone(assign)
        self.assertIsInstance(assign.value, ir.ExprDict)
        self.assertEqual(len(assign.value.keys), 2)
        self.assertEqual(len(assign.value.values), 2)

    def test_map_literal_keys_values_are_exprs(self):
        """Map literal keys and values are IR expressions."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    map<int, int> m;
                    exec body { m = {10:20}; }
                }
            }
        """)
        stmts = self._get_exec_body_stmts(ctx, "C", "a")
        assign = next((s for s in stmts if isinstance(s, ir.StmtAssign)), None)
        self.assertIsNotNone(assign)
        self.assertIsInstance(assign.value, ir.ExprDict)
        self.assertIsInstance(assign.value.keys[0], ir.Expr)
        self.assertIsInstance(assign.value.values[0], ir.Expr)

    # ---- Structure literal {.field=value}  ----

    def test_struct_literal_translates(self):
        """{.a=1, .b=2} translates to ExprStructLiteral."""
        ctx = self.parse_and_translate("""
            struct point { int x; int y; }
            component C {
                action a {
                    point p;
                    exec body { p = {.x=1, .y=2}; }
                }
            }
        """)
        stmts = self._get_exec_body_stmts(ctx, "C", "a")
        assign = next((s for s in stmts if isinstance(s, ir.StmtAssign)), None)
        self.assertIsNotNone(assign)
        self.assertIsInstance(assign.value, ir.ExprStructLiteral)
        self.assertEqual(len(assign.value.fields), 2)

    def test_struct_literal_field_names(self):
        """Struct literal fields have correct names."""
        ctx = self.parse_and_translate("""
            struct point { int x; int y; }
            component C {
                action a {
                    point p;
                    exec body { p = {.x=10, .y=20}; }
                }
            }
        """)
        stmts = self._get_exec_body_stmts(ctx, "C", "a")
        assign = next((s for s in stmts if isinstance(s, ir.StmtAssign)), None)
        self.assertIsNotNone(assign)
        fields = assign.value.fields
        self.assertEqual(fields[0].name, "x")
        self.assertEqual(fields[1].name, "y")

    def test_struct_literal_field_values_are_exprs(self):
        """Struct literal field values are IR expressions."""
        ctx = self.parse_and_translate("""
            struct s { int a; }
            component C {
                action a {
                    s obj;
                    exec body { obj = {.a=99}; }
                }
            }
        """)
        stmts = self._get_exec_body_stmts(ctx, "C", "a")
        assign = next((s for s in stmts if isinstance(s, ir.StmtAssign)), None)
        self.assertIsNotNone(assign)
        self.assertIsInstance(assign.value.fields[0].value, ir.Expr)


if __name__ == "__main__":
    unittest.main()
