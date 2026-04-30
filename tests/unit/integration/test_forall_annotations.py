"""Tests for forall constraint support via PssAnnotation two-pass parse."""
import pytest
from zuspec.fe.pss import (
    load_pss, _preprocess_pss_pass1, _preprocess_pss,
    _transform_forall_foreach, _remove_covergroup_blocks,
    Parser, PssAnnotation,
)
from zuspec.dataclasses import randomize

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


# ---------------------------------------------------------------------------
# Unit: text transforms
# ---------------------------------------------------------------------------

def test_transform_forall_keyword_only():
    src = "constraint forall (p : pkts) { p < 8; }"
    out = _transform_forall_foreach(src, stub_body=False)
    assert 'foreach' in out
    assert 'forall' not in out
    assert 'p < 8' in out


def test_transform_forall_stub_body():
    src = "constraint forall (p : pkts) { p.x < 8; }"
    out = _transform_forall_foreach(src, stub_body=True)
    assert 'foreach' in out
    assert 'forall' not in out
    assert '0 == 0' in out
    assert 'p.x' not in out


def test_transform_preserves_existing_foreach():
    src = "constraint foreach (e : data) { e > 0; }"
    out = _transform_forall_foreach(src, stub_body=True)
    assert out == src   # untouched


def test_transform_multiline_forall():
    src = "constraint forall (p : pkts) {\n    p < 8;\n    p > 0;\n}"
    out = _transform_forall_foreach(src, stub_body=True)
    assert 'foreach' in out
    assert '0 == 0' in out
    assert 'p < 8' not in out


def test_preprocess_pass1_renames_only():
    src = "component pss_top { action t { rand bit[4] arr[3]; constraint forall (e : arr) { e < 8; } } }"
    out = _preprocess_pss_pass1(src)
    assert 'foreach' in out
    assert 'forall' not in out
    assert 'e < 8' in out   # body preserved in pass 1


def test_preprocess_full_stubs_body():
    src = "component pss_top { action t { rand bit[4] arr[3]; constraint forall (e : arr) { e < 8; } } }"
    out = _preprocess_pss(src)
    assert 'foreach' in out
    assert '0 == 0' in out
    assert 'e < 8' not in out   # body stubbed in pass 2


# ---------------------------------------------------------------------------
# Integration: annotation extraction
# ---------------------------------------------------------------------------

def test_forall_annotation_extracted():
    """Parser extracts a forall annotation with correct metadata."""
    pss = """
    component pss_top {
        action test {
            rand bit[8] arr[4];
            constraint forall (e : arr) { e < 100; }
        }
    }
    """
    parser = Parser()
    parser.parses([('t.pss', pss)])
    anns = [a for a in parser.annotations if a.kind == 'forall']
    assert len(anns) == 1
    ann = anns[0]
    assert ann.type_chain == ['pss_top', 'test']
    assert ann.data['iterator'] == 'e'
    assert ann.data['collection'] == ['arr']
    assert len(ann.data['body_ast']) == 1


# ---------------------------------------------------------------------------
# Integration: forall scalar constraint enforced at runtime
# ---------------------------------------------------------------------------

def test_forall_scalar_upper_bound():
    """constraint forall (e : arr) { e < 50; } — all elements < 50."""
    ns = load_pss("""
        struct Vals {
            rand bit[8] arr[4];
            constraint forall (e : arr) { e < 50; }
        }
    """)
    for seed in range(20):
        v = ns.Vals()
        randomize(v, seed=seed)
        for i in range(4):
            assert v.arr[i] < 50, f"seed={seed}: arr[{i}]={v.arr[i]} should be < 50"


def test_forall_scalar_lower_bound():
    """constraint forall (e : vals) { e > 10; } — all elements > 10."""
    ns = load_pss("""
        struct Pos {
            rand bit[8] vals[3];
            constraint forall (e : vals) { e > 10; }
        }
    """)
    for seed in range(20):
        p = ns.Pos()
        randomize(p, seed=seed)
        for i in range(3):
            assert p.vals[i] > 10, f"seed={seed}: vals[{i}]={p.vals[i]} should be > 10"


def test_forall_combined_with_scalar_constraint():
    """forall constraint works alongside a regular scalar constraint."""
    ns = load_pss("""
        struct Mixed {
            rand bit[4] limit;
            rand bit[4] vals[3];
            constraint limit < 8;
            constraint forall (v : vals) { v < 8; }
        }
    """)
    for seed in range(20):
        m = ns.Mixed()
        randomize(m, seed=seed)
        assert m.limit < 8
        for i in range(3):
            assert m.vals[i] < 8, f"seed={seed}: vals[{i}]={m.vals[i]} should be < 8"


def test_forall_in_range():
    """constraint forall (e : data) { e in [5..20]; }"""
    ns = load_pss("""
        struct Ranged {
            rand bit[8] data[4];
            constraint forall (e : data) { e in [5..20]; }
        }
    """)
    for seed in range(20):
        r = ns.Ranged()
        randomize(r, seed=seed)
        for i in range(4):
            assert 5 <= r.data[i] <= 20, f"seed={seed}: data[{i}]={r.data[i]} not in [5,20]"
