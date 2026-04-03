"""Runtime integration tests for PSS inheritance (struct, component, action).

Verifies that:
- Child instances expose inherited fields as normal Python attributes
- The constraint solver randomizes *all* fields (inherited + own)
- Inherited constraints are enforced on child objects
- Python isinstance() returns True for a base class
- Multi-level (A -> B -> C) chains work end-to-end
"""
import pytest
from zuspec.fe.pss import load_pss
from zuspec.dataclasses import randomize


# ---------------------------------------------------------------------------
# Struct inheritance
# ---------------------------------------------------------------------------

class TestStructInheritance:
    def test_child_has_base_field(self):
        ns = load_pss("""
            struct Base { rand bit[8] x; }
            struct Child : Base { rand bit[8] y; }
        """)
        c = ns.Child()
        assert hasattr(c, 'x'), "Child must expose inherited field 'x'"
        assert hasattr(c, 'y')

    def test_randomize_includes_inherited_field(self):
        ns = load_pss("""
            struct Base { rand bit[8] x; }
            struct Child : Base { rand bit[8] y; }
        """)
        c = ns.Child()
        randomize(c, seed=7)
        assert 0 <= c.x <= 255
        assert 0 <= c.y <= 255

    def test_isinstance_of_base(self):
        ns = load_pss("""
            struct Base { rand bit[8] x; }
            struct Child : Base { rand bit[8] y; }
        """)
        c = ns.Child()
        assert isinstance(c, ns.Base)

    def test_inherited_constraint_enforced(self):
        ns = load_pss("""
            struct Base {
                rand bit[8] x;
                constraint { x < 10; }
            }
            struct Child : Base {
                rand bit[8] y;
                constraint { y > 200; }
            }
        """)
        ch = ns.Child()
        randomize(ch, seed=99)
        assert ch.x < 10,  f"Inherited constraint x<10 violated: x={ch.x}"
        assert ch.y > 200, f"Child constraint y>200 violated: y={ch.y}"

    def test_three_level_chain(self):
        ns = load_pss("""
            struct A { rand bit[8] a; }
            struct B : A { rand bit[8] b; }
            struct C : B { rand bit[8] c; }
        """)
        obj = ns.C()
        randomize(obj, seed=1)
        assert 0 <= obj.a <= 255
        assert 0 <= obj.b <= 255
        assert 0 <= obj.c <= 255


# ---------------------------------------------------------------------------
# Action inheritance
# ---------------------------------------------------------------------------

class TestActionInheritance:
    def test_action_child_has_base_field(self):
        ns = load_pss("""
            component C {
                action Base { rand bit[8] x; }
                action Child : Base { rand bit[8] y; }
            }
        """)
        comp = ns.C()
        child_action = ns['C::Child']()
        assert hasattr(child_action, 'x'), "Child action must expose inherited field 'x'"
        assert hasattr(child_action, 'y')

    def test_action_randomize_inherited_field(self):
        ns = load_pss("""
            component C {
                action Base { rand bit[8] x; }
                action Child : Base { rand bit[8] y; }
            }
        """)
        child_action = ns['C::Child']()
        randomize(child_action, seed=3)
        assert 0 <= child_action.x <= 255
        assert 0 <= child_action.y <= 255

    def test_action_inherited_constraint_enforced(self):
        ns = load_pss("""
            component C {
                action Base {
                    rand bit[8] x;
                    constraint { x < 50; }
                }
                action Child : Base {
                    rand bit[8] y;
                    constraint { y > 100; }
                }
            }
        """)
        child_action = ns['C::Child']()
        randomize(child_action, seed=77)
        assert child_action.x < 50,  f"Inherited constraint x<50 violated: x={child_action.x}"
        assert child_action.y > 100, f"Child constraint y>100 violated: y={child_action.y}"
