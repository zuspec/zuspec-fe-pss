"""Shared fixtures for PSS-to-SV simulation tests.

Provides:
- Simulator discovery (mti, vcs -- class/randomize capable)
- DFM-based compile+simulate helper
- IR -> lowering -> SV file generation helper
"""
import os
import sys
import types
import shutil
import asyncio
from pathlib import Path

import pytest

# Stub pssparser so zuspec.fe.pss can be imported without native lib
if "pssparser" not in sys.modules:
    _stub = types.ModuleType("pssparser")
    _stub.Parser = None
    _stub.ParseException = Exception
    sys.modules["pssparser"] = _stub
    _ast = types.ModuleType("pssparser.ast")
    sys.modules["pssparser.ast"] = _ast

from zuspec.dataclasses import ir
from zuspec.fe.pss.ast_to_ir import AstToIrContext
from zuspec.fe.pss.sv.pss_to_sv import pss_to_sv
from zuspec.fe.pss.sv.emit_files import emit_files
from zuspec.fe.pss.sv.lower_top import generate_top_module
from zuspec.be.sv.ir.sv_emit import SVEmitter


def _class_capable_sims():
    """Return list of available simulators that support SV classes + randomize."""
    sims = []
    for exe, tag in [("vsim", "mti"), ("vcs", "vcs")]:
        if shutil.which(exe) is not None:
            sims.append(tag)
    return sims


AVAILABLE_SIMS = _class_capable_sims()


def _get_runtime_lib_path():
    rt = (Path(__file__).resolve().parents[3]
          / "src" / "zuspec" / "fe" / "pss" / "share" / "sv" / "zsp_rt_pkg.sv")
    return rt if rt.exists() else None


def build_ir(*types, parent_comp_names=None):
    """Build an AstToIrContext from datatype objects."""
    ctx = AstToIrContext()
    for dt in types:
        ctx.add_type(dt.name, dt)
    if parent_comp_names:
        ctx.parent_comp_names.update(parent_comp_names)
    return ctx


def generate_sv_files(ir_ctx, output_dir, comp_type, root_action_type,
                      has_activity=True, extra_sv=None):
    """Run the full lowering pipeline and write multi-file SV output.

    Args:
        ir_ctx: AstToIrContext with registered types.
        output_dir: Directory to write generated files.
        comp_type: Top component SV class name.
        root_action_type: Root action SV class name.
        has_activity: True for compound (activity), False for atomic (body).
        extra_sv: Optional dict of filename -> SV text to write alongside.

    Returns:
        List of written file paths.
    """
    sv_nodes = pss_to_sv(ir_ctx)
    top = generate_top_module(
        comp_type=comp_type,
        root_action_type=root_action_type,
        has_activity=has_activity,
    )
    rt_path = _get_runtime_lib_path()
    files = emit_files(sv_nodes, output_dir,
                       runtime_lib_path=rt_path,
                       top_module_node=top)
    if extra_sv:
        out = Path(output_dir)
        for name, content in extra_sv.items():
            p = out / name
            p.write_text(content)
            files.append(p)
    return files


def run_sim(tmpdir, sim, sv_dir, top_module="zsp_test_top", plusargs=None):
    """Compile and simulate SV sources in sv_dir via DFM task graph.

    Args:
        tmpdir: pytest tmpdir (used for DFM rundir).
        sim: Simulator tag ("mti" or "vcs").
        sv_dir: Directory containing .sv files.
        top_module: Top-level module name.
        plusargs: Optional plusarg list.

    Returns:
        Tuple of (status, sim_log_text).
    """
    from dv_flow.mgr import TaskListenerLog, TaskSetRunner, PackageLoader
    from dv_flow.mgr.task_graph_builder import TaskGraphBuilder

    rundir = str(Path(tmpdir) / "rundir")
    errors = []

    def marker_listener(marker):
        from dv_flow.mgr.task_data import SeverityE
        if marker.severity == SeverityE.Error:
            errors.append(str(marker.msg))

    builder = TaskGraphBuilder(
        PackageLoader(marker_listeners=[marker_listener]).load_rgy(
            ["std", f"hdlsim.{sim}"]),
        rundir)

    runner = TaskSetRunner(rundir)
    runner.builder = builder

    fileset = builder.mkTaskNode(
        "std.FileSet",
        name="sv_files",
        type="systemVerilogSource",
        base=str(sv_dir),
        include="*.sv",
        needs=[])

    sim_img = builder.mkTaskNode(
        f"hdlsim.{sim}.SimImage",
        name="sim_img",
        top=[top_module],
        needs=[fileset])

    sim_run_kwargs = dict(name="sim_run", needs=[sim_img])
    if plusargs:
        sim_run_kwargs["plusargs"] = plusargs

    sim_run = builder.mkTaskNode(
        f"hdlsim.{sim}.SimRun", **sim_run_kwargs)

    runner.add_listener(TaskListenerLog().event)
    out = asyncio.run(runner.run(sim_run))

    sim_log = ""
    if out is not None and hasattr(out, "output") and out.output:
        for fs in out.output:
            if getattr(fs, "type", None) == "std.FileSet" and \
               getattr(fs, "filetype", None) == "simRunDir":
                log_path = os.path.join(fs.basedir, "sim.log")
                if os.path.isfile(log_path):
                    sim_log = open(log_path).read()
                break

    if errors and not sim_log:
        sim_log = "\n".join(errors)

    return runner.status, sim_log


def build_and_run(tmpdir, sim, ir_ctx, comp_type, root_action_type,
                  has_activity=True, extra_sv=None, plusargs=None):
    """Full pipeline: IR -> lowering -> SV files -> compile -> simulate.

    Returns:
        Tuple of (status, sim_log_text).
    """
    sv_dir = str(Path(tmpdir) / "sv_out")
    generate_sv_files(ir_ctx, sv_dir, comp_type, root_action_type,
                      has_activity=has_activity, extra_sv=extra_sv)
    return run_sim(tmpdir, sim, sv_dir, plusargs=plusargs)
