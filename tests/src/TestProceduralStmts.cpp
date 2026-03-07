/*
 * TestProceduralStmts.cpp
 *
 * Copyright 2023 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may 
 * not use this file except in compliance with the License.  
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
 * See the License for the specific language governing permissions and 
 * limitations under the License.
 *
 * Created on:
 *     Author:
 */
#include "TestProceduralStmts.h"


namespace zsp {
namespace parser {


TestProceduralStmts::TestProceduralStmts() {

}

TestProceduralStmts::~TestProceduralStmts() {

}

TEST_F(TestProceduralStmts, nested_if_else_vars) {
    const char *text = R"(
        function void doit(int pval) {
            int lval = 1;
            if (lval == 2) {
                int l1_val /*= lval+1*/;
                int l1_val2 = l1_val;
                if (l1_val == 1) {

                }
            } else if (pval == 3) {
                int l2_val = pval+2;
                if (l2_val == 1) {

                }
            } else if (lval == 2) {

            }
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 


    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "nested_if_else_vars.pss",
        files,
        root,
        false);

}

TEST_F(TestProceduralStmts, iteration_var) {
    const char *text = R"(
        function void doit(int pval) {
            int x;
            repeat (i : 20) {
                x = i;
            }
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 


    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "nested_if_else_vars.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, function_local_var) {
    const char *text = R"(
        function int doit(int pval) {
            int val = pval;
            if (pval < 10) {
                val = doit(val+1);
            } else {
                val = pval(10);
            }
            return val;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 


    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "nested_if_else_vars.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, exec_iteration_var_1) {
    const char *text = R"(
        component pss_top {
            action Entry {
                exec body {
                    int x;
                    repeat (20) {
                        x += 1;
                    }
                }
            }
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 


    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "nested_if_else_vars.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, exec_iteration_var_2) {
    const char *text = R"(
        component pss_top {
            action Entry {
                exec body {
                    int x;
                    repeat (i : 20) {
                        x = i+1;
                    }
                }
            }
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 


    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "nested_if_else_vars.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, exec_iteration_var_3) {
    const char *text = R"(
        component pss_top {
            action Entry {
                exec body {
                    int x;
                    repeat (i : 20) {
                        int y;
                        y = x + 1;
                    }
                }
            }
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 


    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "nested_if_else_vars.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, repeat_sum_example) {
    const char *text = R"(
        function int sum(int a, int b) {
            int res;
            res = 0;
            repeat(b) {
                res = res + a;
            }
            return res;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "repeat_sum.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, while_parity_example) {
    const char *text = R"(
        function bool get_parity(int n) {
            bool parity;
            parity = false;
            while (n != 0) {
                parity = !parity;
                n = n & (n-1);
            }
            return parity;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "while_parity.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, if_else_max_example) {
    const char *text = R"(
        function int max(int a, int b) {
            int c;
            if (a > b) {
                c = a;
            } else {
                c = b;
            }
            return c;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "if_else_max.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, match_bucketize_example) {
    const char *text = R"(
        function int bucketize(int a) {
            int res;
            match (a) {
                [0..3]:  res = 1;
                [4..7]:  res = 2;
                [8..15]: res = 3;
                default: res = 4;
            }
            return res;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "match_bucketize.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, foreach_break_continue_example) {
    const char *text = R"(
        function int sum(array<int,100> a) {
            int res;
            res = 0;
            foreach (el : a) {
                if (el == 0)
                    break;
                if (el == 42)
                    continue;
                if ((el % 2) == 0) {
                    res = res + el;
                }
            }
            return res;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "foreach_break_continue.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, foreach_with_index) {
    const char *text = R"(
        function int sum_indexed(array<int,10> a) {
            int res;
            res = 0;
            foreach (el : a[i]) {
                res = res + el + i;
            }
            return res;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "foreach_with_index.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, nested_loops_with_vars) {
    const char *text = R"(
        function void nested_loops() {
            int outer_sum;
            outer_sum = 0;
            repeat (i : 10) {
                int inner_sum;
                inner_sum = 0;
                repeat (j : 5) {
                    inner_sum = inner_sum + j;
                }
                outer_sum = outer_sum + inner_sum + i;
            }
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "nested_loops.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, repeat_while_variant) {
    const char *text = R"(
        function int count_down(int n) {
            int counter;
            counter = n;
            repeat {
                counter = counter - 1;
            } while (counter > 0);
            return counter;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "repeat_while.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, scoped_blocks) {
    const char *text = R"(
        function void test_scopes() {
            int a;
            a = 1;
            {
                int b;
                b = a + 1;
                {
                    int c;
                    c = b + 1;
                }
            }
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "scoped_blocks.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, variable_shadowing) {
    const char *text = R"(
        function void test_shadowing() {
            int x;
            x = 10;
            {
                int x;
                x = 20;
            }
            x = 30;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "variable_shadowing.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, exec_with_foreach_list) {
    const char *text = R"(
        component pss_top {
            action Entry {
                list<int> my_list;
                exec body {
                    int sum;
                    sum = 0;
                    foreach (val : my_list) {
                        sum = sum + val;
                    }
                }
            }
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "exec_foreach_list.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, match_no_default) {
    const char *text = R"(
        function int classify(int value) {
            int result;
            match (value) {
                [0]:     result = 0;
                [1..10]: result = 1;
            }
            return result;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "match_no_default.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, nested_if_with_match) {
    const char *text = R"(
        function int complex_decision(int a, int b) {
            int result;
            if (a > 0) {
                match (b) {
                    [0..5]:  result = 1;
                    [6..10]: result = 2;
                    default: result = 3;
                }
            } else {
                result = 0;
            }
            return result;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "nested_if_match.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralStmts, compound_assignments) {
    const char *text = R"(
        function void test_compound() {
            int x;
            x = 10;
            x = x + 5;
            x = x - 3;
            x = x * 2;
            x = x / 4;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "compound_assignments.pss",
        files,
        root,
        false);
}

}
}
