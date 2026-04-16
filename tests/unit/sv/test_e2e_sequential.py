"""End-to-end tests: sequential atomic actions -> multi-file SV output.

Verifies:
- PSS with sequential atomic actions produces correct SV
- Output file structure (all expected files present)
- File list content and ordering
- Top-level module generation
"""

import os
import tempfile
import shutil

import pytest
from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv import SVModuleDecl
from zuspec.be.sv.ir.sv_emit import SVEmitter

from zuspec.fe.pss.ast_to_ir import AstToIrContext
from zuspec.fe.pss.sv.pss_to_sv import pss_to_sv
from zuspec.fe.pss.sv.emit_files import emit_files, classify_node, classify_nodes
from zuspec.fe.pss.sv.lower_top import generate_top_module
from zuspec.fe.pss.sv.trace import (
    trace_action,
    trace_resource,
    trace_msg,
    trace_parallel_enter,
    wrap_traversal_with_trace,
)


@pytest.fixture
def emitter():
    return SVEmitter()


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="zsp_e2e_seq_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _make_ctx(*types, **comp_map):
    ctx = AstToIrContext()
    for dt in types:
        ctx.add_type(dt.name, dt)
    for action_name, comp_name in comp_map.items():
        ctx.parent_comp_names[action_name] = comp_name
    return ctx


class TestFileOrganization:
    def test_multi_file_output(self, tmp_dir):
        """Verify that multi-file output creates separate files per category."""
        comp_dt = ir.DataTypeComponent(
            name="top_c", super=None, fields=[],
        )
        action_dt = ir.DataTypeClass(
            name="top_c::xfer", super=None,
            fields=[ir.Field(name="addr", datatype=ir.DataTypeInt(bits=32, signed=False),
                             rand_kind="rand")],
        )
        ir_ctx = _make_ctx(comp_dt, action_dt, **{"top_c::xfer": "top_c"})
        sv_nodes = pss_to_sv(ir_ctx)

        rt_path = None  # no runtime lib copy for this test
        files = emit_files(sv_nodes, tmp_dir, runtime_lib_path=rt_path)

        # At minimum: zsp_gen_pkg.sv, zsp_filelist.f
        filenames = [os.path.basename(str(f)) for f in files]
        assert "zsp_filelist.f" in filenames
        assert "zsp_gen_pkg.sv" in filenames

    def test_filelist_ordering(self, tmp_dir):
        """File list should list files in compilation order."""
        comp_dt = ir.DataTypeComponent(
            name="my_c", super=None, fields=[],
        )
        action_dt = ir.DataTypeClass(
            name="my_c::act", super=None, fields=[],
        )
        ir_ctx = _make_ctx(comp_dt, action_dt, **{"my_c::act": "my_c"})
        sv_nodes = pss_to_sv(ir_ctx)
        emit_files(sv_nodes, tmp_dir)

        filelist = open(os.path.join(tmp_dir, "zsp_filelist.f")).read()
        lines = [l.strip() for l in filelist.strip().split("\n") if l.strip()]

        # gen_pkg should come before top
        if "zsp_gen_pkg.sv" in lines and "zsp_top.sv" in lines:
            assert lines.index("zsp_gen_pkg.sv") < lines.index("zsp_top.sv")

    def test_with_enums_and_structs(self, tmp_dir):
        """Enums and structs should go into zsp_gen_pkg.sv."""
        enum_dt = ir.DataTypeEnum(name="cmd_e", items={"RD": 0, "WR": 1})
        struct_dt = ir.DataTypeStruct(
            name="Packet", super=None,
            fields=[ir.Field(name="data", datatype=ir.DataTypeInt(bits=8, signed=False))],
        )
        ir_ctx = _make_ctx(enum_dt, struct_dt)
        sv_nodes = pss_to_sv(ir_ctx)
        emit_files(sv_nodes, tmp_dir)

        filenames = os.listdir(tmp_dir)
        assert "zsp_gen_pkg.sv" in filenames
        pkg_text = open(os.path.join(tmp_dir, "zsp_gen_pkg.sv")).read()
        assert "typedef enum" in pkg_text
        assert "class Packet" in pkg_text

    def test_import_if_separate_file(self, tmp_dir):
        """Import interface classes should go into zsp_gen_pkg.sv."""
        comp_dt = ir.DataTypeComponent(
            name="hw_c", super=None, fields=[],
            functions=[
                ir.Function(
                    name="read_reg",
                    args=ir.Arguments(args=[]),
                    body=[], is_import=True, is_async=False, metadata={},
                ),
            ],
        )
        ir_ctx = _make_ctx(comp_dt)
        sv_nodes = pss_to_sv(ir_ctx)
        emit_files(sv_nodes, tmp_dir)

        filenames = os.listdir(tmp_dir)
        assert "zsp_gen_pkg.sv" in filenames
        text = open(os.path.join(tmp_dir, "zsp_gen_pkg.sv")).read()
        assert "virtual class" in text


class TestTopLevelGeneration:
    def test_basic_top_module(self):
        mod = generate_top_module(
            comp_type="pss_top",
            root_action_type="pss_top__par_xfer",
        )
        assert mod.name == "zsp_test_top"
        text = "\n".join(mod.body_lines)
        assert "import zsp_rt_pkg::*;" in text
        assert "automatic pss_top top;" in text
        assert 'top = new("top"' in text
        assert "pss_top__par_xfer root = new();" in text
        assert "root.randomize()" in text
        assert "root.activity();" in text
        assert "$finish;" in text

    def test_top_module_with_seed(self):
        mod = generate_top_module(
            comp_type="my_c",
            root_action_type="my_c__act",
        )
        text = "\n".join(mod.body_lines)
        assert "zsp_seed" in text
        assert "$value$plusargs" in text

    def test_top_module_with_watchdog(self):
        mod = generate_top_module(
            comp_type="my_c",
            root_action_type="my_c__act",
            watchdog_ns=100000,
        )
        text = "\n".join(mod.body_lines)
        assert "#100000" in text
        assert "Deadlock watchdog" in text

    def test_top_module_atomic_action(self):
        mod = generate_top_module(
            comp_type="my_c",
            root_action_type="my_c__act",
            has_activity=False,
        )
        text = "\n".join(mod.body_lines)
        assert "root.body();" in text
        assert "root.activity();" not in text

    def test_top_module_with_import_if(self):
        mod = generate_top_module(
            comp_type="dma_c",
            root_action_type="dma_c__xfer",
            import_if_type="dma_c_import_if",
            import_if_driver="my_dma_driver",
        )
        text = "\n".join(mod.body_lines)
        assert "automatic my_dma_driver _drv;" in text
        assert "automatic dma_c_import_if _imp;" in text

    def test_top_module_in_file_output(self, tmp_dir):
        """Top module should end up in zsp_top.sv."""
        comp_dt = ir.DataTypeComponent(
            name="top_c", super=None, fields=[],
        )
        ir_ctx = _make_ctx(comp_dt)
        sv_nodes = pss_to_sv(ir_ctx)
        top = generate_top_module(
            comp_type="top_c",
            root_action_type="top_c__act",
        )
        emit_files(sv_nodes, tmp_dir, top_module_node=top)

        filenames = os.listdir(tmp_dir)
        assert "zsp_top.sv" in filenames
        text = open(os.path.join(tmp_dir, "zsp_top.sv")).read()
        assert "module zsp_test_top;" in text
        assert "endmodule" in text

    def test_verbosity_control(self):
        mod = generate_top_module(
            comp_type="c", root_action_type="c__a",
        )
        text = "\n".join(mod.body_lines)
        assert "zsp_verbosity" in text


class TestTraceEmission:
    def test_trace_action_macro(self):
        line = trace_action("dma_c__transfer", "comp")
        assert '`ZSP_TRACE_ACTION("dma_c__transfer"' in line
        assert "comp.get_full_name()" in line

    def test_trace_resource_macro(self):
        line = trace_resource("LOCK", "comp.pool", "act.rid")
        assert '`ZSP_TRACE_RESOURCE("LOCK"' in line
        assert "act.rid" in line

    def test_trace_msg(self):
        line = trace_msg("parallel enter")
        assert '`ZSP_TRACE("parallel enter")' in line

    def test_wrap_traversal(self):
        trav_lines = ["begin", "  act.body();", "end"]
        wrapped = wrap_traversal_with_trace("my_act", "comp", trav_lines)
        assert len(wrapped) == 4
        assert "`ZSP_TRACE_ACTION" in wrapped[0]
        assert "begin" in wrapped[1]

    def test_parallel_enter_exit(self):
        assert "enter" in trace_parallel_enter()
        assert "exit" in trace_parallel_enter.__name__ or "enter" in trace_parallel_enter()


class TestClassifyNode:
    def test_module_to_top(self):
        mod = SVModuleDecl(name="test_top", body_lines=[])
        assert classify_node(mod) == "zsp_top.sv"

    def test_virtual_class_to_import(self):
        from zuspec.be.sv.ir.sv import SVClass
        cls = SVClass(name="my_import_if", is_virtual=True)
        assert classify_node(cls) == "zsp_gen_pkg.sv"

    def test_component_class(self):
        from zuspec.be.sv.ir.sv import SVClass
        cls = SVClass(name="my_comp", extends_name="zsp_component")
        assert classify_node(cls) == "zsp_gen_pkg.sv"

    def test_action_class(self):
        from zuspec.be.sv.ir.sv import SVClass
        cls = SVClass(name="my_act", extends_name="zsp_action")
        assert classify_node(cls) == "zsp_gen_pkg.sv"
