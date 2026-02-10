"""
Tests for basic PSS actions - demonstrating pytest patterns
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path for test_helpers
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import (
    parse_pss, get_symbol, has_symbol, assert_parse_ok,
    assert_parse_error, assert_linked, generate_actions
)


def test_empty_action(parser):
    """Test parsing of empty action"""
    code = """
        component pss_top {
            action A {
            }
        }
    """
    root = parse_pss(code, parser=parser)
    
    # Verify component exists
    pss_top = assert_linked(root, "pss_top")
    
    # Verify action exists
    action_a = assert_linked(pss_top, "A")
    assert action_a is not None


def test_action_with_field(parser):
    """Test action with a field"""
    code = """
        component pss_top {
            action A {
                int x;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    
    assert has_symbol(pss_top, "A")


def test_action_with_rand_field(parser):
    """Test action with random field"""
    code = """
        component pss_top {
            action A {
                rand int x;
            }
        }
    """
    root = assert_parse_ok(code)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_action_with_constraint(parser):
    """Test action with constraint block"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    x > 0;
                    x < 100;
                }
            }
        }
    """
    root = assert_parse_ok(code)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


@pytest.mark.parametrize("action_type,keyword", [
    ("action", "action"),
    ("abstract action", "abstract action"),
])
def test_action_types(parser, action_type, keyword):
    """Test different action type modifiers"""
    code = f"""
        component pss_top {{
            {keyword} A {{
            }}
        }}
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_action_inheritance(parser):
    """Test action inheritance"""
    code = """
        component pss_top {
            action Base {
                rand int x;
            }
            
            action Derived : Base {
                rand int y;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    
    # Both actions should exist
    assert has_symbol(pss_top, "Base")
    assert has_symbol(pss_top, "Derived")


def test_multiple_actions(parser):
    """Test multiple actions in component"""
    code = """
        component pss_top {
            action A { }
            action B { }
            action C { }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    
    assert has_symbol(pss_top, "A")
    assert has_symbol(pss_top, "B")
    assert has_symbol(pss_top, "C")


@pytest.mark.parametrize("num_actions", [10, 50, 100])
def test_many_actions(parser, num_actions):
    """Test parsing many actions"""
    code = generate_actions(num_actions)
    root = parse_pss(code, parser=parser)
    
    pss_top = get_symbol(root, "pss_top")
    assert pss_top is not None
    
    # Verify all actions exist
    for i in range(num_actions):
        assert has_symbol(pss_top, f"A{i}"), f"Action A{i} not found"


def test_action_with_exec_block(parser):
    """Test action with exec block"""
    code = """
        component pss_top {
            action A {
                exec body {
                    int x = 5;
                }
            }
        }
    """
    root = assert_parse_ok(code)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_action_invalid_syntax():
    """Test that invalid action syntax is rejected"""
    code = """
        component pss_top {
            action {  // Missing name
            }
        }
    """
    assert_parse_error(code)


def test_action_duplicate_name():
    """Test duplicate action names"""
    code = """
        component pss_top {
            action A { }
            action A { }  // Duplicate
        }
    """
    # This should parse but may fail at link time
    # TODO: Add proper duplicate checking when API available
    root = parse_pss(code)
    assert root is not None


def test_abstract_action(parser):
    """Test abstract action"""
    code = """
        component pss_top {
            abstract action A {
                rand int x;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_action_with_flow_objects(parser):
    """Test action with flow object fields (input/output)"""
    code = """
        buffer Data_t { };
        
        component pss_top {
            action A {
                input Data_t in_data;
                output Data_t out_data;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")
