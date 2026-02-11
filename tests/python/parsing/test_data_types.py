"""
Tests for PSS data types including primitives and collections.

Tests cover:
- Primitive types (int, bit, bool, string)
- Sized types (int[N], bit[N])
- Collection types (array, list, map, set)
- Type usage in various contexts
"""

import pytest
from zuspec.fe.pss import Parser
from ..test_helpers import parse_pss, assert_parse_ok, assert_parse_error


def test_type_int(parser):
    """Test int type"""
    code = """
    struct test_s {
        rand int value;
    };
    """
    assert_parse_ok(code, parser)


def test_type_bit(parser):
    """Test bit type"""
    code = """
    struct test_s {
        rand bit[8] value;
    };
    """
    assert_parse_ok(code, parser)


def test_type_bool(parser):
    """Test bool type"""
    code = """
    struct test_s {
        rand bool flag;
    };
    """
    assert_parse_ok(code, parser)


def test_type_string(parser):
    """Test string type"""
    code = """
    struct test_s {
        string message;
    };
    """
    assert_parse_ok(code, parser)


def test_type_sized_int(parser):
    """Test sized int type"""
    code = """
    struct test_s {
        rand int[16] value;
    };
    """
    assert_parse_ok(code, parser)


def test_type_sized_bit_various(parser):
    """Test various bit sizes"""
    code = """
    struct test_s {
        rand bit[1] flag;
        rand bit[8] byte_val;
        rand bit[16] word_val;
        rand bit[32] dword_val;
    };
    """
    assert_parse_ok(code, parser)


def test_type_chandle(parser):
    """Test chandle type"""
    code = """
    struct test_s {
        chandle handle;
    };
    """
    assert_parse_ok(code, parser)


def test_type_array_fixed_size(parser):
    """Test fixed-size array"""
    code = """
    struct test_s {
        rand int values[10];
    };
    """
    assert_parse_ok(code, parser)


def test_type_array_of_arrays(parser):
    """Test array of fixed-size arrays (simulates 2D)"""
    code = """
    struct test_s {
        rand int row0[4];
        rand int row1[4];
        rand int row2[4];
        rand int row3[4];
    };
    """
    assert_parse_ok(code, parser)


def test_type_array_of_bits(parser):
    """Test array of bit type"""
    code = """
    struct test_s {
        rand bit[8] bytes[16];
    };
    """
    assert_parse_ok(code, parser)


def test_type_enum_as_type(parser):
    """Test enum used as a type"""
    code = """
    enum status_e { IDLE, BUSY, DONE };
    
    struct test_s {
        rand status_e status;
    };
    """
    assert_parse_ok(code, parser)


def test_type_struct_as_field(parser):
    """Test struct used as field type"""
    code = """
    struct inner_s {
        rand int value;
    };
    
    struct outer_s {
        inner_s inner;
    };
    """
    assert_parse_ok(code, parser)


def test_type_in_action_field(parser):
    """Test various types in action"""
    code = """
    component test_c {
        action test_a {
            rand int int_val;
            rand bit[8] bit_val;
            rand bool bool_val;
            string str_val;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_type_in_function_params(parser):
    """Test types in function parameters"""
    code = """
    function void process(int a, bit[8] b, bool c, string msg);
    """
    assert_parse_ok(code, parser)


def test_type_mixed_in_struct(parser):
    """Test mixing various types in struct"""
    code = """
    struct mixed_s {
        rand int int_field;
        rand bit[16] bit_field;
        rand bool bool_field;
        string str_field;
        chandle handle_field;
    };
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("size", [1, 8, 16, 32, 64])
def test_type_bit_sizes(parser, size):
    """Test various bit field sizes"""
    code = f"""
    struct test_s {{
        rand bit[{size}] value;
    }};
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("size", [8, 16, 32, 64])
def test_type_int_sizes(parser, size):
    """Test various int field sizes"""
    code = f"""
    struct test_s {{
        rand int[{size}] value;
    }};
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("array_size", [1, 10, 100])
def test_type_array_scalability(parser, array_size):
    """Test arrays of different sizes"""
    code = f"""
    struct test_s {{
        rand int values[{array_size}];
    }};
    """
    assert_parse_ok(code, parser)


def test_type_in_constraint(parser):
    """Test type usage in constraints"""
    code = """
    struct test_s {
        rand int[8] small_val;
        rand int[16] large_val;
        
        constraint {
            small_val < 100;
            large_val > 1000;
        }
    };
    """
    assert_parse_ok(code, parser)
