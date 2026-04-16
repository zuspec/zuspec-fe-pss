"""End-to-end test: parallel DMA transfer (design doc S14 worked example).

Builds an IR model matching the DMA example from the design doc and
verifies the generated SV structure.
"""

import os
import tempfile
import shutil

import pytest
from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv_emit import SVEmitter

from zuspec.fe.pss.ast_to_ir import AstToIrContext
from zuspec.fe.pss.sv.pss_to_sv import pss_to_sv
from zuspec.fe.pss.sv.emit_files import emit_files
from zuspec.fe.pss.sv.lower_top import generate_top_module
from zuspec.fe.pss.sv.lower_activities import lower_activity
from zuspec.fe.pss.sv.lower_resources import ResourceClaim, emit_resource_acquire, emit_resource_release
from zuspec.fe.pss.sv.lower_head_solve import HeadAction, emit_head_action_solve
from zuspec.fe.pss.sv.context import LoweringContext


@pytest.fixture
def emitter():
    return SVEmitter()


@pytest.fixture
def ctx():
    return LoweringContext()


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="zsp_e2e_dma_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _build_dma_model():
    """Build an IR matching the design doc S14 DMA example."""
    # Resource type: channel_s
    channel_dt = ir.DataTypeStruct(
        name="channel_s",
        super=None,
        fields=[
            ir.Field(name="priority", datatype=ir.DataTypeInt(bits=4, signed=False),
                     rand_kind="rand"),
        ],
    )

    # Component: dma_c
    dma_comp = ir.DataTypeComponent(
        name="dma_c",
        super=None,
        fields=[],
        functions=[
            ir.Function(
                name="do_transfer",
                args=ir.Arguments(args=[
                    ir.Arg(arg="src"),
                    ir.Arg(arg="len"),
                    ir.Arg(arg="ch"),
                ]),
                body=[],
                is_import=True,
                is_async=True,
                metadata={},
            ),
        ],
    )

    # Action: dma_c::transfer
    transfer_action = ir.DataTypeClass(
        name="dma_c::transfer",
        super=None,
        fields=[
            ir.Field(name="src_addr", datatype=ir.DataTypeInt(bits=32, signed=False),
                     rand_kind="rand"),
            ir.Field(name="dst_addr", datatype=ir.DataTypeInt(bits=32, signed=False),
                     rand_kind="rand"),
            ir.Field(name="length", datatype=ir.DataTypeInt(bits=16, signed=False),
                     rand_kind="rand"),
        ],
        functions=[
            ir.Function(
                name="length_c",
                body=[
                    ir.StmtExpr(expr=ir.ExprIn(
                        value=ir.ExprRefLocal(name="length"),
                        container=ir.ExprRangeList(ranges=[
                            ir.ExprRange(lower=ir.ExprConstant(value=1),
                                         upper=ir.ExprConstant(value=4096)),
                        ]),
                    )),
                ],
                metadata={"_is_constraint": True},
            ),
        ],
    )

    # Component: pss_top
    pss_top = ir.DataTypeComponent(
        name="pss_top",
        super=None,
        fields=[
            ir.Field(name="dma", datatype=ir.DataTypeRef(ref_name="dma_c")),
        ],
    )

    # Action: pss_top::par_xfer (compound with parallel activity)
    par_xfer = ir.DataTypeClass(
        name="pss_top::par_xfer",
        super=None,
        fields=[],
        activity_ir=ir.ActivitySequenceBlock(stmts=[
            ir.ActivityParallel(stmts=[
                ir.ActivityAnonTraversal(action_type="dma_c::transfer"),
                ir.ActivityAnonTraversal(action_type="dma_c::transfer"),
            ]),
        ]),
    )

    ctx = AstToIrContext()
    ctx.add_type("channel_s", channel_dt)
    ctx.add_type("dma_c", dma_comp)
    ctx.add_type("dma_c::transfer", transfer_action)
    ctx.add_type("pss_top", pss_top)
    ctx.add_type("pss_top::par_xfer", par_xfer)
    ctx.parent_comp_names["dma_c::transfer"] = "dma_c"
    ctx.parent_comp_names["pss_top::par_xfer"] = "pss_top"
    return ctx


class TestParallelDmaE2E:
    def test_generates_sv_nodes(self, emitter):
        """Full PSS -> SV IR -> text pipeline produces expected structure."""
        ir_ctx = _build_dma_model()
        sv_nodes = pss_to_sv(ir_ctx)
        text = emitter.emit_all(sv_nodes)

        # Resource type
        assert "class channel_s" in text

        # Component with import interface
        assert "virtual class dma_c_import_if;" in text
        assert "class dma_c extends zsp_component;" in text

        # Action with rand fields and constraints
        assert "class dma_c__transfer extends zsp_action;" in text
        assert "rand bit [31:0] src_addr;" in text
        assert "rand bit [15:0] length;" in text
        assert "constraint length_c" in text

        # Top component
        assert "class pss_top extends zsp_component;" in text

        # Compound action
        assert "class pss_top__par_xfer extends zsp_action;" in text

    def test_multi_file_output(self, tmp_dir, emitter):
        """Multi-file output should produce all expected files."""
        ir_ctx = _build_dma_model()
        sv_nodes = pss_to_sv(ir_ctx)
        top = generate_top_module(
            comp_type="pss_top",
            root_action_type="pss_top__par_xfer",
        )
        files = emit_files(sv_nodes, tmp_dir, top_module_node=top)
        filenames = [os.path.basename(str(f)) for f in files]

        assert "zsp_gen_pkg.sv" in filenames     # all generated classes
        assert "zsp_top.sv" in filenames         # test harness
        assert "zsp_filelist.f" in filenames

    def test_top_module_structure(self):
        """Verify the test harness references the right types."""
        top = generate_top_module(
            comp_type="pss_top",
            root_action_type="pss_top__par_xfer",
            import_if_type="dma_c_import_if",
            import_if_driver="my_dma_driver",
        )
        text = "\n".join(top.body_lines)
        assert "automatic pss_top top;" in text
        assert 'top = new("top"' in text
        assert "pss_top__par_xfer root = new();" in text
        assert "automatic my_dma_driver _drv;" in text
        assert "root.activity();" in text

    def test_filelist_has_correct_order(self, tmp_dir):
        """File list should compile in dependency order."""
        ir_ctx = _build_dma_model()
        sv_nodes = pss_to_sv(ir_ctx)
        top = generate_top_module(
            comp_type="pss_top",
            root_action_type="pss_top__par_xfer",
        )
        emit_files(sv_nodes, tmp_dir, top_module_node=top)
        filelist = open(os.path.join(tmp_dir, "zsp_filelist.f")).read()
        lines = [l.strip() for l in filelist.strip().split("\n") if l.strip()]

        # gen_pkg before top
        for a, b in [
            ("zsp_gen_pkg.sv", "zsp_top.sv"),
        ]:
            if a in lines and b in lines:
                assert lines.index(a) < lines.index(b), f"{a} should come before {b}"


class TestParallelResourcePatterns:
    def test_head_action_solve(self):
        """Verify head-action coordinated solve for two branches."""
        heads = [
            HeadAction(branch_index=0, action_var="act0", action_type="transfer",
                       claims=[ResourceClaim(
                           field_name="chan", pool_expr="comp.pool",
                           id_field="chan_id", claim_kind="lock", is_head=True,
                       )]),
            HeadAction(branch_index=1, action_var="act1", action_type="transfer",
                       claims=[ResourceClaim(
                           field_name="chan", pool_expr="comp.pool",
                           id_field="chan_id", claim_kind="lock", is_head=True,
                       )]),
        ]
        lines = emit_head_action_solve(heads, {"comp.pool": 2})
        text = "\n".join(lines)

        # Should use shuffle-based (pool_size=2 >= n_branches=2, n<=8)
        assert "_pool_idx" in text or "_rid_" in text
        assert "act0.chan_id" in text
        assert "act1.chan_id" in text

    def test_parallel_activity_lowering(self, ctx):
        """Lower a parallel block with two anonymous traversals."""
        activity = ir.ActivitySequenceBlock(stmts=[
            ir.ActivityParallel(stmts=[
                ir.ActivityAnonTraversal(action_type="dma_c::transfer"),
                ir.ActivityAnonTraversal(action_type="dma_c::transfer"),
            ]),
        ])
        lines = lower_activity(ctx, activity, "comp")
        text = "\n".join(lines)

        assert "fork" in text
        assert "join" in text
        assert "dma_c__transfer" in text
        assert "randomize()" in text
