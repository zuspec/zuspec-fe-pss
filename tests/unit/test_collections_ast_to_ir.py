"""
Tests for chandle type and collection types (list, array, map, set).

Covers: AST→IR translation and IR→Runtime building for each collection type.
"""
import unittest

from zuspec.fe.pss import Parser
from pssparser.core import Factory
from zuspec.fe.pss.ast_to_ir import AstToIrTranslator, AstToIrContext
from zuspec.fe.pss.ir_to_runtime import IrToRuntimeBuilder
from zuspec.dataclasses import ir


class TestChandleAstToIr(unittest.TestCase):
    """chandle type AST→IR translation."""

    def setUp(self):
        self.factory = Factory.inst()
        self.parser = Parser()
        self.translator = AstToIrTranslator(debug=False)

    def parse_and_translate(self, pss_code: str) -> AstToIrContext:
        self.parser.parses([("test.pss", pss_code)])
        ast_root = self.parser.link()
        return self.translator.translate(ast_root)

    def test_chandle_field_in_struct(self):
        ctx = self.parse_and_translate("struct s { chandle ptr; }")
        s = ctx.type_map.get("s")
        self.assertIsNotNone(s)
        self.assertEqual(len(s.fields), 1)
        self.assertEqual(s.fields[0].name, "ptr")
        self.assertIsInstance(s.fields[0].datatype, ir.DataTypeChandle)

    def test_chandle_no_errors(self):
        ctx = self.parse_and_translate("struct s { chandle h; }")
        self.assertEqual(ctx.errors, [])


class TestCollectionAstToIr(unittest.TestCase):
    """Collection types (list, array, map, set) AST→IR translation."""

    def setUp(self):
        self.factory = Factory.inst()
        self.parser = Parser()
        self.translator = AstToIrTranslator(debug=False)

    def parse_and_translate(self, pss_code: str) -> AstToIrContext:
        self.parser.parses([("test.pss", pss_code)])
        ast_root = self.parser.link()
        return self.translator.translate(ast_root)

    # --- list<T> -------------------------------------------------------------

    def test_list_int_field(self):
        ctx = self.parse_and_translate("struct s { list<int> items; }")
        s = ctx.type_map["s"]
        f = s.fields[0]
        self.assertEqual(f.name, "items")
        self.assertIsInstance(f.datatype, ir.DataTypeList)

    def test_list_element_type_is_DataTypeInt(self):
        ctx = self.parse_and_translate("struct s { list<int> items; }")
        dt = ctx.type_map["s"].fields[0].datatype
        self.assertIsInstance(dt.element_type, ir.DataTypeInt)

    def test_list_string_element_type(self):
        ctx = self.parse_and_translate("struct s { list<string> tags; }")
        dt = ctx.type_map["s"].fields[0].datatype
        self.assertIsInstance(dt.element_type, ir.DataTypeString)

    # --- array<T, N> ---------------------------------------------------------

    def test_array_field(self):
        ctx = self.parse_and_translate("struct s { array<int, 16> buf; }")
        s = ctx.type_map["s"]
        f = s.fields[0]
        self.assertEqual(f.name, "buf")
        self.assertIsInstance(f.datatype, ir.DataTypeArray)

    def test_array_element_type(self):
        ctx = self.parse_and_translate("struct s { array<int, 8> buf; }")
        dt = ctx.type_map["s"].fields[0].datatype
        self.assertIsInstance(dt.element_type, ir.DataTypeInt)

    def test_array_size(self):
        ctx = self.parse_and_translate("struct s { array<int, 16> buf; }")
        dt = ctx.type_map["s"].fields[0].datatype
        self.assertEqual(dt.size, 16)

    def test_array_square_bracket_syntax(self):
        """int arr[N] should produce the same DataTypeArray as array<int,N>."""
        ctx = self.parse_and_translate("struct s { int arr[16]; }")
        dt = ctx.type_map["s"].fields[0].datatype
        self.assertIsInstance(dt, ir.DataTypeArray)
        self.assertEqual(dt.size, 16)

    # --- map<K, V> -----------------------------------------------------------

    def test_map_field(self):
        ctx = self.parse_and_translate("struct s { map<string, int> m; }")
        s = ctx.type_map["s"]
        f = s.fields[0]
        self.assertEqual(f.name, "m")
        self.assertIsInstance(f.datatype, ir.DataTypeMap)

    def test_map_key_type_is_string(self):
        ctx = self.parse_and_translate("struct s { map<string, int> m; }")
        dt = ctx.type_map["s"].fields[0].datatype
        self.assertIsInstance(dt.key_type, ir.DataTypeString)

    def test_map_value_type_is_int(self):
        ctx = self.parse_and_translate("struct s { map<string, int> m; }")
        dt = ctx.type_map["s"].fields[0].datatype
        self.assertIsInstance(dt.value_type, ir.DataTypeInt)

    # --- set<T> --------------------------------------------------------------

    def test_set_field(self):
        ctx = self.parse_and_translate("struct s { set<int> vals; }")
        s = ctx.type_map["s"]
        f = s.fields[0]
        self.assertEqual(f.name, "vals")
        self.assertIsInstance(f.datatype, ir.DataTypeSet)

    def test_set_element_type(self):
        ctx = self.parse_and_translate("struct s { set<int> vals; }")
        dt = ctx.type_map["s"].fields[0].datatype
        self.assertIsInstance(dt.element_type, ir.DataTypeInt)

    # --- no errors -----------------------------------------------------------

    def test_collections_no_errors(self):
        ctx = self.parse_and_translate("""
            struct s {
                list<int> items;
                array<int, 4> buf;
                map<string, int> m;
                set<int> vals;
            }
        """)
        self.assertEqual(ctx.errors, [])


class TestCollectionIrToRuntime(unittest.TestCase):
    """Collection types IR→Runtime field type mapping."""

    def setUp(self):
        self.factory = Factory.inst()
        self.parser = Parser()
        self.translator = AstToIrTranslator(debug=False)

    def build(self, pss_code: str):
        self.parser.parses([("test.pss", pss_code)])
        ast_root = self.parser.link()
        ctx = self.translator.translate(ast_root)
        return IrToRuntimeBuilder(ctx).build(), ctx

    def _get_annotations(self, cls):
        """Collect all __annotations__ from the MRO."""
        hints = {}
        for c in reversed(cls.__mro__):
            if hasattr(c, '__annotations__'):
                hints.update(c.__annotations__)
        return hints

    def test_list_field_type_is_list(self):
        registry, _ = self.build("struct s { list<int> items; }")
        # structs are not built as components; check the IR field_to_zdc directly
        # by building a component that uses the struct indirectly, or just test
        # via a component with a list field
        pass  # Covered by component test below

    def test_component_with_list_field(self):
        registry, _ = self.build("component C { list<int> items; }")
        C = registry["C"]
        hints = self._get_annotations(C)
        self.assertIn("items", hints)
        self.assertIs(hints["items"], list)

    def test_component_with_array_field(self):
        registry, _ = self.build("component C { array<int, 8> buf; }")
        C = registry["C"]
        hints = self._get_annotations(C)
        self.assertIn("buf", hints)
        self.assertIs(hints["buf"], list)

    def test_component_with_map_field(self):
        registry, _ = self.build("component C { map<string, int> m; }")
        C = registry["C"]
        hints = self._get_annotations(C)
        self.assertIn("m", hints)
        self.assertIs(hints["m"], dict)

    def test_component_with_set_field(self):
        registry, _ = self.build("component C { set<int> vals; }")
        C = registry["C"]
        hints = self._get_annotations(C)
        self.assertIn("vals", hints)
        self.assertIs(hints["vals"], set)

    def test_component_with_chandle_field(self):
        registry, _ = self.build("component C { chandle ptr; }")
        C = registry["C"]
        hints = self._get_annotations(C)
        self.assertIn("ptr", hints)
        self.assertIs(hints["ptr"], int)


class TestCollectionOperatorsAndMethods(unittest.TestCase):
    """Tests for collection subscript operators and method calls."""

    def setUp(self):
        self.factory = Factory.inst()
        self.parser = Parser()
        self.translator = AstToIrTranslator(debug=False)

    def parse_and_translate(self, pss_code: str) -> AstToIrContext:
        self.parser.parses([("test.pss", pss_code)])
        ast_root = self.parser.link()
        return self.translator.translate(ast_root)

    def _get_body_stmts(self, ctx, action_path: str):
        action = ctx.type_map.get(action_path)
        self.assertIsNotNone(action, f"Action not found: {action_path}")
        body_fn = next((f for f in action.functions if f.name == "body"), None)
        self.assertIsNotNone(body_fn, "No body function")
        return body_fn.body

    # ---- Subscript ----

    def test_list_subscript_translates_to_expr_subscript(self):
        """items[0] translates to ExprSubscript(items, 0)."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    list<int> items;
                    exec body { int v; v = items[0]; }
                }
            }
        """)
        stmts = self._get_body_stmts(ctx, "C::a")
        assign = next((s for s in stmts if isinstance(s, ir.StmtAssign)), None)
        self.assertIsNotNone(assign)
        self.assertIsInstance(assign.value, ir.ExprSubscript)
        self.assertIsInstance(assign.value.value, ir.ExprAttribute)
        self.assertEqual(assign.value.value.attr, "items")

    def test_subscript_index_is_constant(self):
        """items[2] has the correct index constant."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    list<int> items;
                    exec body { int v; v = items[2]; }
                }
            }
        """)
        stmts = self._get_body_stmts(ctx, "C::a")
        assign = next((s for s in stmts if isinstance(s, ir.StmtAssign)), None)
        self.assertIsNotNone(assign)
        self.assertIsInstance(assign.value, ir.ExprSubscript)
        self.assertIsInstance(assign.value.slice, ir.ExprConstant)
        self.assertEqual(assign.value.slice.value, 2)

    # ---- List methods ----

    def test_list_push_back_translates(self):
        """items.push_back(5) translates to ExprCall."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    list<int> items;
                    exec body { items.push_back(5); }
                }
            }
        """)
        stmts = self._get_body_stmts(ctx, "C::a")
        stmt = next((s for s in stmts if isinstance(s, ir.StmtExpr)), None)
        self.assertIsNotNone(stmt)
        self.assertIsInstance(stmt.expr, ir.ExprCall)
        self.assertIsInstance(stmt.expr.func, ir.ExprAttribute)
        self.assertEqual(stmt.expr.func.attr, "push_back")
        self.assertEqual(len(stmt.expr.args), 1)

    def test_list_size_returns_call_expr(self):
        """items.size() translates to ExprCall with no args."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    list<int> items;
                    exec body { int sz = items.size(); }
                }
            }
        """)
        stmts = self._get_body_stmts(ctx, "C::a")
        decl = next((s for s in stmts if isinstance(s, ir.StmtAnnAssign)), None)
        self.assertIsNotNone(decl)
        self.assertIsInstance(decl.value, ir.ExprCall)
        self.assertEqual(decl.value.func.attr, "size")
        self.assertEqual(len(decl.value.args), 0)

    def test_list_clear_translates(self):
        """items.clear() translates to ExprCall."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    list<int> items;
                    exec body { items.clear(); }
                }
            }
        """)
        stmts = self._get_body_stmts(ctx, "C::a")
        stmt = next((s for s in stmts if isinstance(s, ir.StmtExpr)), None)
        self.assertIsNotNone(stmt)
        self.assertIsInstance(stmt.expr, ir.ExprCall)
        self.assertEqual(stmt.expr.func.attr, "clear")

    # ---- Map methods ----

    def test_map_delete_translates(self):
        """m.delete(key) translates to ExprCall."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    map<int, int> m;
                    exec body { m.delete(1); }
                }
            }
        """)
        stmts = self._get_body_stmts(ctx, "C::a")
        stmt = next((s for s in stmts if isinstance(s, ir.StmtExpr)), None)
        self.assertIsNotNone(stmt)
        self.assertIsInstance(stmt.expr, ir.ExprCall)
        self.assertEqual(stmt.expr.func.attr, "delete")
        self.assertEqual(len(stmt.expr.args), 1)

    # ---- Collection comparisons ----

    def test_list_equality_translates(self):
        """l1 == l2 translates to ExprBin with Eq op."""
        ctx = self.parse_and_translate("""
            component C {
                action a {
                    list<int> a_list;
                    list<int> b_list;
                    exec body { bool r = (a_list == b_list); }
                }
            }
        """)
        stmts = self._get_body_stmts(ctx, "C::a")
        decl = next((s for s in stmts if isinstance(s, ir.StmtAnnAssign)), None)
        self.assertIsNotNone(decl)
        self.assertIsInstance(decl.value, ir.ExprBin)
        self.assertEqual(decl.value.op, ir.BinOp.Eq)


if __name__ == "__main__":
    unittest.main()
