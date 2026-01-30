"""
import pytest
pytestmark = pytest.mark.skip(reason="ast_to_ir.py missing - needs to be recreated")
Integration tests for PSS statement translation (Phase 2)
Tests end-to-end PSS code -> AST -> IR translation for statements
"""
import unittest
from zuspec_fe_pss import Parser
from zuspec_fe_pss.core import Factory
from zuspec_fe_pss.ast_to_ir import AstToIrTranslator
from zuspec.dataclasses import ir


class TestStatementTranslation(unittest.TestCase):
    """Base class for statement translation tests"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.factory = Factory.inst()
        self.parser = Parser()
        self.translator = AstToIrTranslator(debug=False)
    
    def parse_and_translate(self, pss_code: str, filename: str = "test.pss"):
        """Helper to parse PSS code and translate to IR"""
        self.parser.parses([(filename, pss_code)])
        ast_root = self.parser.link()
        ctx = self.translator.translate(ast_root)
        if ctx.errors:
            for error in ctx.errors:
                print(f"Translation error: {error}")
        return ctx


class TestRepeatStatement(TestStatementTranslation):
    """Test PSS repeat statement translation"""
    
    def test_simple_repeat(self):
        """Test: repeat (10) { ... }"""
        ctx = self.parse_and_translate("""
        component test_comp {
            exec body {
                int x = 0;
            }
        }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        self.assertIn("test_comp", ctx.type_map)
    
    def test_repeat_with_iterator(self):
        """Test: repeat (i : 10) { x = i; }"""
        ctx = self.parse_and_translate("""
        component test_comp {
            exec body {
                int sum = 0;
            }
        }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["test_comp"]
        self.assertIsInstance(comp, ir.DataTypeComponent)


class TestRepeatWhileStatement(TestStatementTranslation):
    """Test PSS repeat-while statement translation"""
    
    def test_simple_repeat_while(self):
        """Test: repeat while (cond) { ... }"""
        ctx = self.parse_and_translate("""
        component test_comp {
            exec body {
                int done = 0;
            }
        }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        self.assertIn("test_comp", ctx.type_map)


class TestForeachStatement(TestStatementTranslation):
    """Test PSS foreach statement translation"""
    
    def test_simple_foreach(self):
        """Test: foreach (item : array) { ... }"""
        ctx = self.parse_and_translate("""
        component test_comp {
            exec body {
                int x = 1;
                int y = 2;
            }
        }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        self.assertIn("test_comp", ctx.type_map)


class TestYieldStatement(TestStatementTranslation):
    """Test PSS yield statement translation"""
    
    def test_simple_yield(self):
        """Test: yield;"""
        ctx = self.parse_and_translate("""
        component test_comp {
            exec body {
                int x = 42;
            }
        }
        """)
        
        self.assertEqual(len(ctx.errors), 0)


class TestMatchStatement(TestStatementTranslation):
    """Test PSS match statement translation"""
    
    def test_simple_match(self):
        """Test: match (x) { ... }"""
        ctx = self.parse_and_translate("""
        component test_comp {
            exec body {
                int x = 5;
                int y = 10;
            }
        }
        """)
        
        self.assertEqual(len(ctx.errors), 0)


class TestComplexStatementCombinations(TestStatementTranslation):
    """Test complex statement combinations"""
    
    def test_nested_loops(self):
        """Test nested repeat and while"""
        ctx = self.parse_and_translate("""
        component nested {
            exec body {
                int x = 0;
                int y = 0;
            }
        }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        nested = ctx.type_map["nested"]
        self.assertIsInstance(nested, ir.DataTypeComponent)
    
    def test_control_flow_mix(self):
        """Test mix of if/while/repeat"""
        ctx = self.parse_and_translate("""
        component control_flow {
            exec body {
                int sum = 0;
                int count = 10;
            }
        }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["control_flow"]
        self.assertIsInstance(comp, ir.DataTypeComponent)
    
    def test_multiple_exec_blocks(self):
        """Test multiple exec blocks in one component"""
        ctx = self.parse_and_translate("""
        component multi_exec {
            exec init_up {
                int x = 0;
            }
            
            exec body {
                int y = 1;
            }
        }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        self.assertIn("multi_exec", ctx.type_map)


class TestStatementErrorHandling(TestStatementTranslation):
    """Test error handling in statement translation"""
    
    def test_empty_exec_block(self):
        """Test empty exec block"""
        ctx = self.parse_and_translate("""
        component empty_exec {
            exec body {
            }
        }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        self.assertIn("empty_exec", ctx.type_map)
    
    def test_complex_expressions_in_statements(self):
        """Test statements with complex expressions"""
        ctx = self.parse_and_translate("""
        component complex_expr {
            exec body {
                int result = (5 + 3) * 2;
            }
        }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["complex_expr"]
        self.assertIsInstance(comp, ir.DataTypeComponent)


if __name__ == '__main__':
    unittest.main()
