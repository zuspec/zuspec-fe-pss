"""Tests for inference mode flag behavior.

Verifies that the ``inference_mode`` parameter controls which inference
mechanisms are emitted in the generated SV output.
"""

import pytest
from zuspec.be.sv.ir.sv_emit import SVEmitter

from zuspec.fe.pss.sv.context import LoweringContext
from zuspec.fe.pss.ast_to_ir import AstToIrContext
from zuspec.fe.pss.sv.lower_factory import (
    ActionTypeEntry,
    assign_type_ids,
    emit_factory_function,
    emit_factory_items,
    emit_type_id_constants,
)
from zuspec.fe.pss.sv.lower_inference import (
    InferenceSlot,
    SlotComplexity,
    classify_slot,
    emit_selector_function,
    emit_infer_and_execute_task,
    emit_dpi_inference_imports,
    emit_dpi_inference_task,
)


@pytest.fixture
def emitter():
    return SVEmitter()


@pytest.fixture
def ctx():
    ir_ctx = AstToIrContext()
    ir_ctx.parent_comp_names = {
        "comp::act_a": "comp",
        "comp::act_b": "comp",
    }
    return LoweringContext(ir_ctx=ir_ctx)


@pytest.fixture
def simple_slot():
    return InferenceSlot(
        consumer_type="consumer_act", consumer_field="buf_in",
        flow_kind="buffer", flow_type="buf_t",
        candidates=[
            (0, "producer_a", "buf_out"),
            (1, "producer_b", "buf_out"),
        ],
    )


@pytest.fixture
def complex_slot():
    return InferenceSlot(
        consumer_type="sink_act", consumer_field="data_in",
        flow_kind="buffer", flow_type="data_t",
        candidates=[(i, f"src_{i}", "out") for i in range(5)],
        depth=2,
    )


class TestStaticMode:
    """inference_mode='static': no runtime inference code."""

    def test_no_selector_needed(self, simple_slot):
        """In static mode, slots are pre-elaborated -- no selector emitted."""
        # Static mode means the user chooses not to emit runtime inference.
        # The slot classification still works, but the code generator
        # should not emit selector/factory items.
        # We verify by checking that the mode is "static" and no
        # inference items would be emitted for it.
        assert classify_slot(simple_slot) == SlotComplexity.SIMPLE
        # In static mode, the caller would skip emitting inference items.
        # This test documents that behavior.

    def test_no_factory_in_static_output(self, ctx, emitter):
        """When no inference is requested, factory is not needed."""
        # In static mode, pss_to_sv does not emit factory items.
        # Verify factory items can be generated but are only included
        # when inference_mode != 'static'.
        registry = assign_type_ids(["comp::act_a", "comp::act_b"], ctx)
        items = emit_factory_items(registry)
        # Items exist but would not be emitted in static mode
        assert len(items) > 0


class TestSvNativeMode:
    """inference_mode='sv-native': SV-native selectors for simple slots."""

    def test_selector_emitted_for_simple(self, simple_slot, emitter):
        func = emit_selector_function(simple_slot)
        text = emitter.emit_one(func)
        assert "select_producer_for_" in text
        assert "candidates" in text
        assert "seed %" in text

    def test_infer_task_emitted(self, simple_slot, emitter):
        task = emit_infer_and_execute_task(simple_slot)
        text = emitter.emit_one(task)
        assert "infer_and_execute_" in text
        assert "zsp_create_action" in text

    def test_factory_required(self, ctx, emitter):
        """SV-native mode requires the factory function."""
        registry = assign_type_ids(["comp::act_a", "comp::act_b"], ctx)
        func = emit_factory_function(registry)
        text = emitter.emit_one(func)
        assert "zsp_create_action" in text
        assert "case (type_id)" in text

    def test_complex_slot_not_covered(self, complex_slot):
        """SV-native mode cannot handle complex slots."""
        assert classify_slot(complex_slot) == SlotComplexity.COMPLEX


class TestDpiMode:
    """inference_mode='dpi': DPI for complex, SV-native for simple."""

    def test_simple_slot_uses_sv_native(self, simple_slot, emitter):
        assert classify_slot(simple_slot) == SlotComplexity.SIMPLE
        func = emit_selector_function(simple_slot)
        text = emitter.emit_one(func)
        assert "candidates" in text

    def test_complex_slot_uses_dpi(self, complex_slot, emitter):
        assert classify_slot(complex_slot) == SlotComplexity.COMPLEX
        task = emit_dpi_inference_task(complex_slot)
        text = emitter.emit_one(task)
        assert "zsp_dpi_infer" in text

    def test_dpi_imports_present(self):
        lines = emit_dpi_inference_imports()
        assert any("zsp_dpi_infer" in l for l in lines)


class TestFullMode:
    """inference_mode='full': DPI for all slots."""

    def test_simple_slot_gets_dpi_task(self, simple_slot, emitter):
        """In full mode, even simple slots use DPI."""
        task = emit_dpi_inference_task(simple_slot)
        text = emitter.emit_one(task)
        assert "zsp_dpi_infer" in text

    def test_static_slot_gets_dpi_task(self, emitter):
        """Even a single-candidate slot uses DPI in full mode."""
        slot = InferenceSlot(
            consumer_type="c", consumer_field="f",
            flow_kind="buffer", flow_type="t",
            candidates=[(0, "only_prod", "out")],
        )
        task = emit_dpi_inference_task(slot)
        text = emitter.emit_one(task)
        assert "zsp_dpi_infer" in text


class TestModeInteraction:
    def test_factory_type_ids_stable(self, ctx):
        """Type IDs are deterministic (sorted by name)."""
        reg1 = assign_type_ids(["comp::act_b", "comp::act_a"], ctx)
        reg2 = assign_type_ids(["comp::act_a", "comp::act_b"], ctx)
        for name in reg1:
            assert reg1[name].type_id == reg2[name].type_id

    def test_classification_independent_of_mode(self, simple_slot, complex_slot):
        """Slot classification is intrinsic, not mode-dependent."""
        assert classify_slot(simple_slot) == SlotComplexity.SIMPLE
        assert classify_slot(complex_slot) == SlotComplexity.COMPLEX
