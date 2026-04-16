"""End-to-end tests: IR context -> pss_to_sv -> SV text.

Builds IR contexts manually and verifies the full lowering pipeline
produces correct SV output.
"""

import pytest
from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv_emit import SVEmitter

from zuspec.fe.pss.ast_to_ir import AstToIrContext
from zuspec.fe.pss.sv.pss_to_sv import pss_to_sv


@pytest.fixture
def emitter():
    return SVEmitter()


def _make_ctx(*types):
    """Build an AstToIrContext with the given types registered."""
    ctx = AstToIrContext()
    for dt in types:
        ctx.add_type(dt.name, dt)
    return ctx


class TestE2E:
    def test_enum_and_struct(self, emitter):
        enum_dt = ir.DataTypeEnum(name="cmd_e", items={"RD": 0, "WR": 1})
        struct_dt = ir.DataTypeStruct(
            name="Packet",
            super=None,
            fields=[
                ir.Field(name="cmd", datatype=enum_dt),
                ir.Field(name="addr", datatype=ir.DataTypeInt(bits=32, signed=False),
                         rand_kind="rand"),
            ],
        )
        ir_ctx = _make_ctx(enum_dt, struct_dt)
        sv_nodes = pss_to_sv(ir_ctx)
        text = emitter.emit_all(sv_nodes)

        # Enum should come before struct
        assert "typedef enum" in text
        assert "class Packet" in text
        enum_pos = text.index("typedef enum")
        class_pos = text.index("class Packet")
        assert enum_pos < class_pos

    def test_component_and_action(self, emitter):
        comp_dt = ir.DataTypeComponent(
            name="dma_c",
            super=None,
            fields=[],
        )
        action_dt = ir.DataTypeClass(
            name="dma_c::transfer",
            super=None,
            fields=[
                ir.Field(name="addr", datatype=ir.DataTypeInt(bits=32, signed=False),
                         rand_kind="rand"),
            ],
        )
        ir_ctx = _make_ctx(comp_dt, action_dt)
        ir_ctx.parent_comp_names["dma_c::transfer"] = "dma_c"
        sv_nodes = pss_to_sv(ir_ctx)
        text = emitter.emit_all(sv_nodes)

        assert "class dma_c extends zsp_component;" in text
        assert "class dma_c__transfer extends zsp_action;" in text
        assert "dma_c comp;" in text
        assert "rand bit [31:0] addr;" in text

    def test_forward_declarations_present(self, emitter):
        struct_dt = ir.DataTypeStruct(
            name="simple_s",
            super=None,
            fields=[],
        )
        ir_ctx = _make_ctx(struct_dt)
        sv_nodes = pss_to_sv(ir_ctx)
        text = emitter.emit_all(sv_nodes)

        assert "typedef class simple_s;" in text
        fwd_pos = text.index("typedef class simple_s;")
        cls_pos = text.index("class simple_s;")
        assert fwd_pos < cls_pos

    def test_import_interface_generated(self, emitter):
        comp_dt = ir.DataTypeComponent(
            name="ctrl_c",
            super=None,
            fields=[],
            functions=[
                ir.Function(
                    name="do_op",
                    args=ir.Arguments(args=[]),
                    body=[],
                    is_import=True,
                    is_async=True,
                    metadata={},
                ),
            ],
        )
        ir_ctx = _make_ctx(comp_dt)
        sv_nodes = pss_to_sv(ir_ctx)
        text = emitter.emit_all(sv_nodes)

        assert "virtual class ctrl_c_import_if;" in text
        assert "pure virtual task do_op" in text
        assert "class ctrl_c extends zsp_component;" in text

    def test_action_with_constraints_e2e(self, emitter):
        action_dt = ir.DataTypeClass(
            name="aligned_xfer",
            super=None,
            fields=[
                ir.Field(name="addr", datatype=ir.DataTypeInt(bits=32, signed=False),
                         rand_kind="rand"),
            ],
            functions=[
                ir.Function(
                    name="addr_align_c",
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
        ir_ctx = _make_ctx(action_dt)
        sv_nodes = pss_to_sv(ir_ctx)
        text = emitter.emit_all(sv_nodes)

        assert "rand bit [31:0] addr;" in text
        assert "constraint addr_align_c" in text
        assert "4096" in text


class TestE2EOrdering:
    def test_dependency_order(self, emitter):
        """Verify output ordering: enums, forward decls, structs, components, actions."""
        enum_dt = ir.DataTypeEnum(name="mode_e", items={"A": 0, "B": 1})
        struct_dt = ir.DataTypeStruct(
            name="payload_s",
            super=None,
            fields=[
                ir.Field(name="data", datatype=ir.DataTypeInt(bits=32, signed=False)),
            ],
        )
        comp_dt = ir.DataTypeComponent(
            name="top_c",
            super=None,
            fields=[],
        )
        action_dt = ir.DataTypeClass(
            name="top_c::xfer",
            super=None,
            fields=[
                ir.Field(name="addr", datatype=ir.DataTypeInt(bits=32, signed=False),
                         rand_kind="rand"),
            ],
        )
        ir_ctx = _make_ctx(enum_dt, struct_dt, comp_dt, action_dt)
        ir_ctx.parent_comp_names["top_c::xfer"] = "top_c"
        sv_nodes = pss_to_sv(ir_ctx)
        text = emitter.emit_all(sv_nodes)

        # Enum before struct
        assert text.index("typedef enum") < text.index("class payload_s")
        # Struct forward decl before struct def
        assert text.index("typedef class payload_s;") < text.index("class payload_s;")
        # Component before action
        assert text.index("class top_c extends zsp_component") < text.index("class top_c__xfer extends zsp_action")

    def test_no_duplicate_types(self, emitter):
        """Same type registered under multiple names should not produce duplicates."""
        struct_dt = ir.DataTypeStruct(
            name="unique_s",
            super=None,
            fields=[],
        )
        ir_ctx = AstToIrContext()
        ir_ctx.add_type("unique_s", struct_dt)
        ir_ctx.add_type("alias_unique_s", struct_dt)  # same object, different key
        sv_nodes = pss_to_sv(ir_ctx)
        text = emitter.emit_all(sv_nodes)

        # The class definition should appear only once (forward decl is separate)
        assert text.count("\nclass unique_s") == 1 or text.count("class unique_s;\nendclass") == 1


class TestE2EComponentImport:
    def test_import_interface_before_component(self, emitter):
        """Import interface class should appear before the component that uses it."""
        comp_dt = ir.DataTypeComponent(
            name="hw_c",
            super=None,
            fields=[],
            functions=[
                ir.Function(
                    name="read_reg",
                    args=ir.Arguments(args=[ir.Arg(arg="addr")]),
                    body=[],
                    is_import=True,
                    is_async=False,
                    returns=ir.DataTypeInt(bits=32, signed=False),
                    metadata={},
                ),
            ],
        )
        ir_ctx = _make_ctx(comp_dt)
        sv_nodes = pss_to_sv(ir_ctx)
        text = emitter.emit_all(sv_nodes)

        assert "virtual class hw_c_import_if;" in text
        assert "class hw_c extends zsp_component;" in text
        assert "hw_c_import_if import_if;" in text
        # Import interface should come before component
        assert text.index("hw_c_import_if;") < text.index("class hw_c extends")


class TestE2EResourceTypes:
    def test_resource_type_lowering(self, emitter):
        # For Phase 3, resource types are stored as DataTypeStruct with a
        # flow-object category. The pss_to_sv pass treats them as structs.
        # Detection of resource/buffer/stream/state is done at a higher
        # level or by metadata; for now they lower as plain structs.
        res_dt = ir.DataTypeStruct(
            name="channel_r",
            super=None,
            fields=[
                ir.Field(name="id", datatype=ir.DataTypeInt(bits=8, signed=False)),
            ],
        )
        ir_ctx = _make_ctx(res_dt)
        sv_nodes = pss_to_sv(ir_ctx)
        text = emitter.emit_all(sv_nodes)
        assert "class channel_r" in text
        assert "bit [7:0] id;" in text
