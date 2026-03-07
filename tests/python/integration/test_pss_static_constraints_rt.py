"""PSS FE → RT tests: static constraints (§16.1.1).

Each test:
  1. Defines a PSS struct with constraints in a Python string
  2. Loads it with load_pss() to get a randomizable Python class
  3. Instantiates and randomizes the class
  4. Asserts the constraint is satisfied
"""
import pytest
from zuspec.fe.pss import load_pss
from zuspec.dataclasses import randomize


def test_unnamed_constraint():
    """Unnamed inline constraint: constraint expr;"""
    ns = load_pss("""
        struct Packet {
            rand bit[8] addr;
            constraint addr % 4 == 0;
        }
    """)
    pkt = ns.Packet()
    randomize(pkt, seed=42)
    assert pkt.addr % 4 == 0, f"addr not aligned: {pkt.addr}"


def test_named_constraint_block():
    """Named constraint block: constraint name { expr; }"""
    ns = load_pss("""
        struct Packet {
            rand bit[8] addr;
            constraint aligned { addr % 4 == 0; }
        }
    """)
    pkt = ns.Packet()
    randomize(pkt, seed=42)
    assert pkt.addr % 4 == 0, f"addr not aligned: {pkt.addr}"


def test_multiple_constraints():
    """Multiple constraints all apply simultaneously."""
    ns = load_pss("""
        struct Packet {
            rand bit[8] addr;
            rand bit[8] data;
            constraint addr % 4 == 0;
            constraint data > 0;
        }
    """)
    for seed in range(10):
        pkt = ns.Packet()
        randomize(pkt, seed=seed)
        assert pkt.addr % 4 == 0, f"seed={seed}: addr not aligned: {pkt.addr}"
        assert pkt.data > 0, f"seed={seed}: data not positive: {pkt.data}"


def test_constraint_with_upper_bound():
    """Constraint limiting field to a subrange."""
    ns = load_pss("""
        struct Config {
            rand bit[8] burst_len;
            constraint burst_len <= 16;
        }
    """)
    for seed in range(20):
        cfg = ns.Config()
        randomize(cfg, seed=seed)
        assert cfg.burst_len <= 16, f"seed={seed}: burst_len={cfg.burst_len} > 16"


def test_constraint_relationship_between_fields():
    """Constraint relating two rand fields."""
    ns = load_pss("""
        struct Range {
            rand bit[8] lo;
            rand bit[8] hi;
            constraint lo < hi;
        }
    """)
    for seed in range(15):
        r = ns.Range()
        randomize(r, seed=seed)
        assert r.lo < r.hi, f"seed={seed}: lo={r.lo} >= hi={r.hi}"


def test_constraint_produces_varied_values():
    """Randomize should produce different values across seeds (not constant)."""
    ns = load_pss("""
        struct Token {
            rand bit[8] val;
            constraint val > 0;
        }
    """)
    values = set()
    for seed in range(30):
        t = ns.Token()
        randomize(t, seed=seed)
        assert t.val > 0, f"seed={seed}: val={t.val} must be > 0"
        values.add(t.val)
    assert len(values) > 1, "Expected varied values across seeds"
