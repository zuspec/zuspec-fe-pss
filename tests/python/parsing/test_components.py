"""
Tests for PSS components
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path for test_helpers
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import (
    parse_pss, get_symbol, has_symbol, assert_parse_ok,
    generate_components
)


def test_empty_component(parser):
    """Test parsing of empty component"""
    code = """
        component C {
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(root, "C")


def test_component_with_action(parser):
    """Test component containing an action"""
    code = """
        component pss_top {
            action A {
                rand int x;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    
    assert pss_top is not None
    assert has_symbol(pss_top, "A")


def test_multiple_components(parser):
    """Test multiple components at top level"""
    code = """
        component A { }
        component B { }
        component pss_top { }
    """
    root = parse_pss(code, parser=parser)
    
    assert has_symbol(root, "A")
    assert has_symbol(root, "B")
    assert has_symbol(root, "pss_top")


def test_component_inheritance(parser):
    """Test component inheritance"""
    code = """
        component Base {
            action A { }
        }
        
        component Derived : Base {
            action B { }
        }
    """
    root = parse_pss(code, parser=parser)
    
    assert has_symbol(root, "Base")
    assert has_symbol(root, "Derived")


def test_component_with_component_field(parser):
    """Test component containing another component as a field"""
    code = """
        component Inner {
            action A { }
        }
        
        component Outer {
            Inner inner_inst;
        }
    """
    root = parse_pss(code, parser=parser)
    
    assert has_symbol(root, "Inner")
    assert has_symbol(root, "Outer")


def test_component_with_struct(parser):
    """Test component with struct definition"""
    code = """
        component pss_top {
            struct Point {
                int x;
                int y;
            }
            
            action Move {
                Point dest;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    
    assert has_symbol(pss_top, "Point")
    assert has_symbol(pss_top, "Move")


def test_pure_component(parser):
    """Test pure component modifier"""
    code = """
        pure component Utility {
            action Helper { }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(root, "Utility")


@pytest.mark.parametrize("num_components", [5, 10, 20])
def test_many_components(parser, num_components):
    """Test parsing many components"""
    code = generate_components(num_components)
    root = parse_pss(code, parser=parser)
    
    for i in range(num_components):
        assert has_symbol(root, f"C{i}"), f"Component C{i} not found"


def test_component_with_field(parser):
    """Test component with field"""
    code = """
        component Inner { }
        
        component Outer {
            Inner inst;
        }
    """
    root = parse_pss(code, parser=parser)
    
    assert has_symbol(root, "Inner")
    assert has_symbol(root, "Outer")


def test_component_extension(parser):
    """Test component extension"""
    code = """
        component Base {
            action A { }
        }
        
        extend component Base {
            action B { }
        }
    """
    root = parse_pss(code, parser=parser)
    base = get_symbol(root, "Base")
    
    assert base is not None
    # After extension, both actions should be accessible
    assert has_symbol(base, "A")
    assert has_symbol(base, "B")


def test_pss_top_component(parser):
    """Test pss_top component (standard entry point)"""
    code = """
        component pss_top {
            action entry {
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    
    assert pss_top is not None
    assert has_symbol(pss_top, "entry")
