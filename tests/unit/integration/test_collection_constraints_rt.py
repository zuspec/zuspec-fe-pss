"""Runtime integration tests for PSS collection constraints.

Covers:
- Direct array element indexing in constraints: data[0] < 10
- Index-style foreach inside braces: constraint { foreach (data[i]) { data[i] > 50; } }
- Element-style foreach in braces: constraint { foreach (e : arr) { e > 0; } }
- Constraints mixing scalar and array fields
"""
import pytest
from zuspec.fe.pss import load_pss
from zuspec.dataclasses import randomize


class TestDirectArrayIndexConstraints:
    def test_single_element_bound(self):
        """data[0] < 10 constrains just the first element."""
        ns = load_pss("""
            struct Foo {
                rand bit[8] data[4];
                constraint { data[0] < 10; }
            }
        """)
        obj = ns.Foo()
        randomize(obj, seed=1)
        assert obj.data[0] < 10, f"data[0]={obj.data[0]} must be < 10"
        assert 0 <= obj.data[1] <= 255

    def test_multiple_element_bounds(self):
        """data[0] < 10 and data[1] > 100 — two separate element constraints."""
        ns = load_pss("""
            struct Foo {
                rand bit[8] data[4];
                constraint { data[0] < 10; data[1] > 100; }
            }
        """)
        obj = ns.Foo()
        randomize(obj, seed=2)
        assert obj.data[0] < 10,  f"data[0]={obj.data[0]} must be < 10"
        assert obj.data[1] > 100, f"data[1]={obj.data[1]} must be > 100"

    def test_last_element_constraint(self):
        """Constraint on the last element of a fixed array."""
        ns = load_pss("""
            struct Tail {
                rand bit[8] arr[4];
                constraint { arr[3] == 0; }
            }
        """)
        obj = ns.Tail()
        randomize(obj, seed=5)
        assert obj.arr[3] == 0, f"arr[3]={obj.arr[3]} must be 0"


class TestForeachIndexStyle:
    """foreach (arr[i]) { arr[i] > 0; } — index-style foreach inside braced block."""

    def test_all_elements_positive(self):
        ns = load_pss("""
            struct Packet {
                rand bit[8] data[4];
                constraint { foreach (data[i]) { data[i] > 50; } }
            }
        """)
        for seed in range(10):
            obj = ns.Packet()
            randomize(obj, seed=seed)
            assert all(x > 50 for x in obj.data), \
                f"seed={seed}: all data[] must be > 50, got {obj.data}"

    def test_upper_bound(self):
        ns = load_pss("""
            struct Bounded {
                rand bit[8] arr[3];
                constraint { foreach (arr[i]) { arr[i] < 100; } }
            }
        """)
        for seed in range(10):
            obj = ns.Bounded()
            randomize(obj, seed=seed)
            assert all(x < 100 for x in obj.arr), \
                f"seed={seed}: all arr[] must be < 100, got {obj.arr}"

    def test_range_constraint(self):
        ns = load_pss("""
            struct Ranged {
                rand bit[8] vals[4];
                constraint { foreach (vals[i]) { vals[i] >= 10; vals[i] <= 50; } }
            }
        """)
        for seed in range(10):
            obj = ns.Ranged()
            randomize(obj, seed=seed)
            assert all(10 <= v <= 50 for v in obj.vals), \
                f"seed={seed}: all vals[] must be in [10,50], got {obj.vals}"


class TestForeachElementStyleBraces:
    """foreach (e : arr) { ... } inside a braced constraint block."""

    def test_all_elements_lower_bound(self):
        ns = load_pss("""
            struct X {
                rand bit[8] vals[3];
                constraint { foreach (e : vals) { e > 10; e < 50; } }
            }
        """)
        for seed in range(10):
            obj = ns.X()
            randomize(obj, seed=seed)
            assert all(10 < v < 50 for v in obj.vals), \
                f"seed={seed}: all vals must be in (10,50), got {obj.vals}"


class TestMixedConstraints:
    def test_scalar_and_array(self):
        """A scalar constraint and an array foreach constraint together."""
        ns = load_pss("""
            struct Mixed {
                rand bit[8] limit;
                rand bit[8] data[3];
                constraint { limit < 50; }
                constraint { foreach (data[i]) { data[i] < 20; } }
            }
        """)
        for seed in range(10):
            obj = ns.Mixed()
            randomize(obj, seed=seed)
            assert obj.limit < 50, f"seed={seed}: limit={obj.limit} must be < 50"
            assert all(d < 20 for d in obj.data), \
                f"seed={seed}: all data[] must be < 20, got {obj.data}"
