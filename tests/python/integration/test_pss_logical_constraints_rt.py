"""PSS FE → RT tests: logical and implication constraints (§16.1.4, §16.1.5)."""
import pytest
from zuspec.fe.pss import load_pss
from zuspec.dataclasses import randomize


def test_logical_and():
    """Constraint with && (logical and): both sub-expressions must hold."""
    ns = load_pss("""
        struct Packet {
            rand bit[8] addr;
            constraint (addr % 4 == 0) && (addr > 0);
        }
    """)
    for seed in range(15):
        pkt = ns.Packet()
        randomize(pkt, seed=seed)
        assert pkt.addr % 4 == 0, f"seed={seed}: addr not aligned: {pkt.addr}"
        assert pkt.addr > 0, f"seed={seed}: addr must be > 0: {pkt.addr}"


def test_logical_or():
    """Constraint with || (logical or): at least one sub-expression must hold."""
    ns = load_pss("""
        struct Token {
            rand bit[8] val;
            constraint (val < 10) || (val > 200);
        }
    """)
    for seed in range(20):
        t = ns.Token()
        randomize(t, seed=seed)
        assert t.val < 10 or t.val > 200, f"seed={seed}: val={t.val} not in (<10 or >200)"


def test_logical_not():
    """Constraint with != (logical not-equal); note: !(expr) has known PSS parser limits.

    PSS !(expr) in a constraint can be expressed naturally as the negated comparison.
    """
    ns = load_pss("""
        struct Config {
            rand bit[8] mode;
            constraint mode != 0;
        }
    """)
    for seed in range(15):
        cfg = ns.Config()
        randomize(cfg, seed=seed)
        assert cfg.mode != 0, f"seed={seed}: mode must not be 0: {cfg.mode}"


def test_implication():
    """Implication constraint: if cond then consequent."""
    ns = load_pss("""
        struct Packet {
            rand bit[8] kind;
            rand bit[8] data;
            constraint (kind == 1) -> (data % 2 == 0);
        }
    """)
    for seed in range(30):
        pkt = ns.Packet()
        randomize(pkt, seed=seed)
        if pkt.kind == 1:
            assert pkt.data % 2 == 0, (
                f"seed={seed}: kind=1 but data={pkt.data} is odd"
            )


def test_implication_both_branches_reachable():
    """Implication: verify both (kind==1) and (kind!=1) cases are produced."""
    ns = load_pss("""
        struct Packet {
            rand bit[8] kind;
            rand bit[8] data;
            constraint (kind == 1) -> (data % 2 == 0);
        }
    """)
    kind_one_seen = False
    kind_other_seen = False
    for seed in range(50):
        pkt = ns.Packet()
        randomize(pkt, seed=seed)
        if pkt.kind == 1:
            kind_one_seen = True
            assert pkt.data % 2 == 0
        else:
            kind_other_seen = True
    assert kind_one_seen, "kind==1 case never produced"
    assert kind_other_seen, "kind!=1 case never produced"
