/*
 * TestPSS30Grammar.cpp
 *
 * Comprehensive grammar regression tests for PSS 3.0 features
 * 
 * Tests all PSS 3.0 grammar productions including:
 * - Randomize statements (procedural)
 * - Atomic blocks (activity)
 * - Monitor declarations
 * - String methods and substring operator
 * - Reference collections
 * - Yield statements
 * - Platform qualifiers
 * - Cover statements
 */

#include "TestPSS30Grammar.h"

namespace zsp {
namespace parser {

TestPSS30Grammar::TestPSS30Grammar() {
}

TestPSS30Grammar::~TestPSS30Grammar() {
}

TEST_F(TestPSS30Grammar, randomize_simple) {
    const char *text = R"(
        component pss_top {
            action my_action {
                rand int x;
                
                exec body {
                    randomize x;
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "randomize_simple.pss",
        files,
        root,
        false);
}

TEST_F(TestPSS30Grammar, randomize_multiple) {
    const char *text = R"(
        component pss_top {
            action my_action {
                rand int x;
                rand int y;
                
                exec body {
                    randomize x, y;
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "randomize_multiple.pss",
        files,
        root,
        false);
}

TEST_F(TestPSS30Grammar, randomize_with_constraints) {
    const char *text = R"(
        component pss_top {
            action my_action {
                rand int x;
                rand int y;
                
                exec body {
                    randomize x, y with {
                        x < y;
                        y < 100;
                    };
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "randomize_with_constraints.pss",
        files,
        root,
        false);
}

TEST_F(TestPSS30Grammar, atomic_block_simple) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            action B {
                exec body { }
            }
            
            action my_compound {
                A a1;
                B b1;
                
                activity {
                    atomic {
                        a1;
                        b1;
                    }
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "atomic_block_simple.pss",
        files,
        root,
        false);
}

TEST_F(TestPSS30Grammar, atomic_block_nested) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            action B {
                exec body { }
            }
            
            action my_compound {
                A a1;
                A a2;
                B b1;
                
                activity {
                    sequence {
                        atomic {
                            a1;
                            a2;
                        }
                        b1;
                    }
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "atomic_block_nested.pss",
        files,
        root,
        false);
}

TEST_F(TestPSS30Grammar, pss30_combined_features) {
    const char *text = R"(
        component pss_top {
            action A {
                rand int x;
                
                exec body {
                    randomize x with { x < 50; };
                }
            }
            
            action B {
                exec body { }
            }
            
            action my_compound {
                A a1;
                A a2;
                B b1;
                
                activity {
                    atomic {
                        a1;
                        a2;
                    }
                    b1;
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(
        &marker_c,
        text,
        "pss30_combined_features.pss",
        files,
        root,
        false);
}

// ========================================================================
// String Method Tests (Section 7.6.3)
// ========================================================================

TEST_F(TestPSS30Grammar, string_method_size) {
    const char *text = R"(
        component pss_top {
            action A {
                string s;
                exec body {
                    int len = s.size();
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "string_method_size.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, string_method_find) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body {
                    string s = "hello world";
                    int pos1 = s.find("world");
                    int pos2 = s.find("lo", 3);
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "string_method_find.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, string_method_find_last) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body {
                    string s = "hello hello";
                    int pos = s.find_last("hello");
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "string_method_find_last.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, string_method_find_all) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body {
                    string s = "hello world hello";
                    list<int> positions = s.find_all("hello");
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "string_method_find_all.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, string_method_lower_upper) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body {
                    string s = "Hello World";
                    string lower_s = s.lower();
                    string upper_s = s.upper();
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "string_method_lower_upper.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, string_method_split) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body {
                    string s = "one,two,three";
                    list<string> parts = s.split(",");
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "string_method_split.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, string_method_chars) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body {
                    string s = "ABC";
                    list<bit[8]> codes = s.chars();
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "string_method_chars.pss", files, root, false);
}

// ========================================================================
// Substring Operator Tests (Section 7.6.2)
// ========================================================================

TEST_F(TestPSS30Grammar, substring_range) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body {
                    string s = "hello world";
                    string sub = s[0..4];
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "substring_range.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, substring_from_start) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body {
                    string s = "hello world";
                    string sub = s[6..];
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "substring_from_start.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, substring_to_end) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body {
                    string s = "hello world";
                    string sub = s[0..5];
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "substring_to_end.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, substring_single_char) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body {
                    string s = "hello";
                    bit[8] ch = s[0];
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "substring_single_char.pss", files, root, false);
}

// ========================================================================
// Monitor Tests (Section 19)
// ========================================================================

TEST_F(TestPSS30Grammar, monitor_basic) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            monitor basic_monitor {
                A a;
                
                activity {
                    a;
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "monitor_basic.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, monitor_abstract) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            abstract monitor base_monitor {
                A a;
            }
            
            monitor concrete_monitor : base_monitor {
                activity {
                    a;
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "monitor_abstract.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, monitor_activity_concat) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            action B {
                exec body { }
            }
            
            monitor sequence_monitor {
                A a;
                B b;
                
                activity {
                    concat { a; b; }
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "monitor_activity_concat.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, monitor_activity_eventually) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            action B {
                exec body { }
            }
            
            monitor eventually_monitor {
                A a;
                B b;
                
                activity {
                    eventually sequence { a; }
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "monitor_activity_eventually.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, monitor_activity_overlap) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            action B {
                exec body { }
            }
            
            monitor overlap_monitor {
                A a;
                B b;
                
                activity {
                    overlap { a; b; }
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "monitor_activity_overlap.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, monitor_activity_schedule) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            action B {
                exec body { }
            }
            
            monitor schedule_monitor {
                A a;
                B b;
                
                activity {
                    schedule { a; b; }
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "monitor_activity_schedule.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, monitor_with_constraints) {
    const char *text = R"(
        component pss_top {
            action A {
                rand int x;
                exec body { }
            }
            
            monitor constrained_monitor {
                A a;
                
                constraint {
                    a.x < 100;
                }
                
                activity {
                    a;
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "monitor_with_constraints.pss", files, root, false);
}

// ========================================================================
// Cover Statement Tests (Section 19)
// ========================================================================

TEST_F(TestPSS30Grammar, cover_inline) {
    const char *text = R"(
        component pss_top {
            action A {
                rand int x;
                exec body { }
            }
            
            monitor test_monitor {
                A a;
                activity {
                    a;
                }
            }
            
            cover {
                test_monitor m;
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "cover_inline.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, cover_reference) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            monitor my_monitor {
                A a;
                activity {
                    a;
                }
            }
            
            cover my_monitor;
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "cover_reference.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, cover_labeled) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            monitor my_monitor {
                A a;
                activity {
                    a;
                }
            }
            
            cov1: cover my_monitor;
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "cover_labeled.pss", files, root, false);
}

// ========================================================================
// Reference Collection Tests (Section 7.10)
// ========================================================================

TEST_F(TestPSS30Grammar, ref_collection_array) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            action Container {
                array<ref A, 10> action_refs;
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "ref_collection_array.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, ref_collection_list) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            action Container {
                list<ref A> action_refs;
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "ref_collection_list.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, ref_collection_set) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            action Container {
                set<ref A> unique_refs;
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "ref_collection_set.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, ref_collection_map) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            action Container {
                map<string, ref A> named_refs;
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "ref_collection_map.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, ref_simple_declaration) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body { }
            }
            
            action Container {
                ref A action_ref;
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "ref_simple_declaration.pss", files, root, false);
}

// ========================================================================
// Yield Statement Tests (Section 22.7.14)
// ========================================================================

TEST_F(TestPSS30Grammar, yield_simple) {
    const char *text = R"(
        component pss_top {
            target function void my_func() {
                yield;
            }
            
            action A {
                exec body {
                    my_func();
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "yield_simple.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, yield_in_exec_block) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body {
                    int x = 0;
                    yield;
                    x = x + 1;
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "yield_in_exec_block.pss", files, root, false);
}

// ========================================================================
// Platform Qualifier Tests (Section 22.2.3)
// ========================================================================

TEST_F(TestPSS30Grammar, platform_qualifier_target) {
    const char *text = R"(
        component pss_top {
            target function void target_func() {
                // Runs on target platform
            }
            
            action A {
                exec body {
                    target_func();
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "platform_qualifier_target.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, platform_qualifier_solve) {
    const char *text = R"(
        component pss_top {
            solve function int solve_func() {
                return 42;
            }
            
            action A {
                rand int x;
                constraint {
                    x == solve_func();
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "platform_qualifier_solve.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, platform_qualifier_both) {
    const char *text = R"(
        component pss_top {
            target function void target_only() { }
            solve function int solve_only() { return 0; }
            target solve function int both_platforms() { return 0; }
            
            action A {
                exec body {
                    target_only();
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "platform_qualifier_both.pss", files, root, false);
}

// ========================================================================
// Feature Combination Tests
// ========================================================================

TEST_F(TestPSS30Grammar, combined_string_operations) {
    const char *text = R"(
        component pss_top {
            action A {
                exec body {
                    string s = "Hello World";
                    string lower_s = s.lower();
                    string sub = lower_s[0..4];
                    int pos = sub.find("ell");
                    list<string> parts = s.split(" ");
                }
            }
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "combined_string_operations.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, combined_monitor_features) {
    const char *text = R"(
        component pss_top {
            action A {
                rand int x;
                exec body { }
            }
            
            action B {
                exec body { }
            }
            
            abstract monitor base_mon {
                A a;
            }
            
            monitor complex_mon : base_mon {
                B b;
                
                constraint {
                    a.x > 10;
                }
                
                activity {
                    eventually sequence { a; }
                }
            }
            
            cov1: cover complex_mon;
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "combined_monitor_features.pss", files, root, false);
}

TEST_F(TestPSS30Grammar, combined_all_pss30_features) {
    const char *text = R"(
        component pss_top {
            action A {
                rand int x;
                list<ref A> ref_list;
                
                exec body {
                    string msg = "Processing";
                    msg = msg.upper();
                    randomize x with { x < 100; };
                    yield;
                }
            }
            
            action B {
                exec body { }
            }
            
            monitor test_mon {
                A a;
                B b;
                
                activity {
                    concat { a; b; }
                }
            }
            
            target function void process() {
                yield;
            }
            
            solve function int calculate() {
                return 42;
            }
            
            cover test_mon;
        }
    )";

    MarkerCollector marker_c; 
    std::vector<ast::IGlobalScopeUP> files;
    ast::ISymbolScopeUP root;

    parseLink(&marker_c, text, "combined_all_pss30_features.pss", files, root, false);
}

}
}
