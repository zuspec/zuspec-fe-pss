"""Full-pipeline simulation tests: PSS source -> parser -> IR -> lowering -> SV -> sim.

Each test starts from PSS source text and exercises the complete pipeline:
1. pssparser.Parser parses PSS text
2. AstToIrTranslator produces IR
3. pss_to_sv() lowers IR to SV IR nodes
4. emit_files() writes SV to disk (with runtime library)
5. DFM compiles and simulates on Questa / VCS
6. sim.log is checked for TEST_PASSED / $fatal absence

Because the PSS standard library produces types with unresolved
template parameters (TRAIT, Te, Tc), we filter the IR to only include
user-defined types before lowering.
"""
import os
import sys
import types as pytypes
from pathlib import Path

import pytest

# Stub avoidance: pssparser must be available for these tests
try:
    from pssparser import Parser
    HAS_PARSER = True
except ImportError:
    HAS_PARSER = False

if HAS_PARSER:
    from zuspec.fe.pss.ast_to_ir import AstToIrTranslator, AstToIrContext
    from zuspec.fe.pss.sv.pss_to_sv import pss_to_sv
    from zuspec.fe.pss.sv.emit_files import emit_files
    from zuspec.fe.pss.sv.lower_top import generate_top_module
    from zuspec.be.sv.ir.sv_emit import SVEmitter
    from zuspec.dataclasses import ir

from .conftest import AVAILABLE_SIMS, run_sim

pytestmark = pytest.mark.skipif(not HAS_PARSER, reason="pssparser not available")

# Standard library package prefixes to filter out
_STDLIB_PREFIXES = (
    "bool", "int", "string", "bit[", "int[",
    "array", "list", "set", "map",
    "sync_pkg::", "channel_c",
    "std_pkg::", "packed_s", "actor_c",
    "executor_pkg::", "executor_trait_s", "empty_executor_trait_s",
    "executor_base_c", "executor_c", "executor_group_c",
    "executor_group_default_c", "executor_claim_s",
    "addr_reg_pkg::", "addr_space_base_c", "addr_space_group_c",
    "addr_trait_s", "empty_addr_trait_s", "addr_handle_t",
    "contiguous_addr_space_c", "transparent_addr_space_c",
    "addr_region_base_s", "addr_region_s", "transparent_addr_region_s",
    "addr_claim_base_s", "addr_claim_s", "transparent_addr_claim_s",
    "sizeof_s", "sized_addr_handle_s",
    "reg_c", "reg_group_c", "reg_access",
    "endianness_e", "message_verbosity_e",
    "put_a", "get_a",
)


def _is_user_type(name):
    """Return True if type name is user-defined (not PSS stdlib)."""
    for prefix in _STDLIB_PREFIXES:
        if name == prefix or name.startswith(prefix):
            return False
    return True


def _pss_to_sv_files(pss_text, output_dir, comp_type, root_action_type,
                     has_activity=True, top_sv_override=None):
    """Full pipeline: PSS text -> parse -> IR -> filter -> lower -> write files.

    Returns list of written file paths.
    """
    parser = Parser()
    parser.parses([("test.pss", pss_text)])
    root = parser.link()
    ir_ctx = AstToIrTranslator().translate(root)
    assert not ir_ctx.errors, f"IR translation errors: {ir_ctx.errors}"

    # Filter to user types only
    filtered_ctx = AstToIrContext()
    for name, dtype in ir_ctx.type_map.items():
        if _is_user_type(name):
            filtered_ctx.add_type(name, dtype)
    filtered_ctx.parent_comp_names = {
        k: v for k, v in ir_ctx.parent_comp_names.items() if _is_user_type(k)
    }

    sv_nodes = pss_to_sv(filtered_ctx)

    rt_path = (Path(__file__).resolve().parents[3]
               / "src" / "zuspec" / "fe" / "pss" / "share" / "sv" / "zsp_rt_pkg.sv")

    if top_sv_override:
        files = emit_files(sv_nodes, output_dir,
                           runtime_lib_path=rt_path if rt_path.exists() else None)
        (Path(output_dir) / "zsp_top.sv").write_text(top_sv_override)
        files.append(Path(output_dir) / "zsp_top.sv")
    else:
        top = generate_top_module(
            comp_type=comp_type,
            root_action_type=root_action_type,
            has_activity=has_activity,
        )
        files = emit_files(sv_nodes, output_dir,
                           runtime_lib_path=rt_path if rt_path.exists() else None,
                           top_module_node=top)
    return files


# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------

@pytest.mark.parametrize("sim", AVAILABLE_SIMS)
def test_pss_simple_action(tmpdir, sim):
    """Minimal PSS: one component, one action with rand field + constraint."""
    pss = """\
component top_c {
    action hello {
        rand bit[32] addr;
        constraint addr_c { addr >= 256; }
    }
}
"""
    sv_dir = str(Path(str(tmpdir)) / "sv_out")
    top_sv = """\
module zsp_test_top;
    import zsp_rt_pkg::*;
    import zsp_gen_pkg::*;

    initial begin
        automatic top_c comp_inst = new("top", null);
        automatic top_c__hello act = new();
        act.comp = comp_inst;
        if (!act.randomize())
            $fatal(1, "randomize failed");
        if (act.addr < 256)
            $fatal(1, "FAIL: addr=%0d < 256", act.addr);
        $display("[ACTION] addr=%0d", act.addr);
        $display("TEST_PASSED");
        $finish;
    end
endmodule
"""
    _pss_to_sv_files(pss, sv_dir, "top_c", "top_c__hello",
                     has_activity=False, top_sv_override=top_sv)

    status, log = run_sim(tmpdir, sim, sv_dir)
    assert status == 0, f"Sim failed:\n{log}"
    assert "TEST_PASSED" in log, f"TEST_PASSED not in log:\n{log}"


@pytest.mark.parametrize("sim", AVAILABLE_SIMS)
def test_pss_two_actions_with_constraints(tmpdir, sim):
    """Two actions in one component, each with different constraints."""
    pss = """\
component top_c {
    action write_a {
        rand bit[16] addr;
        rand bit[8] data;
        constraint addr_c { addr % 4 == 0; }
    }
    action read_a {
        rand bit[16] addr;
        constraint addr_c { addr < 1024; }
    }
}
"""
    sv_dir = str(Path(str(tmpdir)) / "sv_out")
    top_sv = """\
module zsp_test_top;
    import zsp_rt_pkg::*;
    import zsp_gen_pkg::*;

    initial begin
        automatic top_c comp_inst = new("top", null);

        begin
            automatic top_c__write_a wr = new();
            wr.comp = comp_inst;
            if (!wr.randomize()) $fatal(1, "write randomize failed");
            if (wr.addr % 4 != 0)
                $fatal(1, "FAIL: write addr=%0d not aligned", wr.addr);
            $display("[WRITE] addr=%0d data=%0d", wr.addr, wr.data);
        end

        begin
            automatic top_c__read_a rd = new();
            rd.comp = comp_inst;
            if (!rd.randomize()) $fatal(1, "read randomize failed");
            if (rd.addr >= 1024)
                $fatal(1, "FAIL: read addr=%0d >= 1024", rd.addr);
            $display("[READ] addr=%0d", rd.addr);
        end

        $display("TEST_PASSED");
        $finish;
    end
endmodule
"""
    _pss_to_sv_files(pss, sv_dir, "top_c", "top_c__write_a",
                     has_activity=False, top_sv_override=top_sv)

    status, log = run_sim(tmpdir, sim, sv_dir)
    assert status == 0, f"Sim failed:\n{log}"
    assert "TEST_PASSED" in log, f"TEST_PASSED not in log:\n{log}"
    assert "[WRITE]" in log
    assert "[READ]" in log


@pytest.mark.parametrize("sim", AVAILABLE_SIMS)
def test_pss_component_tree(tmpdir, sim):
    """PSS component hierarchy lowered to SV class tree."""
    pss = """\
component child_c {
    action work {
        rand bit[8] val;
    }
}
component top_c {
    child_c child;
}
"""
    sv_dir = str(Path(str(tmpdir)) / "sv_out")
    top_sv = """\
module zsp_test_top;
    import zsp_rt_pkg::*;
    import zsp_gen_pkg::*;

    initial begin
        automatic top_c root_comp = new("top", null);

        if (root_comp.get_full_name() != "top")
            $fatal(1, "FAIL: root name=%s", root_comp.get_full_name());

        $display("[COMP] root=%s", root_comp.get_full_name());
        $display("TEST_PASSED");
        $finish;
    end
endmodule
"""
    _pss_to_sv_files(pss, sv_dir, "top_c", "child_c__work",
                     has_activity=False, top_sv_override=top_sv)

    status, log = run_sim(tmpdir, sim, sv_dir)
    assert status == 0, f"Sim failed:\n{log}"
    assert "TEST_PASSED" in log, f"TEST_PASSED not in log:\n{log}"


@pytest.mark.parametrize("sim", AVAILABLE_SIMS)
def test_pss_generated_top(tmpdir, sim):
    """Use fully generated top module (no hand-written override)."""
    pss = """\
component top_c {
    action hello {
        rand bit[8] val;
    }
}
"""
    sv_dir = str(Path(str(tmpdir)) / "sv_out")
    _pss_to_sv_files(pss, sv_dir, "top_c", "top_c__hello", has_activity=False)

    status, log = run_sim(tmpdir, sim, sv_dir)
    assert status == 0, f"Sim failed:\n{log}"
    assert "Scenario complete" in log, f"Scenario complete not in log:\n{log}"


@pytest.mark.parametrize("sim", AVAILABLE_SIMS)
def test_pss_multiple_rand_fields(tmpdir, sim):
    """Action with multiple rand fields and inter-field constraint."""
    pss = """\
component top_c {
    action xfer {
        rand bit[32] src_addr;
        rand bit[32] dst_addr;
        rand bit[16] length;
        constraint len_c { length in [1..4096]; }
        constraint diff_c { src_addr != dst_addr; }
    }
}
"""
    sv_dir = str(Path(str(tmpdir)) / "sv_out")
    top_sv = """\
module zsp_test_top;
    import zsp_rt_pkg::*;
    import zsp_gen_pkg::*;

    initial begin
        automatic top_c comp_inst = new("top", null);
        automatic top_c__xfer act = new();
        act.comp = comp_inst;

        if (!act.randomize())
            $fatal(1, "randomize failed");

        if (act.length < 1 || act.length > 4096)
            $fatal(1, "FAIL: length=%0d out of range", act.length);
        if (act.src_addr == act.dst_addr)
            $fatal(1, "FAIL: src==dst");

        $display("[XFER] src=0x%08h dst=0x%08h len=%0d",
                 act.src_addr, act.dst_addr, act.length);
        $display("TEST_PASSED");
        $finish;
    end
endmodule
"""
    _pss_to_sv_files(pss, sv_dir, "top_c", "top_c__xfer",
                     has_activity=False, top_sv_override=top_sv)

    status, log = run_sim(tmpdir, sim, sv_dir)
    assert status == 0, f"Sim failed:\n{log}"
    assert "TEST_PASSED" in log, f"TEST_PASSED not in log:\n{log}"
