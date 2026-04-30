"""T1-4: extend struct verification -- fields from base and extension both present."""
from __future__ import annotations
import os
import tempfile
import pytest

from zuspec.fe.pss import Parser, AstToIrTranslator

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

PSS_SRC = """\
buffer token_t {
    rand bit[8] x;
}
extend buffer token_t {
    rand bit[8] y;
}
component pss_top {
    action producer { output token_t tok; }
    action consumer { input token_t tok; }
    action test {
        producer p;
        consumer c;
        activity { p; c; }
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


def test_extend_struct_fields_merged():
    """After extend buffer token_t, the IR struct should have both x and y fields."""
    ctx = _build_ctx(PSS_SRC)
    token_ir = ctx.type_map.get("token_t")
    assert token_ir is not None, "token_t not found in type_map"
    field_names = {f.name for f in token_ir.fields}
    assert "x" in field_names, f"Field 'x' missing; fields={field_names}"
    assert "y" in field_names, f"Field 'y' missing; fields={field_names}"
