"""T1-2: Lock/Share field detection through the full AST-to-IR pipeline."""
from __future__ import annotations
import asyncio
import os
import tempfile
import pytest

from zuspec.fe.pss import Parser, AstToIrTranslator, IrToRuntimeBuilder
from zuspec.ir.core.fields import FieldKind, Pool
from zuspec.ir.core.data_type import DataTypeClass

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

PSS_SRC = """\
component pss_top {
    resource ch_r {}
    abstract action xfer {
        lock ch_r channel;
        share ch_r shared_ch;
    }
    pool ch_r ch_pool;
    bind ch_pool *;
    action do_xfer : xfer {}
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


def test_lock_field_kind():
    """Lock resource field should have FieldKind.Lock in the action IR."""
    ctx = _build_ctx(PSS_SRC)
    xfer_ir = ctx.type_map.get("pss_top::xfer")
    assert xfer_ir is not None, "pss_top::xfer not found in type_map"
    lock_fields = [f for f in xfer_ir.fields if f.kind == FieldKind.Lock]
    assert len(lock_fields) == 1, f"Expected 1 Lock field, got {len(lock_fields)}"
    assert lock_fields[0].name == "channel"


def test_share_field_kind():
    """Share resource field should have FieldKind.Share in the action IR."""
    ctx = _build_ctx(PSS_SRC)
    xfer_ir = ctx.type_map.get("pss_top::xfer")
    assert xfer_ir is not None
    share_fields = [f for f in xfer_ir.fields if f.kind == FieldKind.Share]
    assert len(share_fields) == 1, f"Expected 1 Share field, got {len(share_fields)}"
    assert share_fields[0].name == "shared_ch"


def test_pool_inferred_for_resource():
    """Pool should be inferred for the resource type used in lock/share fields."""
    ctx = _build_ctx(PSS_SRC)
    comp_ir = ctx.type_map.get("pss_top")
    assert comp_ir is not None
    assert len(comp_ir.pools) > 0, "No pools inferred for resource type"
