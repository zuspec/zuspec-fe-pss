"""Tests for PSS import function lowering to SV virtual classes."""

import pytest
from zuspec.dataclasses import ir
from zuspec.be.sv.ir.sv_emit import SVEmitter

from zuspec.fe.pss.sv.context import LoweringContext
from zuspec.fe.pss.sv.lower_imports import lower_import_interface


@pytest.fixture
def ctx():
    return LoweringContext()


@pytest.fixture
def emitter():
    return SVEmitter()


class TestLowerImports:
    def test_no_imports_returns_none(self, ctx):
        comp = ir.DataTypeComponent(name="simple_c", super=None, fields=[])
        result = lower_import_interface(ctx, comp)
        assert result is None

    def test_import_task(self, ctx, emitter):
        comp = ir.DataTypeComponent(
            name="dma_c",
            super=None,
            fields=[],
            functions=[
                ir.Function(
                    name="do_transfer",
                    args=ir.Arguments(args=[
                        ir.Arg(arg="src"),
                        ir.Arg(arg="dst"),
                    ]),
                    body=[],
                    is_import=True,
                    is_async=True,
                    metadata={},
                ),
            ],
        )
        sv = lower_import_interface(ctx, comp)
        assert sv is not None
        text = emitter.emit_one(sv)
        assert "virtual class dma_c_import_if;" in text
        assert "pure virtual task do_transfer" in text

    def test_import_function(self, ctx, emitter):
        comp = ir.DataTypeComponent(
            name="ctrl_c",
            super=None,
            fields=[],
            functions=[
                ir.Function(
                    name="get_status",
                    args=ir.Arguments(args=[]),
                    body=[],
                    returns=ir.DataTypeInt(bits=32, signed=False),
                    is_import=True,
                    is_async=False,
                    metadata={},
                ),
            ],
        )
        sv = lower_import_interface(ctx, comp)
        assert sv is not None
        text = emitter.emit_one(sv)
        assert "virtual class ctrl_c_import_if;" in text
        assert "pure virtual function" in text
        assert "get_status" in text


class TestLowerImportsAdvanced:
    def test_multiple_import_functions(self, ctx, emitter):
        comp = ir.DataTypeComponent(
            name="multi_c",
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
                ir.Function(
                    name="write_reg",
                    args=ir.Arguments(args=[ir.Arg(arg="addr"), ir.Arg(arg="data")]),
                    body=[],
                    is_import=True,
                    is_async=True,
                    metadata={},
                ),
            ],
        )
        sv = lower_import_interface(ctx, comp)
        assert sv is not None
        text = emitter.emit_one(sv)
        assert "pure virtual function" in text
        assert "read_reg" in text
        assert "pure virtual task write_reg" in text

    def test_import_name_mangling(self, ctx, emitter):
        comp = ir.DataTypeComponent(
            name="pkg::my_ctrl",
            super=None,
            fields=[],
            functions=[
                ir.Function(
                    name="init",
                    args=ir.Arguments(args=[]),
                    body=[],
                    is_import=True,
                    is_async=True,
                    metadata={},
                ),
            ],
        )
        sv = lower_import_interface(ctx, comp)
        assert sv is not None
        assert sv.name == "pkg__my_ctrl_import_if"
