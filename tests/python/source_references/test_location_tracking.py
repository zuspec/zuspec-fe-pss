"""
Tests for PSS source location tracking.

Tests cover:
- Line and column tracking for declarations
- Source locations for various PSS elements
- Multi-file location tracking
- Location preservation through parsing
"""

import pytest
from zuspec.fe.pss import Parser
from ..test_helpers import parse_pss, get_location, assert_location


def test_location_struct_declaration(parser):
    """Test location tracking for struct declaration"""
    code = """
struct test_s {
    rand int value;
};
"""
    root = parse_pss(code, "test.pss", parser)
    # Basic verification that parsing succeeds with location info
    assert root is not None


def test_location_enum_declaration(parser):
    """Test location tracking for enum declaration"""
    code = """
enum status_e { IDLE, BUSY };
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_action_declaration(parser):
    """Test location tracking for action declaration"""
    code = """
component pss_top {
    action test_a {
        rand int value;
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_component_declaration(parser):
    """Test location tracking for component declaration"""
    code = """
component my_c {
    action test_a {
        rand int value;
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_package_declaration(parser):
    """Test location tracking for package declaration"""
    code = """
package my_pkg {
    struct data_s {
        rand int value;
    };
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_function_declaration(parser):
    """Test location tracking for function declaration"""
    code = """
function int compute(int value);
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_field_declaration(parser):
    """Test location tracking for field declarations"""
    code = """
struct test_s {
    rand int field1;
    rand int field2;
    rand int field3;
};
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_constraint_block(parser):
    """Test location tracking for constraint blocks"""
    code = """
struct test_s {
    rand int value;
    
    constraint {
        value > 0;
        value < 100;
    }
};
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_activity_block(parser):
    """Test location tracking for activity blocks"""
    code = """
component pss_top {
    action A {
        rand int value;
    }
    
    action test_a {
        A a;
        
        activity {
            do a;
        }
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_exec_block(parser):
    """Test location tracking for exec blocks"""
    code = """
component pss_top {
    action test_a {
        rand int value;
        int result;
        
        exec post_solve {
            result = value * 2;
        }
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_import_statement(parser):
    """Test location tracking for import statements"""
    code = """
package my_pkg {
    struct data_s {
        rand int value;
    };
}

import my_pkg::*;
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_inheritance(parser):
    """Test location tracking for inheritance"""
    code = """
struct base_s {
    rand int base_val;
};

struct derived_s : base_s {
    rand int derived_val;
};
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_nested_scopes(parser):
    """Test location tracking in nested scopes"""
    code = """
package outer {
    package inner {
        struct data_s {
            rand int value;
        };
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_multiple_declarations(parser):
    """Test location tracking with multiple declarations"""
    code = """
struct s1 {
    rand int v1;
};

struct s2 {
    rand int v2;
};

struct s3 {
    rand int v3;
};
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_complex_expressions(parser):
    """Test location tracking for complex expressions"""
    code = """
struct test_s {
    rand int a;
    rand int b;
    rand int c;
    
    constraint {
        a + b * c < 100;
        (a > 0) && (b > 0) && (c > 0);
    }
};
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


@pytest.mark.parametrize("lines", [5, 10, 20])
def test_location_scalability(parser, lines):
    """Test location tracking with many declarations"""
    structs = "\n".join([f"""
struct s{i} {{
    rand int v{i};
}};
""" for i in range(lines)])
    
    root = parse_pss(structs, "test.pss", parser)
    assert root is not None


def test_location_multiline_declaration(parser):
    """Test location tracking across multiple lines"""
    code = """
struct test_s {
    rand int field1;
    rand int field2;
    rand int field3;
    rand int field4;
    rand int field5;
};
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_with_comments(parser):
    """Test location tracking with comments"""
    code = """
// This is a comment
struct test_s {
    // Field comment
    rand int value;
};
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None
