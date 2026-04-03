"""
Tests for package declaration and yield statement AST→IR translation.

Covers:
 - package my_pkg { component C { action a {} } } → type key my_pkg::C, my_pkg::C::a
 - nested package outer::inner
 - yield statement in exec body → StmtYield
"""
import unittest

from zuspec.fe.pss import Parser
from pssparser.core import Factory
from zuspec.fe.pss.ast_to_ir import AstToIrTranslator, AstToIrContext
from zuspec.dataclasses import ir


class TestPackageDeclaration(unittest.TestCase):
    """Package declaration AST→IR translation tests."""

    def setUp(self):
        self.factory = Factory.inst()
        self.parser = Parser()
        self.translator = AstToIrTranslator(debug=False)

    def parse_and_translate(self, pss_code: str) -> AstToIrContext:
        self.parser.parses([("test.pss", pss_code)])
        ast_root = self.parser.link()
        return self.translator.translate(ast_root)

    def test_package_component_registered_with_qualified_name(self):
        """Types inside a package get a qualified key: my_pkg::C."""
        ctx = self.parse_and_translate("""
            package my_pkg {
                component C {
                    action a {}
                }
            }
        """)
        self.assertIn("my_pkg::C", ctx.type_map)

    def test_package_action_registered_with_qualified_name(self):
        """Actions inside a package component get qualified key: my_pkg::C::a."""
        ctx = self.parse_and_translate("""
            package my_pkg {
                component C {
                    action a {}
                }
            }
        """)
        self.assertIn("my_pkg::C::a", ctx.type_map)

    def test_package_component_is_datatype_component(self):
        """Packaged component maps to DataTypeComponent IR node."""
        ctx = self.parse_and_translate("""
            package my_pkg {
                component C {}
            }
        """)
        comp = ctx.type_map.get("my_pkg::C")
        self.assertIsNotNone(comp)
        self.assertIsInstance(comp, ir.DataTypeComponent)

    def test_nested_package_type_registered(self):
        """Nested package outer::inner: type key is outer::inner::C."""
        ctx = self.parse_and_translate("""
            package outer::inner {
                component C {}
            }
        """)
        self.assertIn("outer::inner::C", ctx.type_map)

    def test_package_struct_registered(self):
        """Struct inside package gets qualified key."""
        ctx = self.parse_and_translate("""
            package my_pkg {
                struct S {
                    int x;
                }
            }
        """)
        self.assertIn("my_pkg::S", ctx.type_map)

    def test_unprefixed_types_still_work(self):
        """Types outside any package still work (backward compatibility)."""
        ctx = self.parse_and_translate("""
            component C {
                action a {}
            }
        """)
        self.assertIn("C", ctx.type_map)
        self.assertIn("C::a", ctx.type_map)


class TestYieldStatement(unittest.TestCase):
    """Yield statement AST→IR translation tests."""

    def setUp(self):
        self.factory = Factory.inst()
        self.parser = Parser()
        self.translator = AstToIrTranslator(debug=False)

    def parse_and_translate(self, pss_code: str) -> AstToIrContext:
        self.parser.parses([("test.pss", pss_code)])
        ast_root = self.parser.link()
        return self.translator.translate(ast_root)

    def _get_body_stmts(self, ctx, action_key: str):
        action = ctx.type_map.get(action_key)
        self.assertIsNotNone(action, f"Action not found: {action_key}")
        body_fn = next((f for f in action.functions if f.name == "body"), None)
        self.assertIsNotNone(body_fn, "No body function found")
        return body_fn.body

    def test_yield_statement_translates_to_stmt_yield(self):
        """'yield;' in exec body → ir.StmtYield."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    exec body {
                        yield;
                    }
                }
            }
        """)
        stmts = self._get_body_stmts(ctx, "C::a")
        self.assertTrue(
            any(isinstance(s, ir.StmtYield) for s in stmts),
            f"Expected StmtYield in body, got: {[type(s).__name__ for s in stmts]}"
        )

    def test_yield_statement_has_no_value(self):
        """'yield;' produces StmtYield with value=None."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    exec body {
                        yield;
                    }
                }
            }
        """)
        stmts = self._get_body_stmts(ctx, "C::a")
        yield_stmts = [s for s in stmts if isinstance(s, ir.StmtYield)]
        self.assertEqual(len(yield_stmts), 1)
        self.assertIsNone(yield_stmts[0].value)


if __name__ == "__main__":
    unittest.main()
