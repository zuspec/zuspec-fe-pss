"""Tests for PSS component lowering to SV IR nodes."""

import pytest
from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv_emit import SVEmitter

from zuspec.fe.pss.sv.context import LoweringContext
from zuspec.fe.pss.sv.lower_components import lower_component


@pytest.fixture
def ctx():
    return LoweringContext()


@pytest.fixture
def emitter():
    return SVEmitter()


class TestLowerComponent:
    def test_simple_component(self, ctx, emitter):
        comp = ir.DataTypeComponent(
            name="my_comp",
            super=None,
            fields=[],
        )
        sv = lower_component(ctx, comp)
        text = emitter.emit_one(sv)
        assert "class my_comp extends zsp_component;" in text
        assert "function new" in text
        assert "super.new(name, parent);" in text
        assert "endclass" in text

    def test_component_with_fields(self, ctx, emitter):
        comp = ir.DataTypeComponent(
            name="dma_c",
            super=None,
            fields=[
                ir.Field(name="chan_count", datatype=ir.DataTypeInt(bits=32, signed=False)),
            ],
        )
        sv = lower_component(ctx, comp)
        text = emitter.emit_one(sv)
        assert "bit [31:0] chan_count;" in text

    def test_component_with_inheritance(self, ctx, emitter):
        comp = ir.DataTypeComponent(
            name="ext_comp",
            super=ir.DataTypeRef(ref_name="base_comp"),
            fields=[],
        )
        sv = lower_component(ctx, comp)
        text = emitter.emit_one(sv)
        assert "class ext_comp extends base_comp;" in text

    def test_component_constructor_args(self, ctx, emitter):
        comp = ir.DataTypeComponent(
            name="simple_c",
            super=None,
            fields=[],
        )
        sv = lower_component(ctx, comp)
        text = emitter.emit_one(sv)
        assert "input string name" in text
        assert "input zsp_component parent" in text


class TestComponentImportInterface:
    def test_component_with_import_has_if_field(self, ctx, emitter):
        comp = ir.DataTypeComponent(
            name="dma_c",
            super=None,
            fields=[],
            functions=[
                ir.Function(
                    name="do_transfer",
                    args=ir.Arguments(args=[]),
                    body=[],
                    is_import=True,
                    is_async=True,
                    metadata={},
                ),
            ],
        )
        sv = lower_component(ctx, comp)
        text = emitter.emit_one(sv)
        assert "dma_c_import_if import_if;" in text

    def test_component_without_import_no_if_field(self, ctx, emitter):
        comp = ir.DataTypeComponent(
            name="simple_c",
            super=None,
            fields=[],
            functions=[
                ir.Function(name="helper", body=[], metadata={}),
            ],
        )
        sv = lower_component(ctx, comp)
        text = emitter.emit_one(sv)
        assert "import_if" not in text

    def test_component_name_mangling(self, ctx, emitter):
        comp = ir.DataTypeComponent(
            name="pkg::my_comp",
            super=None,
            fields=[],
        )
        sv = lower_component(ctx, comp)
        text = emitter.emit_one(sv)
        assert "class pkg__my_comp" in text
