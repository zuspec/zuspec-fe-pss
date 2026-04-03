"""PSS FE → RT tests: in-set and in-range constraints (§8.5.9)."""
import pytest
from zuspec.fe.pss import load_pss
from zuspec.dataclasses import randomize


def test_in_set():
    """x in { val, val, ... }: value must be in the explicit set."""
    ns = load_pss("""
        struct Packet {
            rand bit[8] prio;
            constraint prio in [0, 1, 2, 7];
        }
    """)
    valid = {0, 1, 2, 7}
    for seed in range(30):
        pkt = ns.Packet()
        randomize(pkt, seed=seed)
        assert pkt.prio in valid, f"seed={seed}: prio={pkt.prio} not in {valid}"


def test_in_range():
    """x in [lo..hi]: value must fall within the range."""
    ns = load_pss("""
        struct Packet {
            rand bit[8] burst;
            constraint burst in [4..16];
        }
    """)
    for seed in range(30):
        pkt = ns.Packet()
        randomize(pkt, seed=seed)
        assert 4 <= pkt.burst <= 16, (
            f"seed={seed}: burst={pkt.burst} not in [4..16]"
        )


def test_in_set_all_values_reachable():
    """Every member of the set should be reachable across enough seeds."""
    ns = load_pss("""
        struct Token {
            rand bit[8] val;
            constraint val in [10, 20, 30];
        }
    """)
    seen = set()
    for seed in range(60):
        t = ns.Token()
        randomize(t, seed=seed)
        assert t.val in {10, 20, 30}, f"seed={seed}: val={t.val} not in set"
        seen.add(t.val)
    assert seen == {10, 20, 30}, f"Not all set members seen: {seen}"
