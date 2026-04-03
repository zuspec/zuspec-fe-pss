"""PSS FE → RT tests: foreach constraints (§16.1.7)."""
import pytest
from zuspec.fe.pss import load_pss
from zuspec.dataclasses import randomize


def test_foreach_all_elements_positive():
    """foreach (e : data) { e > 0; }: all array elements must be positive."""
    ns = load_pss("""
        struct Buf {
            rand bit[8] data[4];
            constraint foreach (e : data) { e > 0; }
        }
    """)
    for seed in range(20):
        b = ns.Buf()
        randomize(b, seed=seed)
        for i in range(4):
            assert b.data[i] > 0, f"seed={seed}: data[{i}]={b.data[i]} must be > 0"


def test_foreach_upper_bound():
    """foreach (e : arr) { e < 100; }: all elements must be less than 100."""
    ns = load_pss("""
        struct Bounded {
            rand bit[8] arr[3];
            constraint foreach (e : arr) { e < 100; }
        }
    """)
    for seed in range(20):
        b = ns.Bounded()
        randomize(b, seed=seed)
        for i in range(3):
            assert b.arr[i] < 100, f"seed={seed}: arr[{i}]={b.arr[i]} must be < 100"


def test_foreach_range_constraint():
    """foreach (e : vals) { e >= 10 && e <= 50; }"""
    ns = load_pss("""
        struct Ranged {
            rand bit[8] vals[4];
            constraint foreach (e : vals) { e >= 10; e <= 50; }
        }
    """)
    for seed in range(20):
        r = ns.Ranged()
        randomize(r, seed=seed)
        for i in range(4):
            assert 10 <= r.vals[i] <= 50, \
                f"seed={seed}: vals[{i}]={r.vals[i]} must be in [10,50]"


def test_foreach_combined_with_scalar_constraint():
    """foreach constraint combined with a scalar constraint."""
    ns = load_pss("""
        struct Mixed {
            rand bit[4] threshold;
            rand bit[4] values[3];
            constraint threshold < 8;
            constraint foreach (v : values) { v < 8; }
        }
    """)
    for seed in range(20):
        m = ns.Mixed()
        randomize(m, seed=seed)
        assert m.threshold < 8, f"seed={seed}: threshold={m.threshold} must be < 8"
        for i in range(3):
            assert m.values[i] < 8, \
                f"seed={seed}: values[{i}]={m.values[i]} must be < 8"
