"""PSS FE → RT tests: unique constraints (§16.1.9)."""
import pytest
from zuspec.fe.pss import load_pss
from zuspec.dataclasses import randomize


def test_unique_two_fields():
    """unique { a, b }: two fields must have distinct values."""
    ns = load_pss("""
        struct Pair {
            rand bit[8] a;
            rand bit[8] b;
            constraint { unique { a, b }; }
        }
    """)
    for seed in range(20):
        p = ns.Pair()
        randomize(p, seed=seed)
        assert p.a != p.b, f"seed={seed}: a={p.a} == b={p.b} (must be unique)"


def test_unique_three_fields():
    """unique { a, b, c }: all three fields must have distinct values."""
    ns = load_pss("""
        struct Triple {
            rand bit[8] a;
            rand bit[8] b;
            rand bit[8] c;
            constraint { unique { a, b, c }; }
        }
    """)
    for seed in range(20):
        t = ns.Triple()
        randomize(t, seed=seed)
        assert t.a != t.b, f"seed={seed}: a={t.a} == b={t.b}"
        assert t.b != t.c, f"seed={seed}: b={t.b} == c={t.c}"
        assert t.a != t.c, f"seed={seed}: a={t.a} == c={t.c}"


def test_unique_with_domain_constraint():
    """unique combined with domain constraints."""
    ns = load_pss("""
        struct Sel {
            rand bit[4] x;
            rand bit[4] y;
            constraint x < 8;
            constraint y < 8;
            constraint { unique { x, y }; }
        }
    """)
    for seed in range(20):
        s = ns.Sel()
        randomize(s, seed=seed)
        assert s.x < 8, f"seed={seed}: x={s.x} >= 8"
        assert s.y < 8, f"seed={seed}: y={s.y} >= 8"
        assert s.x != s.y, f"seed={seed}: x={s.x} == y={s.y}"
