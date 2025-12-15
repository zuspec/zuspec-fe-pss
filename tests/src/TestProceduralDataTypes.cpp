/*
 * TestProceduralDataTypes.cpp
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
#include "TestProceduralDataTypes.h"


namespace zsp {
namespace parser {


TestProceduralDataTypes::TestProceduralDataTypes() {

}

TestProceduralDataTypes::~TestProceduralDataTypes() {

}

TEST_F(TestProceduralDataTypes, int_variables) {
    const char *text = R"(
        function int test_ints() {
            int a;
            int b;
            a = 10;
            b = 20;
            return a + b;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "int_variables.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralDataTypes, bool_variables) {
    const char *text = R"(
        function bool test_bool() {
            bool flag1;
            bool flag2;
            flag1 = true;
            flag2 = false;
            return flag1 && flag2;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "bool_variables.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralDataTypes, bit_variables) {
    const char *text = R"(
        function bit[8] test_bits() {
            bit[8] val1;
            bit[8] val2;
            val1 = 0xFF;
            val2 = 0x00;
            return val1 & val2;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "bit_variables.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralDataTypes, array_access) {
    const char *text = R"(
        function int array_sum(array<int,10> arr) {
            int sum;
            int i;
            sum = 0;
            repeat (i : 10) {
                sum = sum + arr[i];
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
        "array_access.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralDataTypes, list_operations) {
    const char *text = R"(
        component pss_top {
            action Entry {
                list<int> my_list;
                exec body {
                    int val;
                    val = 5;
                    my_list.push_back(val);
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
        "list_operations.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralDataTypes, foreach_array) {
    const char *text = R"(
        function int sum_array(array<int,20> arr) {
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
        "foreach_array.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralDataTypes, foreach_list) {
    const char *text = R"(
        component pss_top {
            action Entry {
                list<int> items;
                exec body {
                    int sum;
                    sum = 0;
                    foreach (item : items) {
                        sum = sum + item;
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
        "foreach_list.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralDataTypes, mixed_types) {
    const char *text = R"(
        function void test_mixed() {
            int i_val;
            bool b_val;
            bit[16] bit_val;
            
            i_val = 42;
            b_val = (i_val > 0);
            bit_val = 0xABCD;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "mixed_types.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralDataTypes, string_variables) {
    const char *text = R"(
        function void test_string() {
            string msg;
            msg = "Hello";
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "string_variables.pss",
        files,
        root,
        false);
}

TEST_F(TestProceduralDataTypes, variable_initialization) {
    const char *text = R"(
        function int test_init() {
            int x = 5;
            int y = x + 10;
            bool flag = true;
            return y;
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 

    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "variable_initialization.pss",
        files,
        root,
        false);
}

}
}
