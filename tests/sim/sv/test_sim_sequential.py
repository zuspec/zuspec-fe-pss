"""Simulation tests: full pipeline IR -> lowering -> SV -> compile -> simulate.

Each test constructs IR types programmatically (simulating what the PSS
parser would produce), runs them through pss_to_sv() + emit_files() +
generate_top_module(), then compiles and simulates with DFM across
available commercial simulators (Questa, VCS).

The body task in the generated action is a placeholder. To verify
simulation behavior we inject a small hand-written SV snippet that
overrides or extends the generated top module with assertion checks.
"""
import pytest
from zuspec.dataclasses import ir

from .conftest import AVAILABLE_SIMS, build_ir, build_and_run


# -----------------------------------------------------------------------
# Helpers for building IR types
# -----------------------------------------------------------------------

def _make_action(name, fields=None, constraints=None, comp_name=None):
    """Build a DataTypeClass (action) with optional fields and constraints."""
    flds = []
    if fields:
        for f in fields:
            flds.append(ir.Field(
                name=f["name"],
                datatype=ir.DataTypeInt(bits=f.get("bits", 32), signed=f.get("signed", False)),
                rand_kind=f.get("rand_kind", "rand"),
            ))
    funcs = []
    if constraints:
        for cname, exprs in constraints.items():
            funcs.append(ir.Function(
                name=cname,
                body=[ir.StmtExpr(expr=e) for e in exprs],
                metadata={"_is_constraint": True},
            ))
    # Add body placeholder
    funcs.append(ir.Function(name="body", body=[], metadata={}))
    return ir.DataTypeClass(name=name, super=None, fields=flds, functions=funcs)


def _make_component(name, fields=None):
    """Build a DataTypeComponent."""
    flds = []
    if fields:
        for f in fields:
            flds.append(ir.Field(name=f["name"], datatype=f["datatype"]))
    return ir.DataTypeComponent(name=name, super=None, fields=flds)


# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------

@pytest.mark.parametrize("sim", AVAILABLE_SIMS)
def test_simple_action_randomize(tmpdir, sim):
    """Single action with rand field + constraint: verify constraint holds."""
    comp = _make_component("top_c")
    action = _make_action("top_c::hello", fields=[
        {"name": "addr", "bits": 32},
    ], constraints={
        "align_c": [ir.ExprCompare(
            left=ir.ExprSubscript(
                value=ir.ExprRefLocal(name="addr"),
                slice=ir.ExprSlice(
                    lower=ir.ExprConstant(value=0),
                    upper=ir.ExprConstant(value=1),
                ),
            ),
            ops=[ir.CmpOp.Eq],
            comparators=[ir.ExprConstant(value=0)],
        )],
    })
    ir_ctx = build_ir(comp, action, parent_comp_names={"top_c::hello": "top_c"})

    # Override the top module to add constraint verification after randomize
    extra_top = """\
// Verification wrapper: included alongside generated files
module zsp_test_top;
    import zsp_rt_pkg::*;
    import zsp_gen_pkg::*;

    initial begin
        automatic top_c comp_inst = new("top", null);
        automatic top_c__hello act = new();
        act.comp = comp_inst;
        act.pre_solve();
        if (!act.randomize())
            $fatal(1, "randomize failed");
        act.post_solve();

        if (act.addr[1:0] != 2'b0)
            $fatal(1, "FAIL: addr not aligned: 0x%08h", act.addr);

        act.body();
        $display("TEST_PASSED");
        $finish;
    end
endmodule
"""

    # Generate SV from lowering pipeline but replace top with our checker
    from zuspec.fe.pss.sv.pss_to_sv import pss_to_sv
    from zuspec.fe.pss.sv.emit_files import emit_files
    from pathlib import Path

    sv_dir = str(Path(str(tmpdir)) / "sv_out")
    sv_nodes = pss_to_sv(ir_ctx)
    rt_path = Path(__file__).resolve().parents[3] / "src" / "zuspec" / "fe" / "pss" / "share" / "sv" / "zsp_rt_pkg.sv"
    emit_files(sv_nodes, sv_dir, runtime_lib_path=rt_path if rt_path.exists() else None)

    # Write our custom top (overrides any generated one)
    (Path(sv_dir) / "zsp_top.sv").write_text(extra_top)

    from .conftest import run_sim
    status, log = run_sim(tmpdir, sim, sv_dir)
    assert status == 0, f"Sim failed (status={status}):\n{log}"
    assert "TEST_PASSED" in log, f"TEST_PASSED not in log:\n{log}"


@pytest.mark.parametrize("sim", AVAILABLE_SIMS)
def test_two_actions_sequential(tmpdir, sim):
    """Two actions executed sequentially, verify execution order."""
    comp = _make_component("top_c")
    act_a = _make_action("top_c::act_a", fields=[{"name": "val", "bits": 8}])
    act_b = _make_action("top_c::act_b", fields=[{"name": "val", "bits": 8}],
                         constraints={
                             "small_c": [ir.ExprCompare(
                                 left=ir.ExprRefLocal(name="val"),
                                 ops=[ir.CmpOp.Lt],
                                 comparators=[ir.ExprConstant(value=10)],
                             )]
                         })
    ir_ctx = build_ir(comp, act_a, act_b, parent_comp_names={
        "top_c::act_a": "top_c", "top_c::act_b": "top_c",
    })

    extra_top = """\
module zsp_test_top;
    import zsp_rt_pkg::*;
    import zsp_gen_pkg::*;

    initial begin
        automatic top_c comp_inst = new("top", null);

        begin
            automatic top_c__act_a a = new();
            a.comp = comp_inst;
            if (!a.randomize()) $fatal(1, "act_a randomize failed");
            $display("[A] val=%0d", a.val);
        end

        begin
            automatic top_c__act_b b = new();
            b.comp = comp_inst;
            if (!b.randomize()) $fatal(1, "act_b randomize failed");
            if (b.val >= 10)
                $fatal(1, "FAIL: act_b val=%0d >= 10", b.val);
            $display("[B] val=%0d", b.val);
        end

        $display("TEST_PASSED");
        $finish;
    end
endmodule
"""

    from zuspec.fe.pss.sv.pss_to_sv import pss_to_sv
    from zuspec.fe.pss.sv.emit_files import emit_files
    from pathlib import Path

    sv_dir = str(Path(str(tmpdir)) / "sv_out")
    sv_nodes = pss_to_sv(ir_ctx)
    rt_path = Path(__file__).resolve().parents[3] / "src" / "zuspec" / "fe" / "pss" / "share" / "sv" / "zsp_rt_pkg.sv"
    emit_files(sv_nodes, sv_dir, runtime_lib_path=rt_path if rt_path.exists() else None)
    (Path(sv_dir) / "zsp_top.sv").write_text(extra_top)

    from .conftest import run_sim
    status, log = run_sim(tmpdir, sim, sv_dir)
    assert status == 0, f"Sim failed:\n{log}"
    assert "TEST_PASSED" in log, f"TEST_PASSED not in log:\n{log}"
    assert log.index("[A]") < log.index("[B]"), "A should execute before B"


@pytest.mark.parametrize("sim", AVAILABLE_SIMS)
def test_component_hierarchy(tmpdir, sim):
    """Component tree: verify get_full_name() works via simulation."""
    parent_comp = _make_component("top_c")
    child_comp = _make_component("dma_c")
    action = _make_action("dma_c::xfer", fields=[{"name": "addr", "bits": 32}])

    ir_ctx = build_ir(parent_comp, child_comp, action,
                      parent_comp_names={"dma_c::xfer": "dma_c"})

    extra_top = """\
module zsp_test_top;
    import zsp_rt_pkg::*;
    import zsp_gen_pkg::*;

    initial begin
        automatic top_c root_comp = new("top", null);
        automatic dma_c child_comp = new("dma", root_comp);
        automatic dma_c__xfer act = new();

        act.comp = child_comp;
        if (!act.randomize()) $fatal(1, "randomize failed");

        if (child_comp.get_full_name() != "top.dma")
            $fatal(1, "FAIL: full_name=%s", child_comp.get_full_name());

        $display("[COMP] %s", child_comp.get_full_name());
        $display("TEST_PASSED");
        $finish;
    end
endmodule
"""

    from zuspec.fe.pss.sv.pss_to_sv import pss_to_sv
    from zuspec.fe.pss.sv.emit_files import emit_files
    from pathlib import Path

    sv_dir = str(Path(str(tmpdir)) / "sv_out")
    sv_nodes = pss_to_sv(ir_ctx)
    rt_path = Path(__file__).resolve().parents[3] / "src" / "zuspec" / "fe" / "pss" / "share" / "sv" / "zsp_rt_pkg.sv"
    emit_files(sv_nodes, sv_dir, runtime_lib_path=rt_path if rt_path.exists() else None)
    (Path(sv_dir) / "zsp_top.sv").write_text(extra_top)

    from .conftest import run_sim
    status, log = run_sim(tmpdir, sim, sv_dir)
    assert status == 0, f"Sim failed:\n{log}"
    assert "TEST_PASSED" in log, f"TEST_PASSED not in log:\n{log}"
    assert "top.dma" in log


@pytest.mark.parametrize("sim", AVAILABLE_SIMS)
def test_parallel_fork_join(tmpdir, sim):
    """Two actions run in parallel via fork/join."""
    comp = _make_component("top_c")
    action = _make_action("top_c::par_act", fields=[{"name": "id", "bits": 8}])
    ir_ctx = build_ir(comp, action, parent_comp_names={"top_c::par_act": "top_c"})

    extra_top = """\
module zsp_test_top;
    import zsp_rt_pkg::*;
    import zsp_gen_pkg::*;

    initial begin
        automatic top_c comp_inst = new("top", null);

        fork
            begin
                automatic top_c__par_act a0 = new();
                a0.comp = comp_inst;
                if (!a0.randomize()) $fatal(1, "a0 randomize failed");
                $display("[A] start t=%0t", $time);
                #10;
                $display("[A] end t=%0t", $time);
            end
            begin
                automatic top_c__par_act a1 = new();
                a1.comp = comp_inst;
                if (!a1.randomize()) $fatal(1, "a1 randomize failed");
                $display("[B] start t=%0t", $time);
                #10;
                $display("[B] end t=%0t", $time);
            end
        join

        $display("TEST_PASSED");
        $finish;
    end
endmodule
"""

    from zuspec.fe.pss.sv.pss_to_sv import pss_to_sv
    from zuspec.fe.pss.sv.emit_files import emit_files
    from pathlib import Path

    sv_dir = str(Path(str(tmpdir)) / "sv_out")
    sv_nodes = pss_to_sv(ir_ctx)
    rt_path = Path(__file__).resolve().parents[3] / "src" / "zuspec" / "fe" / "pss" / "share" / "sv" / "zsp_rt_pkg.sv"
    emit_files(sv_nodes, sv_dir, runtime_lib_path=rt_path if rt_path.exists() else None)
    (Path(sv_dir) / "zsp_top.sv").write_text(extra_top)

    from .conftest import run_sim
    status, log = run_sim(tmpdir, sim, sv_dir)
    assert status == 0, f"Sim failed:\n{log}"
    assert "TEST_PASSED" in log, f"TEST_PASSED not in log:\n{log}"
    assert "[A] start" in log
    assert "[B] start" in log


@pytest.mark.parametrize("sim", AVAILABLE_SIMS)
def test_resource_pool(tmpdir, sim):
    """Resource pool lock/unlock simulation with generated resource class."""
    res_dt = ir.DataTypeStruct(
        name="channel_r", super=None,
        fields=[ir.Field(name="prio", datatype=ir.DataTypeInt(bits=4, signed=False),
                         rand_kind="rand")],
    )
    comp = _make_component("top_c")
    ir_ctx = build_ir(res_dt, comp)

    extra_top = """\
module zsp_test_top;
    import zsp_rt_pkg::*;
    import zsp_gen_pkg::*;

    initial begin
        automatic zsp_resource_pool #(zsp_resource) pool = new(4);

        if (pool.pool_size() != 4)
            $fatal(1, "FAIL: pool_size=%0d", pool.pool_size());

        pool.force_lock(0);
        if (!pool.lock_held[0])
            $fatal(1, "FAIL: resource 0 not locked");

        pool.unlock(0);
        if (pool.lock_held[0])
            $fatal(1, "FAIL: resource 0 still locked");

        if (pool.instances[2].instance_id != 2)
            $fatal(1, "FAIL: instance_id=%0d", pool.instances[2].instance_id);

        $display("TEST_PASSED");
        $finish;
    end
endmodule
"""

    from zuspec.fe.pss.sv.pss_to_sv import pss_to_sv
    from zuspec.fe.pss.sv.emit_files import emit_files
    from pathlib import Path

    sv_dir = str(Path(str(tmpdir)) / "sv_out")
    sv_nodes = pss_to_sv(ir_ctx)
    rt_path = Path(__file__).resolve().parents[3] / "src" / "zuspec" / "fe" / "pss" / "share" / "sv" / "zsp_rt_pkg.sv"
    emit_files(sv_nodes, sv_dir, runtime_lib_path=rt_path if rt_path.exists() else None)
    (Path(sv_dir) / "zsp_top.sv").write_text(extra_top)

    from .conftest import run_sim
    status, log = run_sim(tmpdir, sim, sv_dir)
    assert status == 0, f"Sim failed:\n{log}"
    assert "TEST_PASSED" in log, f"TEST_PASSED not in log:\n{log}"


@pytest.mark.parametrize("sim", AVAILABLE_SIMS)
def test_stream_channel(tmpdir, sim):
    """Stream channel (mailbox) with concurrent producer/consumer."""
    comp = _make_component("top_c")
    ir_ctx = build_ir(comp)

    extra_top = """\
module zsp_test_top;
    import zsp_rt_pkg::*;
    import zsp_gen_pkg::*;

    initial begin
        automatic zsp_stream_channel #(zsp_stream) ch = new();
        automatic zsp_stream received;

        fork
            begin
                automatic zsp_stream frame = new();
                $display("[PRODUCER] putting frame");
                ch.put(frame);
            end
            begin
                ch.get(received);
                $display("[CONSUMER] got frame");
                if (received == null)
                    $fatal(1, "FAIL: received null");
            end
        join

        $display("TEST_PASSED");
        $finish;
    end
endmodule
"""

    from zuspec.fe.pss.sv.pss_to_sv import pss_to_sv
    from zuspec.fe.pss.sv.emit_files import emit_files
    from pathlib import Path

    sv_dir = str(Path(str(tmpdir)) / "sv_out")
    sv_nodes = pss_to_sv(ir_ctx)
    rt_path = Path(__file__).resolve().parents[3] / "src" / "zuspec" / "fe" / "pss" / "share" / "sv" / "zsp_rt_pkg.sv"
    emit_files(sv_nodes, sv_dir, runtime_lib_path=rt_path if rt_path.exists() else None)
    (Path(sv_dir) / "zsp_top.sv").write_text(extra_top)

    from .conftest import run_sim
    status, log = run_sim(tmpdir, sim, sv_dir)
    assert status == 0, f"Sim failed:\n{log}"
    assert "TEST_PASSED" in log, f"TEST_PASSED not in log:\n{log}"
    assert "[PRODUCER]" in log
    assert "[CONSUMER]" in log


@pytest.mark.parametrize("sim", AVAILABLE_SIMS)
def test_generated_top_module(tmpdir, sim):
    """Use the fully generated top module (no hand-written override)."""
    comp = _make_component("top_c")
    action = _make_action("top_c::hello", fields=[
        {"name": "val", "bits": 8},
    ])
    ir_ctx = build_ir(comp, action, parent_comp_names={"top_c::hello": "top_c"})

    status, log = build_and_run(tmpdir, sim, ir_ctx,
                                comp_type="top_c",
                                root_action_type="top_c__hello",
                                has_activity=False)
    assert status == 0, f"Sim failed:\n{log}"
    assert "Scenario complete" in log, f"Scenario complete not in log:\n{log}"
