"""Tests for PSS action lowering to SV IR nodes."""

import pytest
from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv_emit import SVEmitter

from zuspec.fe.pss.sv.context import LoweringContext
from zuspec.fe.pss.sv.lower_actions import lower_action


@pytest.fixture
def ctx():
    return LoweringContext()


@pytest.fixture
def emitter():
    return SVEmitter()


class TestLowerAction:
    def test_simple_action(self, ctx, emitter):
        act = ir.DataTypeClass(
            name="my_action",
            super=None,
            fields=[],
        )
        sv = lower_action(ctx, act)
        text = emitter.emit_one(sv)
        assert "class my_action extends zsp_action;" in text
        assert "endclass" in text

    def test_action_with_rand_fields(self, ctx, emitter):
        act = ir.DataTypeClass(
            name="transfer",
            super=None,
            fields=[
                ir.Field(name="addr", datatype=ir.DataTypeInt(bits=32, signed=False),
                         rand_kind="rand"),
                ir.Field(name="length", datatype=ir.DataTypeInt(bits=16, signed=False),
                         rand_kind="rand"),
            ],
        )
        sv = lower_action(ctx, act)
        text = emitter.emit_one(sv)
        assert "rand bit [31:0] addr;" in text
        assert "rand bit [15:0] length;" in text

    def test_action_with_comp_ref(self, ctx, emitter):
        act = ir.DataTypeClass(
            name="dma_c::transfer",
            super=None,
            fields=[],
        )
        sv = lower_action(ctx, act, comp_type_name="dma_c")
        text = emitter.emit_one(sv)
        assert "dma_c comp;" in text

    def test_action_with_constraints(self, ctx, emitter):
        act = ir.DataTypeClass(
            name="aligned_xfer",
            super=None,
            fields=[
                ir.Field(name="addr", datatype=ir.DataTypeInt(bits=32, signed=False),
                         rand_kind="rand"),
            ],
            functions=[
                ir.Function(
                    name="addr_c",
                    body=[
            ir.StmtExpr(expr=ir.ExprCompare(
                            left=ir.ExprRefLocal(name="addr"),
                            ops=[ir.CmpOp.GtE],
                            comparators=[ir.ExprConstant(value=4096)],
                        )),
                    ],
                    metadata={"_is_constraint": True},
                ),
            ],
        )
        sv = lower_action(ctx, act)
        text = emitter.emit_one(sv)
        assert "constraint addr_c" in text
        assert "addr" in text

    def test_action_with_body(self, ctx, emitter):
        act = ir.DataTypeClass(
            name="body_action",
            super=None,
            fields=[],
            functions=[
                ir.Function(name="body", body=[], is_async=True, metadata={}),
            ],
        )
        sv = lower_action(ctx, act)
        text = emitter.emit_one(sv)
        assert "virtual task body();" in text

    def test_action_with_pre_post_solve(self, ctx, emitter):
        act = ir.DataTypeClass(
            name="solve_action",
            super=None,
            fields=[],
            functions=[
                ir.Function(name="pre_solve", body=[], metadata={}),
                ir.Function(name="post_solve", body=[], metadata={}),
            ],
        )
        sv = lower_action(ctx, act)
        text = emitter.emit_one(sv)
        assert "virtual function void pre_solve();" in text
        assert "virtual function void post_solve();" in text

    def test_action_name_mangling(self, ctx, emitter):
        act = ir.DataTypeClass(
            name="my_comp::my_action",
            super=None,
            fields=[],
        )
        sv = lower_action(ctx, act)
        text = emitter.emit_one(sv)
        assert "class my_comp__my_action" in text


class TestActionInheritance:
    def test_action_extending_base(self, ctx, emitter):
        act = ir.DataTypeClass(
            name="ext_action",
            super=ir.DataTypeRef(ref_name="base_action"),
            fields=[
                ir.Field(name="extra", datatype=ir.DataTypeInt(bits=8, signed=False),
                         rand_kind="rand"),
            ],
        )
        sv = lower_action(ctx, act)
        text = emitter.emit_one(sv)
        assert "class ext_action extends base_action;" in text
        assert "rand bit [7:0] extra;" in text

    def test_action_with_randc(self, ctx, emitter):
        act = ir.DataTypeClass(
            name="randc_action",
            super=None,
            fields=[
                ir.Field(name="id", datatype=ir.DataTypeInt(bits=4, signed=False),
                         rand_kind="randc"),
            ],
        )
        sv = lower_action(ctx, act)
        text = emitter.emit_one(sv)
        assert "randc bit [3:0] id;" in text

    def test_action_with_multiple_constraints(self, ctx, emitter):
        act = ir.DataTypeClass(
            name="multi_c_act",
            super=None,
            fields=[
                ir.Field(name="addr", datatype=ir.DataTypeInt(bits=32, signed=False),
                         rand_kind="rand"),
                ir.Field(name="size", datatype=ir.DataTypeInt(bits=16, signed=False),
                         rand_kind="rand"),
            ],
            functions=[
                ir.Function(
                    name="addr_c",
                    body=[
                        ir.StmtExpr(expr=ir.ExprCompare(
                            left=ir.ExprRefLocal(name="addr"),
                            ops=[ir.CmpOp.GtE],
                            comparators=[ir.ExprConstant(value=0x1000)],
                        )),
                    ],
                    metadata={"_is_constraint": True},
                ),
                ir.Function(
                    name="size_c",
                    body=[
                        ir.StmtExpr(expr=ir.ExprCompare(
                            left=ir.ExprRefLocal(name="size"),
                            ops=[ir.CmpOp.LtE],
                            comparators=[ir.ExprConstant(value=4096)],
                        )),
                    ],
                    metadata={"_is_constraint": True},
                ),
            ],
        )
        sv = lower_action(ctx, act)
        text = emitter.emit_one(sv)
        assert "constraint addr_c" in text
        assert "constraint size_c" in text

    def test_action_with_non_rand_field(self, ctx, emitter):
        act = ir.DataTypeClass(
            name="mixed_action",
            super=None,
            fields=[
                ir.Field(name="rand_f", datatype=ir.DataTypeInt(bits=8, signed=False),
                         rand_kind="rand"),
                ir.Field(name="nonrand_f", datatype=ir.DataTypeInt(bits=8, signed=False)),
            ],
        )
        sv = lower_action(ctx, act)
        text = emitter.emit_one(sv)
        assert "rand bit [7:0] rand_f;" in text
        assert "bit [7:0] nonrand_f;" in text
        # nonrand_f should NOT have rand prefix
        lines = text.split('\n')
        for line in lines:
            if "nonrand_f" in line:
                assert "rand " not in line or "nonrand" in line.split("rand ")[0]
