/*
 * TestProceduralVarResolution.cpp
 *
 * Copyright 2025 Matthew Ballance and Contributors
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
#include "TestProceduralVarResolution.h"


namespace zsp {
namespace parser {


TestProceduralVarResolution::TestProceduralVarResolution() {

}

TestProceduralVarResolution::~TestProceduralVarResolution() {

}

TEST_F(TestProceduralVarResolution, param_reference_in_function) {
    const char *text = R"(
        function int triple(int value) {
            int result;
            result = value * 3;
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
        "param_reference.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, local_var_reference) {
    const char *text = R"(
        function int test() {
            int local_var;
            int another_var;
            local_var = 10;
            another_var = local_var + 5;
            return another_var;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "local_var_reference.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, loop_index_reference) {
    const char *text = R"(
        function int loop_sum() {
            int sum;
            sum = 0;
            repeat (i : 10) {
                sum = sum + i;
            }
            return sum;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "loop_index_reference.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, foreach_iterator_reference) {
    const char *text = R"(
        function int array_sum(array<int,10> arr) {
            int total;
            total = 0;
            foreach (elem : arr) {
                total = total + elem;
            }
            return total;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "foreach_iterator_reference.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, foreach_index_iterator_reference) {
    const char *text = R"(
        function int indexed_sum(array<int,10> arr) {
            int total;
            total = 0;
            foreach (elem : arr[idx]) {
                total = total + elem + idx;
            }
            return total;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "foreach_index_iterator_reference.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, nested_scope_outer_var) {
    const char *text = R"(
        function int nested_scopes() {
            int outer;
            outer = 10;
            {
                int inner;
                inner = outer + 5;
            }
            return outer;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "nested_scope_outer_var.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, nested_loop_outer_var) {
    const char *text = R"(
        function int nested_loops() {
            int result;
            result = 0;
            repeat (i : 5) {
                repeat (j : 3) {
                    result = result + i + j;
                }
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
        "nested_loop_outer_var.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, if_else_branch_vars) {
    const char *text = R"(
        function int branch_test(int param) {
            int result;
            if (param > 0) {
                int pos_val;
                pos_val = param;
                result = pos_val;
            } else {
                int neg_val;
                neg_val = -param;
                result = neg_val;
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
        "if_else_branch_vars.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, match_branch_vars) {
    const char *text = R"(
        function int match_test(int value) {
            int result;
            match (value) {
                [0..10]: {
                    int low_val;
                    low_val = value;
                    result = low_val * 2;
                }
                [11..20]: {
                    int mid_val;
                    mid_val = value;
                    result = mid_val * 3;
                }
                default: {
                    int high_val;
                    high_val = value;
                    result = high_val * 4;
                }
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
        "match_branch_vars.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, function_call_with_local_var) {
    const char *text = R"(
        function int helper(int x) {
            return x * 2;
        }
        
        function int caller() {
            int local;
            int result;
            local = 5;
            result = helper(local);
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
        "function_call_with_local_var.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, exec_action_field_reference) {
    const char *text = R"(
        component pss_top {
            action Entry {
                int field_var;
                exec body {
                    int local_var;
                    local_var = field_var;
                    field_var = local_var + 1;
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
        "exec_action_field_reference.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, shadowing_param_with_local) {
    const char *text = R"(
        function int shadow_test(int x) {
            int result;
            result = x;
            {
                int x;
                x = 99;
                result = result + x;
            }
            result = result + x;
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
        "shadowing_param_with_local.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, complex_nested_references) {
    const char *text = R"(
        function int complex_test(int param1, int param2) {
            int outer_var;
            outer_var = param1;
            
            repeat (i : param2) {
                int loop_var;
                loop_var = i + outer_var;
                
                if (loop_var > 10) {
                    int branch_var;
                    branch_var = loop_var - param1;
                    outer_var = outer_var + branch_var;
                } else {
                    outer_var = outer_var + i;
                }
            }
            
            return outer_var;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "complex_nested_references.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, array_element_reference) {
    const char *text = R"(
        function int array_test(array<int,10> arr, int idx) {
            int value;
            value = arr[idx];
            arr[idx] = value + 1;
            return arr[idx];
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "array_element_reference.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

TEST_F(TestProceduralVarResolution, list_method_reference) {
    const char *text = R"(
        component pss_top {
            action Entry {
                list<int> my_list;
                exec body {
                    int elem;
                    elem = 42;
                    my_list.push_back(elem);
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
        "list_method_reference.pss",
        files,
        root,
        false);
    
    ASSERT_FALSE(marker_c.hasSeverity(parser::MarkerSeverityE::Error));
}

}
}
