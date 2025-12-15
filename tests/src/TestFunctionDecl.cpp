/*
 * TestFunctionDecl.cpp
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
#include "zsp/parser/impl/TaskGetName.h"
#include "TestFunctionDecl.h"


namespace zsp {
namespace parser {


TestFunctionDecl::TestFunctionDecl() {

}

TestFunctionDecl::~TestFunctionDecl() {

}

TEST_F(TestFunctionDecl, simple_decl) {
    const char *text = R"(
        component pss_top {
            action Entry {
            }
        }

        function void doit1() {
        }
    )";

    enableDebug(true);
    MarkerCollector marker_c; 


    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "inst_field_static_ref.pss",
        files,
        root,
        false);

    std::unordered_map<std::string,int32_t>::const_iterator doit1_idx;  
    doit1_idx = root->getSymtab().find("doit1");
    ASSERT_NE(doit1_idx, root->getSymtab().end());

    ast::IScopeChild *doit1 = root->getChildren().at(doit1_idx->second).get();
    ASSERT_TRUE(doit1);
    
    std::string fname = TaskGetName().get(doit1);
    ASSERT_EQ(fname, "doit1");

    std::string qname = TaskGetName().get(doit1, true);
    ASSERT_EQ(qname, "doit1");
}    

TEST_F(TestFunctionDecl, builtin) {
    const char *text = R"(
        import std_pkg::*;
        import addr_reg_pkg::*;

        component pss_top {
            action Entry {
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
        "inst_field_static_ref.pss",
        files,
        root,
        true);

    std::unordered_map<std::string,int32_t>::const_iterator addr_reg_pkg_idx;  
    addr_reg_pkg_idx = root->getSymtab().find("addr_reg_pkg");
    ASSERT_NE(addr_reg_pkg_idx, root->getSymtab().end());

    ast::ISymbolScope *addr_reg_pkg = dynamic_cast<ast::ISymbolScope *>(
        root->getChildren().at(addr_reg_pkg_idx->second).get());
    ASSERT_TRUE(addr_reg_pkg);

    std::unordered_map<std::string,int32_t>::const_iterator write64_idx;  
    write64_idx = addr_reg_pkg->getSymtab().find("write64");
    ASSERT_NE(write64_idx, root->getSymtab().end());

    ast::ISymbolScope *write64 = dynamic_cast<ast::ISymbolFunctionScope *>(
        addr_reg_pkg->getChildren().at(write64_idx->second).get());
    ASSERT_TRUE(write64);
    
    std::string fname = TaskGetName().get(write64);
    ASSERT_EQ(fname, "write64");

    std::string qname = TaskGetName().get(write64, true);
    ASSERT_EQ(qname, "addr_reg_pkg::write64");
}

TEST_F(TestFunctionDecl, function_with_params) {
    const char *text = R"(
        function int add(int a, int b) {
            return a + b;
        }
        
        component pss_top {
            action Entry {
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
        "function_with_params.pss",
        files,
        root,
        false);
}

TEST_F(TestFunctionDecl, function_param_reference) {
    const char *text = R"(
        function int double_value(int x) {
            int result;
            result = x * 2;
            return result;
        }
        
        component pss_top {
            action Entry {
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
        "function_param_reference.pss",
        files,
        root,
        false);
}

TEST_F(TestFunctionDecl, function_multiple_params) {
    const char *text = R"(
        function int calculate(int a, int b, int c) {
            int temp;
            temp = a + b;
            temp = temp * c;
            return temp;
        }
        
        component pss_top {
            action Entry {
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
        "function_multiple_params.pss",
        files,
        root,
        false);
}

TEST_F(TestFunctionDecl, function_calls_function) {
    const char *text = R"(
        function int helper(int x) {
            return x + 1;
        }
        
        function int caller(int y) {
            int result;
            result = helper(y);
            return result;
        }
        
        component pss_top {
            action Entry {
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
        "function_calls_function.pss",
        files,
        root,
        false);
}

TEST_F(TestFunctionDecl, target_function) {
    const char *text = R"(
        target function int sum(int a, int b) {
            int res;
            res = 0;
            repeat(b) {
                res = res + a;
            }
            return res;
        }
        
        component pss_top {
            action Entry {
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
        "target_function.pss",
        files,
        root,
        false);
}

TEST_F(TestFunctionDecl, solve_function) {
    const char *text = R"(
        solve function int factorial(int n) {
            int result;
            result = 1;
            repeat (i : n) {
                result = result * (i + 1);
            }
            return result;
        }
        
        component pss_top {
            action Entry {
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
        "solve_function.pss",
        files,
        root,
        false);
}

TEST_F(TestFunctionDecl, void_function) {
    const char *text = R"(
        function void print_value(int val) {
            int temp;
            temp = val;
        }
        
        component pss_top {
            action Entry {
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
        "void_function.pss",
        files,
        root,
        false);
}

}
}
