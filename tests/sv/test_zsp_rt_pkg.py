"""Simulation-based tests for the zsp_rt_pkg SV runtime library.

Uses DV Flow Manager (pytest_dfm) to compile and simulate the
standalone testbench with available simulators (VCS, Questa).
"""

import asyncio
import os
import shutil

import pytest
from dv_flow.mgr import PackageLoader, TaskGraphBuilder, TaskListenerLog, TaskSetRunner

# Path to the SV runtime package directory (for +incdir)
_RT_PKG_DIR = os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    os.pardir, os.pardir,
    "src", "zuspec", "fe", "pss", "share", "sv",
))
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _get_available_sims():
    """Return list of simulator short-names that are on PATH."""
    sims = []
    for exe, short in {"vcs": "vcs", "vsim": "mti"}.items():
        if shutil.which(exe) is not None:
            sims.append(short)
    return sims


@pytest.mark.parametrize("sim", _get_available_sims())
def test_zsp_rt_pkg_sim(tmpdir, sim):
    """Compile and simulate the zsp_rt_pkg testbench.

    Verifies that every check inside test_zsp_rt_pkg.sv passes.
    """
    runner = TaskSetRunner(os.path.join(str(tmpdir), "rundir"))

    def marker_listener(marker):
        from dv_flow.mgr.task_data import SeverityE
        if marker.severity == SeverityE.Error:
            raise Exception(f"Marker error: {marker.msg}")

    builder = TaskGraphBuilder(
        PackageLoader(
            marker_listeners=[marker_listener],
        ).load_rgy(["std", f"hdlsim.{sim}"]),
        os.path.join(str(tmpdir), "rundir"),
    )
    runner.builder = builder

    # Testbench FileSet with incdir pointing at the runtime package
    sv_src = builder.mkTaskNode(
        "std.FileSet",
        name="sv_src",
        type="systemVerilogSource",
        base=_DATA_DIR,
        include="test_zsp_rt_pkg.sv",
        incdirs=[_RT_PKG_DIR],
        needs=[],
    )

    # Build simulation image
    sim_img = builder.mkTaskNode(
        f"hdlsim.{sim}.SimImage",
        name="sim_img",
        top=["test_zsp_rt_top"],
        needs=[sv_src],
    )

    # Run simulation
    sim_run = builder.mkTaskNode(
        f"hdlsim.{sim}.SimRun",
        name="sim_run",
        needs=[sim_img],
    )

    runner.add_listener(TaskListenerLog().event)
    out = asyncio.run(runner.run(sim_run))

    assert runner.status == 0, "DFM runner reported failure"

    # Locate simulation log
    rundir_fs = None
    for fs in out.output:
        if fs.type == "std.FileSet" and fs.filetype == "simRunDir":
            rundir_fs = fs

    assert rundir_fs is not None, "No simRunDir fileset in output"
    sim_log_path = os.path.join(rundir_fs.basedir, "sim.log")
    assert os.path.isfile(sim_log_path), f"sim.log not found at {sim_log_path}"

    with open(sim_log_path) as f:
        sim_log = f.read()

    # Verify all checks passed
    assert "ALL TESTS PASSED" in sim_log, (
        f"Testbench did not report ALL TESTS PASSED.\n"
        f"--- sim.log tail ---\n{sim_log[-2000:]}"
    )
    assert "FAIL:" not in sim_log, "One or more checks reported FAIL"
