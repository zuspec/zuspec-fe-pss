"""T2-3, T2-4: Standard library stub parsing tests."""
from __future__ import annotations
import os
import tempfile
import pytest

from zuspec.fe.pss import Parser, AstToIrTranslator

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

_SML_PKG = os.path.join(
    os.path.dirname(__file__), '..', '..', '..',
    'src', 'zuspec', 'fe', 'pss', 'std_libs', 'sml_pkg.pss',
)


def _build_ctx(*files):
    p = Parser()
    p.parse(list(files))
    root = p.link()
    return AstToIrTranslator().translate(root)


def test_addr_reg_pkg_built_in(tmp_path):
    """addr_reg_pkg types are available from the built-in standard library (T2-3)."""
    # addr_reg_pkg is built into the PSS parser -- parse an empty file and check.
    pss_file = tmp_path / "empty.pss"
    pss_file.write_text("component pss_top {}\n")
    ctx = _build_ctx(str(pss_file))
    assert "addr_reg_pkg::addr_claim_s" in ctx.type_map, \
        "addr_reg_pkg::addr_claim_s not found -- built-in addr_reg_pkg missing"
    assert "addr_reg_pkg::contiguous_addr_space_c" in ctx.type_map


def test_sml_pkg_stub_parses(tmp_path):
    """sml_pkg stub parses without errors and registers key types (T2-4)."""
    ctx = _build_ctx(_SML_PKG)
    assert "sml_pkg::sml_core_r" in ctx.type_map, \
        "sml_pkg::sml_core_r not in type_map"
    assert "sml_pkg::sml_data_buff" in ctx.type_map, \
        "sml_pkg::sml_data_buff not in type_map"


def test_sml_pkg_move_data_fields(tmp_path):
    """sml_pkg.move_data has lock, input, and output fields (T2-4)."""
    ctx = _build_ctx(_SML_PKG)
    move_ir = ctx.type_map.get("sml_pkg::move_data")
    assert move_ir is not None, "sml_pkg::move_data not found"
    from zuspec.ir.core.fields import FieldKind
    kinds = {f.kind for f in move_ir.fields}
    assert FieldKind.Input in kinds, "move_data should have an Input field"
    assert FieldKind.Output in kinds, "move_data should have an Output field"
    assert FieldKind.Lock in kinds, "move_data should have a Lock field"
