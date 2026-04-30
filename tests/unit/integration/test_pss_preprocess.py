"""Tests for the PSS source pre-processor that injects built-in fields."""
from __future__ import annotations
import os
import tempfile
import pytest

from zuspec.fe.pss import Parser, AstToIrTranslator, _preprocess_pss

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


# ------------------------------------------------------------------
# Unit tests for _preprocess_pss
# ------------------------------------------------------------------

def test_injects_initial_into_state():
    src = "state s { rand bit[8] x; }"
    out = _preprocess_pss(src)
    assert "bool initial;" in out
    assert out.index("bool initial;") < out.index("rand bit[8] x;")


def test_injects_instance_id_into_resource():
    src = "resource r { rand bit[4] mode; }"
    out = _preprocess_pss(src)
    assert "int instance_id;" in out


def test_no_double_injection_initial():
    src = "state s { bool initial; rand int x; }"
    out = _preprocess_pss(src)
    assert out.count("bool initial;") == 1


def test_no_double_injection_instance_id():
    src = "resource r { int instance_id; rand bit[4] cfg; }"
    out = _preprocess_pss(src)
    assert out.count("int instance_id;") == 1


def test_no_injection_into_struct():
    src = "struct s { rand int y; }"
    out = _preprocess_pss(src)
    assert "bool initial;" not in out
    assert "int instance_id;" not in out


def test_no_injection_inside_line_comment():
    src = "// state in_comment { }\nstruct s { int x; }"
    out = _preprocess_pss(src)
    assert "bool initial;" not in out


def test_state_with_inheritance():
    src = "state child_s : base_s { rand int x; }"
    out = _preprocess_pss(src)
    assert "bool initial;" in out


def test_state_constraint_initial_parseable():
    """Full parse+link of PSS with `constraint initial -> val == 0;`."""
    pss_src = """\
state power_s {
    rand bit[8] val;
    constraint initial -> val == 0;
}
component pss_top {
    pool power_s p;
    bind p *;
    action step { input power_s a; output power_s b; }
}
"""
    with tempfile.NamedTemporaryFile(suffix='.pss', mode='w', delete=False) as f:
        f.write(pss_src)
        fname = f.name
    try:
        p = Parser()
        p.parse([fname])  # pre-processor runs inside parse()
        root = p.link()   # should not raise "unknown identifier 'initial'"
        ctx = AstToIrTranslator().translate(root)
        st_ir = ctx.type_map.get("power_s")
        assert st_ir is not None
        assert "initial" in [fld.name for fld in st_ir.fields]
        assert st_ir.has_initial_constraint
    finally:
        try:
            os.unlink(fname)
        except OSError:
            pass


def test_resource_constraint_instance_id_parseable():
    """Full parse+link of PSS with `constraint instance_id < 2;`."""
    pss_src = """\
resource ch_r {
    constraint instance_id < 2;
}
component pss_top {
    pool ch_r ch;
    bind ch *;
    action xfer { lock ch_r c; }
}
"""
    with tempfile.NamedTemporaryFile(suffix='.pss', mode='w', delete=False) as f:
        f.write(pss_src)
        fname = f.name
    try:
        p = Parser()
        p.parse([fname])
        root = p.link()
        ctx = AstToIrTranslator().translate(root)
        ch_ir = ctx.type_map.get("ch_r")
        assert ch_ir is not None
        assert "instance_id" in [fld.name for fld in ch_ir.fields]
    finally:
        try:
            os.unlink(fname)
        except OSError:
            pass
