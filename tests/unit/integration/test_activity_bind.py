"""T2-1: ActivityBind translation from PSS AST to IR."""
from __future__ import annotations
import os
import tempfile
import pytest

from zuspec.fe.pss import Parser, AstToIrTranslator
from zuspec.ir.core.activity import ActivityBind
from zuspec.ir.core.data_type import DataTypeClass

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

PSS_SRC = """\
component pss_top {
    stream data_t { rand bit[8] val; }
    action producer { output data_t out_data; }
    action consumer { input data_t in_data; }
    action test {
        producer p;
        consumer c;
        activity {
            p;
            c;
            bind p.out_data c.in_data;
        }
    }
}
"""


def _build_ctx(src: str):
    with tempfile.NamedTemporaryFile(suffix='.pss', mode='w', delete=False) as f:
        f.write(src)
        fname = f.name
    try:
        p = Parser()
        p.parse([fname])
        root = p.link()
        return AstToIrTranslator().translate(root)
    finally:
        try:
            os.unlink(fname)
        except OSError:
            pass


def _collect_binds(stmts):
    """Recursively collect all ActivityBind nodes from a stmt list."""
    result = []
    for s in stmts:
        if isinstance(s, ActivityBind):
            result.append(s)
        for attr in ("stmts", "body", "if_body", "else_body"):
            child_list = getattr(s, attr, [])
            if child_list:
                result.extend(_collect_binds(child_list))
    return result


def test_activity_bind_not_none():
    """ActivityBindStmt should produce an ActivityBind IR node, not None."""
    ctx = _build_ctx(PSS_SRC)
    test_ir = ctx.type_map.get("pss_top::test")
    assert test_ir is not None
    assert test_ir.activity_ir is not None
    binds = _collect_binds(test_ir.activity_ir.stmts)
    assert len(binds) >= 1, "Expected at least one ActivityBind in activity IR"


def test_activity_bind_src_path():
    """ActivityBind.src should be an ExprAttribute chain ending in 'out_data'."""
    ctx = _build_ctx(PSS_SRC)
    test_ir = ctx.type_map.get("pss_top::test")
    binds = _collect_binds(test_ir.activity_ir.stmts)
    assert binds, "No ActivityBind found"
    from zuspec.ir.core.expr import ExprAttribute
    bind = binds[0]
    assert isinstance(bind.src, ExprAttribute), \
        f"Expected ExprAttribute for src, got {type(bind.src).__name__}"
    assert bind.src.attr == "out_data", \
        f"Expected src.attr='out_data', got {bind.src.attr!r}"


def test_activity_bind_dst_path():
    """ActivityBind.dst should be an ExprAttribute chain ending in 'in_data'."""
    ctx = _build_ctx(PSS_SRC)
    test_ir = ctx.type_map.get("pss_top::test")
    binds = _collect_binds(test_ir.activity_ir.stmts)
    from zuspec.ir.core.expr import ExprAttribute
    bind = binds[0]
    assert isinstance(bind.dst, ExprAttribute)
    assert bind.dst.attr == "in_data"
