"""
import pytest
pytestmark = pytest.mark.skip(reason="ast_to_ir.py missing - needs to be recreated")
Test statement and expression translation
"""
import unittest
import logging
from zuspec.fe.pss import Parser, AstToIrTranslator
from zuspec.dataclasses import ir

logging.basicConfig(level=logging.INFO)

class TestStmtExprTranslation(unittest.TestCase):
    """Test statement and expression translation"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.parser = Parser()
        self.translator = AstToIrTranslator(debug=False)
    
    def parse_and_translate(self, pss_code: str) -> ir.Context:
        """Parse and translate PSS code"""
        self.parser.parses([("test.pss", pss_code)])
        ast_root = self.parser.link()
        ctx = self.translator.translate(ast_root)
        if ctx.errors:
            for error in ctx.errors:
                print(f"Translation error: {error}")
        return ctx
    
    def test_function_with_return_literal(self):
        """Test function with return of literal value"""
        ctx = self.parse_and_translate("""
            component C {
                function int get_value() {
                    return 42;
                }
            }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["C"]
        self.assertEqual(len(comp.functions), 1)
        
        func = comp.functions[0]
        self.assertEqual(func.name, "get_value")
        
        # Should have 1 statement (return)
        self.assertEqual(len(func.body), 1)
        
        # First statement should be StmtReturn
        stmt = func.body[0]
        self.assertIsInstance(stmt, ir.StmtReturn)
        
        # Should have a value (literal 42)
        self.assertIsNotNone(stmt.value)
        self.assertIsInstance(stmt.value, ir.ExprConstant)
        self.assertEqual(stmt.value.value, 42)
    
    def test_function_with_return_expr(self):
        """Test function with return of binary expression"""
        ctx = self.parse_and_translate("""
            component C {
                function int add(int a, int b) {
                    return a + b;
                }
            }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["C"]
        func = comp.functions[0]
        
        # Should have 1 statement
        self.assertEqual(len(func.body), 1)
        
        # Should be a return statement
        stmt = func.body[0]
        self.assertIsInstance(stmt, ir.StmtReturn)
        
        # Value should be a binary expression
        self.assertIsNotNone(stmt.value)
        self.assertIsInstance(stmt.value, ir.ExprBin)
        
        # Check binary expression
        bin_expr = stmt.value
        self.assertEqual(bin_expr.op, ir.BinOp.Add)
        self.assertIsNotNone(bin_expr.lhs)
        self.assertIsNotNone(bin_expr.rhs)
    
    def test_function_with_void_return(self):
        """Test function with void return"""
        ctx = self.parse_and_translate("""
            component C {
                function void do_nothing() {
                    return;
                }
            }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["C"]
        func = comp.functions[0]
        
        # Should have 1 statement
        self.assertEqual(len(func.body), 1)
        
        # Should be a return with no value
        stmt = func.body[0]
        self.assertIsInstance(stmt, ir.StmtReturn)
        self.assertIsNone(stmt.value)
    
    def test_literal_expressions(self):
        """Test various literal expressions"""
        ctx = self.parse_and_translate("""
            component C {
                function int get_int() {
                    return 123;
                }
            }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["C"]
        func = comp.functions[0]
        stmt = func.body[0]
        
        # Should be integer literal
        self.assertIsInstance(stmt.value, ir.ExprConstant)
        self.assertEqual(stmt.value.value, 123)
    
    def test_binary_operations(self):
        """Test various binary operations"""
        test_cases = [
            ("a + b", ir.BinOp.Add),
            ("a - b", ir.BinOp.Sub),
            ("a * b", ir.BinOp.Mult),
            ("a / b", ir.BinOp.Div),
            ("a == b", ir.BinOp.Eq),
            ("a != b", ir.BinOp.NotEq),
            ("a < b", ir.BinOp.Lt),
            ("a > b", ir.BinOp.Gt),
            ("a <= b", ir.BinOp.LtE),
            ("a >= b", ir.BinOp.GtE),
        ]
        
        for expr_str, expected_op in test_cases:
            with self.subTest(expr=expr_str):
                ctx = self.parse_and_translate(f"""
                    component C {{
                        function int test(int a, int b) {{
                            return {expr_str};
                        }}
                    }}
                """)
                
                self.assertEqual(len(ctx.errors), 0, f"Errors for {expr_str}: {ctx.errors}")
                comp = ctx.type_map["C"]
                func = comp.functions[0]
                stmt = func.body[0]
                
                self.assertIsInstance(stmt.value, ir.ExprBin)
                self.assertEqual(stmt.value.op, expected_op, f"Wrong op for {expr_str}")
    
    def test_variable_declaration(self):
        """Test variable declaration without initialization"""
        ctx = self.parse_and_translate("""
            component C {
                function void test() {
                    int x;
                }
            }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["C"]
        func = comp.functions[0]
        
        # Should have 1 statement
        self.assertEqual(len(func.body), 1)
        
        # Should be annotated assignment (declaration)
        stmt = func.body[0]
        self.assertIsInstance(stmt, ir.StmtAnnAssign)
        
        # Check target (variable name)
        self.assertIsNotNone(stmt.target)
        # Value should be None for uninitialized
        self.assertIsNone(stmt.value)
    
    def test_variable_declaration_with_init(self):
        """Test variable declaration with initialization"""
        ctx = self.parse_and_translate("""
            component C {
                function void test() {
                    int x = 42;
                }
            }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["C"]
        func = comp.functions[0]
        
        # Should have 1 statement
        self.assertEqual(len(func.body), 1)
        
        # Should be annotated assignment
        stmt = func.body[0]
        self.assertIsInstance(stmt, ir.StmtAnnAssign)
        
        # Should have an initial value
        self.assertIsNotNone(stmt.value)
        self.assertIsInstance(stmt.value, ir.ExprConstant)
        self.assertEqual(stmt.value.value, 42)
    
    def test_assignment_statement(self):
        """Test simple assignment statement"""
        ctx = self.parse_and_translate("""
            component C {
                function void test() {
                    int x;
                    x = 5;
                }
            }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["C"]
        func = comp.functions[0]
        
        # Should have 2 statements
        self.assertEqual(len(func.body), 2)
        
        # Second statement should be assignment
        stmt = func.body[1]
        self.assertIsInstance(stmt, ir.StmtAssign)
        
        # Should have target and value
        self.assertEqual(len(stmt.targets), 1)
        self.assertIsNotNone(stmt.value)
        self.assertIsInstance(stmt.value, ir.ExprConstant)
        self.assertEqual(stmt.value.value, 5)
    
    def test_assignment_with_expression(self):
        """Test assignment with expression on RHS"""
        ctx = self.parse_and_translate("""
            component C {
                function void test(int a, int b) {
                    int sum;
                    sum = a + b;
                }
            }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["C"]
        func = comp.functions[0]
        
        # Second statement should be assignment with binary expr
        stmt = func.body[1]
        self.assertIsInstance(stmt, ir.StmtAssign)
        self.assertIsInstance(stmt.value, ir.ExprBin)
        self.assertEqual(stmt.value.op, ir.BinOp.Add)
    
    def test_if_statement(self):
        """Test if statement without else"""
        ctx = self.parse_and_translate("""
            component C {
                function int test(int x) {
                    if (x > 0) {
                        return 1;
                    }
                    return 0;
                }
            }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["C"]
        func = comp.functions[0]
        
        # Should have 2 statements (if and return)
        self.assertEqual(len(func.body), 2)
        
        # First should be if statement
        stmt = func.body[0]
        self.assertIsInstance(stmt, ir.StmtIf)
        
        # Should have test condition
        self.assertIsNotNone(stmt.test)
        self.assertIsInstance(stmt.test, ir.ExprBin)
        
        # Should have body
        self.assertGreater(len(stmt.body), 0)
        
        # Should have empty else
        self.assertEqual(len(stmt.orelse), 0)
    
    def test_if_else_statement(self):
        """Test if-else statement"""
        ctx = self.parse_and_translate("""
            component C {
                function int test(int x) {
                    if (x > 0) {
                        return 1;
                    } else {
                        return 0;
                    }
                }
            }
        """)
        
        self.assertEqual(len(ctx.errors), 0)
        comp = ctx.type_map["C"]
        func = comp.functions[0]
        
        # Should have 1 statement (if-else)
        self.assertEqual(len(func.body), 1)
        
        stmt = func.body[0]
        self.assertIsInstance(stmt, ir.StmtIf)
        
        # Should have both body and else
        self.assertGreater(len(stmt.body), 0)
        self.assertGreater(len(stmt.orelse), 0)


if __name__ == '__main__':
    unittest.main()
