"""PSS FE → RT tests: if-else constraints (§16.1.6)."""
import pytest
from zuspec.fe.pss import load_pss
from zuspec.dataclasses import randomize


def test_if_constraint():
    """if (cond) constraint block: conditional constraint."""
    ns = load_pss("""
        struct Packet {
            rand bit[8] kind;
            rand bit[8] data;
            constraint {
                if (kind == 1) {
                    data % 4 == 0;
                }
            }
        }
    """)
    for seed in range(30):
        pkt = ns.Packet()
        randomize(pkt, seed=seed)
        if pkt.kind == 1:
            assert pkt.data % 4 == 0, (
                f"seed={seed}: kind=1 but data={pkt.data} not aligned to 4"
            )


def test_if_else_constraint():
    """if-else constraint: different constraints for each branch."""
    ns = load_pss("""
        struct Packet {
            rand bit[8] kind;
            rand bit[8] data;
            constraint {
                if (kind == 0) {
                    data < 128;
                } else {
                    data >= 128;
                }
            }
        }
    """)
    for seed in range(30):
        pkt = ns.Packet()
        randomize(pkt, seed=seed)
        if pkt.kind == 0:
            assert pkt.data < 128, (
                f"seed={seed}: kind=0 but data={pkt.data} >= 128"
            )
        else:
            assert pkt.data >= 128, (
                f"seed={seed}: kind!=0 but data={pkt.data} < 128"
            )


def test_if_else_both_branches_reachable():
    """Both branches of if-else must be reachable across seeds."""
    ns = load_pss("""
        struct Packet {
            rand bit[8] kind;
            rand bit[8] data;
            constraint {
                if (kind == 0) {
                    data < 128;
                } else {
                    data >= 128;
                }
            }
        }
    """)
    branch_zero = False
    branch_nonzero = False
    for seed in range(50):
        pkt = ns.Packet()
        randomize(pkt, seed=seed)
        if pkt.kind == 0:
            branch_zero = True
        else:
            branch_nonzero = True
    assert branch_zero, "kind==0 branch never reached"
    assert branch_nonzero, "kind!=0 branch never reached"
