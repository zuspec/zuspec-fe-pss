"""T2-5: Package-qualified super-type resolution."""
from __future__ import annotations
import os
import tempfile
import pytest

from zuspec.fe.pss import Parser, AstToIrTranslator
from zuspec.ir.core.data_type import DataTypeRef

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

PSS_SRC = """\
package sys_pkg {
    abstract action base_a {}
}
component pss_top {
    action derived : sys_pkg::base_a {}
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


def test_package_qualified_super():
    """Action derived : sys_pkg::base_a should resolve super to base_a IR."""
    ctx = _build_ctx(PSS_SRC)
    derived_ir = ctx.type_map.get("pss_top::derived")
    assert derived_ir is not None, "pss_top::derived not in type_map"
    assert derived_ir.super is not None, "derived.super should not be None"
    # The super may be a DataTypeRef (if PSS linker re-exports the fully-qualified name)
    # or the actual DataTypeClass. Either way, the ref_name should point to base_a.
    if isinstance(derived_ir.super, DataTypeRef):
        assert "base_a" in derived_ir.super.ref_name, \
            f"Expected 'base_a' in ref_name, got {derived_ir.super.ref_name!r}"
    else:
        assert derived_ir.super.name is not None and "base_a" in derived_ir.super.name


def test_base_action_in_type_map():
    """sys_pkg::base_a should be in the type_map."""
    ctx = _build_ctx(PSS_SRC)
    assert "sys_pkg::base_a" in ctx.type_map, \
        "sys_pkg::base_a not found in type_map"
