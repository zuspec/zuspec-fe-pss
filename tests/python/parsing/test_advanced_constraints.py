"""
Tests for PSS advanced constraint features
Based on PSS v3.0 LRM Chapter 10 (Constraints)

Note: This focuses on features not already covered in test_constraints.py
Includes: foreach arrays, unique, implication complex, dynamic, named blocks
Excludes: forall (not well supported), default (not supported), multidim arrays
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_ok, assert_parse_error


# =============================================================================
# Foreach Constraints on Arrays
# =============================================================================

def test_foreach_array_basic(parser):
    """Test foreach constraint on array"""
    code = """
    component pss_top {
        action test_a {
            rand int arr[4];
            
            constraint {
                foreach (arr[i]) {
                    arr[i] > 0;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_foreach_with_index(parser):
    """Test foreach with explicit index variable"""
    code = """
    component pss_top {
        action test_a {
            rand int arr[8];
            
            constraint {
                foreach (arr[i]) {
                    arr[i] == i * 2;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_foreach_multiple_constraints(parser):
    """Test foreach with multiple constraints"""
    code = """
    component pss_top {
        action test_a {
            rand int arr[5];
            
            constraint {
                foreach (arr[i]) {
                    arr[i] > 0;
                    arr[i] < 100;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_foreach_nested_simple(parser):
    """Test nested foreach on separate arrays"""
    code = """
    component pss_top {
        action test_a {
            rand int arr1[3];
            rand int arr2[3];
            
            constraint {
                foreach (arr1[i]) {
                    arr1[i] > 0;
                    foreach (arr2[j]) {
                        arr2[j] < 100;
                    }
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Unique Constraints
# =============================================================================

def test_unique_basic(parser):
    """Test basic unique constraint"""
    code = """
    component pss_top {
        action test_a {
            rand int a;
            rand int b;
            rand int c;
            
            constraint {
                unique {a, b, c};
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_unique_two_elements(parser):
    """Test unique constraint with two elements"""
    code = """
    component pss_top {
        action test_a {
            rand int x;
            rand int y;
            
            constraint {
                unique {x, y};
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_unique_array_simulation(parser):
    """Test unique behavior on array elements using foreach"""
    code = """
    component pss_top {
        action test_a {
            rand int arr[5];
            
            constraint {
                foreach (arr[i]) {
                    foreach (arr[j]) {
                        (i != j) -> (arr[i] != arr[j]);
                    }
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_unique_multiple_sets(parser):
    """Test multiple unique constraint sets"""
    code = """
    component pss_top {
        action test_a {
            rand int a, b, c;
            rand int x, y, z;
            
            constraint {
                unique {a, b, c};
                unique {x, y, z};
            }
        }
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Implication Constraints (Advanced Cases)
# =============================================================================

def test_implication_basic(parser):
    """Test basic implication constraint"""
    code = """
    component pss_top {
        action test_a {
            rand int a;
            rand int b;
            
            constraint {
                (a > 5) -> (b == 1);
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_implication_multiple_consequences(parser):
    """Test implication with multiple consequences"""
    code = """
    component pss_top {
        action test_a {
            rand int a;
            rand int b;
            rand int c;
            
            constraint {
                (a > 5) -> {
                    b == 1;
                    c == 2;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_implication_nested(parser):
    """Test nested implication constraints"""
    code = """
    component pss_top {
        action test_a {
            rand int a;
            rand int b;
            rand int c;
            
            constraint {
                (a > 5) -> {
                    (b > 3) -> {
                        c == 10;
                    }
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_implication_with_foreach(parser):
    """Test implication within foreach"""
    code = """
    component pss_top {
        action test_a {
            rand int arr[4];
            rand int flag;
            
            constraint {
                foreach (arr[i]) {
                    (flag == 1) -> (arr[i] > 10);
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_implication_bidirectional(parser):
    """Test bidirectional implication behavior"""
    code = """
    component pss_top {
        action test_a {
            rand int a;
            rand int b;
            rand int c;
            
            constraint {
                (a > 5) -> (b == 1);
                (b == 1) -> (c < 10);
            }
        }
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Dynamic Constraints
# =============================================================================

def test_dynamic_constraint_basic(parser):
    """Test basic dynamic constraint"""
    code = """
    component pss_top {
        action test_a {
            rand int pkt_sz;
            
            dynamic constraint small_pkt_c {
                pkt_sz <= 100;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_dynamic_constraint_multiple(parser):
    """Test multiple dynamic constraints"""
    code = """
    component pss_top {
        action test_a {
            rand int pkt_sz;
            
            dynamic constraint small_pkt_c {
                pkt_sz <= 100;
            }
            
            dynamic constraint medium_pkt_c {
                pkt_sz > 100;
                pkt_sz <= 1500;
            }
            
            dynamic constraint jumbo_pkt_c {
                pkt_sz > 1500;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_dynamic_constraint_complex(parser):
    """Test dynamic constraint with complex expressions"""
    code = """
    component pss_top {
        action test_a {
            rand int size;
            rand int mode;
            
            dynamic constraint strict_c {
                (mode == 1) -> {
                    size > 1000;
                    size % 64 == 0;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Named Constraint Blocks
# =============================================================================

def test_named_constraint_block(parser):
    """Test named constraint block"""
    code = """
    component pss_top {
        action test_a {
            rand int val;
            
            constraint valid_range_c {
                val > 0;
                val < 100;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_multiple_named_constraint_blocks(parser):
    """Test multiple named constraint blocks"""
    code = """
    component pss_top {
        action test_a {
            rand int a;
            rand int b;
            
            constraint range_a_c {
                a > 0;
                a < 50;
            }
            
            constraint range_b_c {
                b >= 50;
                b <= 100;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_named_and_unnamed_constraints(parser):
    """Test combination of named and unnamed constraints"""
    code = """
    component pss_top {
        action test_a {
            rand int a;
            rand int b;
            
            constraint named_c {
                a > 0;
            }
            
            constraint {
                b < 100;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Constraint Inheritance and Override
# =============================================================================

def test_constraint_combination_foreach_implication(parser):
    """Test foreach with implication"""
    code = """
    component pss_top {
        action test_a {
            rand int arr[4];
            rand int mode;
            
            constraint {
                foreach (arr[i]) {
                    (mode == 1) -> (arr[i] > 10);
                    (mode == 2) -> (arr[i] < 5);
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_constraint_combination_unique_implication(parser):
    """Test unique with implication"""
    code = """
    component pss_top {
        action test_a {
            rand int a, b, c;
            rand int enable;
            
            constraint {
                (enable == 1) -> {
                    unique {a, b, c};
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_constraint_combination_dynamic_foreach(parser):
    """Test dynamic constraint with foreach"""
    code = """
    component pss_top {
        action test_a {
            rand int arr[4];
            
            dynamic constraint strict_c {
                foreach (arr[i]) {
                    arr[i] == i * 10;
                    arr[i] > 0;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Array Constraint Operations
# =============================================================================

def test_array_constraint_sum(parser):
    """Test constraint on array sum"""
    code = """
    component pss_top {
        action test_a {
            rand int arr[4];
            
            constraint {
                arr[0] + arr[1] + arr[2] + arr[3] == 100;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_array_constraint_ordering(parser):
    """Test constraint for array ordering"""
    code = """
    component pss_top {
        action test_a {
            rand int arr[5];
            
            constraint {
                foreach (arr[i]) {
                    (i < 4) -> (arr[i] <= arr[i+1]);
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_array_constraint_relationships(parser):
    """Test constraints on relationships between array elements"""
    code = """
    component pss_top {
        action test_a {
            rand int arr1[3];
            rand int arr2[3];
            
            constraint {
                foreach (arr1[i]) {
                    arr1[i] > 0;
                    arr2[i] == arr1[i] * 2;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Scalability Tests
# =============================================================================

@pytest.mark.parametrize("count", [2, 5, 10])
def test_many_unique_constraints(parser, count):
    """Test multiple unique constraints"""
    vars_decl = ", ".join([f"v{i}" for i in range(count)])
    vars_list = ", ".join([f"v{i}" for i in range(count)])
    
    code = f"""
    component pss_top {{
        action test_a {{
            rand int {vars_decl};
            
            constraint {{
                unique {{{vars_list}}};
            }}
        }}
    }}
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("size", [2, 4, 8])
def test_foreach_various_sizes(parser, size):
    """Test foreach on arrays of various sizes"""
    code = f"""
    component pss_top {{
        action test_a {{
            rand int arr[{size}];
            
            constraint {{
                foreach (arr[i]) {{
                    arr[i] > 0;
                    arr[i] < 100;
                }}
            }}
        }}
    }}
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_nested_implications(parser, depth):
    """Test nested implications at various depths"""
    if depth == 1:
        code = """
        component pss_top {
            action test_a {
                rand int a, b;
                constraint {
                    (a > 5) -> (b == 1);
                }
            }
        }
        """
    elif depth == 2:
        code = """
        component pss_top {
            action test_a {
                rand int a, b, c;
                constraint {
                    (a > 5) -> {
                        (b > 3) -> (c == 10);
                    }
                }
            }
        }
        """
    else:  # depth == 3
        code = """
        component pss_top {
            action test_a {
                rand int a, b, c, d;
                constraint {
                    (a > 5) -> {
                        (b > 3) -> {
                            (c > 1) -> (d == 100);
                        }
                    }
                }
            }
        }
        """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("count", [1, 3, 5])
def test_multiple_dynamic_constraints(parser, count):
    """Test multiple dynamic constraints"""
    dynamic_constraints = "\n".join([
        f"            dynamic constraint c{i} {{\n                pkt_sz == {i * 100};\n            }}"
        for i in range(count)
    ])
    
    code = f"""
    component pss_top {{
        action test_a {{
            rand int pkt_sz;
            
{dynamic_constraints}
        }}
    }}
    """
    assert_parse_ok(code, parser)
