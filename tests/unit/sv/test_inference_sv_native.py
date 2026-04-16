"""Tests for SV-native runtime inference (Layer 1).

Covers:
- Action factory generation (type IDs, case statement)
- Single-level buffer inference with ICL size 1
- Single-level with ICL size 2 (random selection)
- Selector function generation
- Infer-and-execute task generation
- Slot classification
"""

import pytest
from zuspec.be.sv.ir.sv_emit import SVEmitter

from zuspec.fe.pss.sv.context import LoweringContext
from zuspec.fe.pss.ast_to_ir import AstToIrContext
from zuspec.fe.pss.sv.lower_factory import (
    ActionTypeEntry,
    assign_type_ids,
    emit_type_id_constants,
    emit_factory_function,
    emit_factory_items,
)
from zuspec.fe.pss.sv.lower_inference import (
    InferenceSlot,
    SlotComplexity,
    classify_slot,
    emit_selector_function,
    emit_infer_and_execute_task,
)


@pytest.fixture
def emitter():
    return SVEmitter()


@pytest.fixture
def ctx():
    ir_ctx = AstToIrContext()
    ir_ctx.parent_comp_names = {
        "dma_c::transfer": "dma_c",
        "dma_c::fill": "dma_c",
        "cpu_c::read": "cpu_c",
    }
    lctx = LoweringContext(ir_ctx=ir_ctx)
    return lctx


@pytest.fixture
def registry(ctx):
    return assign_type_ids(
        ["dma_c::transfer", "dma_c::fill", "cpu_c::read"], ctx
    )


# -----------------------------------------------------------------------
# Factory tests
# -----------------------------------------------------------------------

class TestActionFactory:
    def test_assign_type_ids(self, registry):
        """Each action gets a unique sequential type ID."""
        ids = [e.type_id for e in registry.values()]
        assert sorted(ids) == [0, 1, 2]
        # Names are sorted, so IDs are assigned alphabetically
        names = sorted(registry.keys())
        for i, name in enumerate(names):
            assert registry[name].type_id == i

    def test_type_id_constants(self, registry):
        lines = emit_type_id_constants(registry)
        text = "\n".join(lines)
        assert "localparam int" in text
        assert "TYPE_ID_" in text
        # Three constants
        assert text.count("localparam int") == 3

    def test_factory_function_structure(self, registry, emitter):
        func = emit_factory_function(registry)
        assert func.name == "zsp_create_action"
        assert func.return_type == "zsp_action"
        assert len(func.args) == 2
        assert func.args[0].name == "type_id"
        assert func.args[1].name == "comp"

        text = emitter.emit_one(func)
        assert "case (type_id)" in text
        assert "endcase" in text
        assert "default:" in text
        assert "$fatal" in text

    def test_factory_covers_all_actions(self, registry, emitter):
        """Every registered action type appears in the factory case."""
        func = emit_factory_function(registry)
        text = emitter.emit_one(func)

        for name, entry in registry.items():
            assert entry.sv_class_name in text, f"{entry.sv_class_name} missing"
            assert f"a.comp = comp;" in text

    def test_factory_with_no_comp(self, emitter):
        """Action without a component uses comp_base."""
        registry = {
            "standalone": ActionTypeEntry(
                type_id=0, sv_class_name="standalone_act", comp_type=None,
            ),
        }
        func = emit_factory_function(registry)
        text = emitter.emit_one(func)
        assert "a.comp_base = comp;" in text

    def test_emit_factory_items(self, registry):
        items = emit_factory_items(registry)
        assert len(items) == 2  # constants + function

    def test_name_mangling_in_registry(self, ctx):
        registry = assign_type_ids(["pkg::MyAction"], ctx)
        assert "pkg::MyAction" in registry
        assert registry["pkg::MyAction"].sv_class_name == "pkg__MyAction"


# -----------------------------------------------------------------------
# Slot classification tests
# -----------------------------------------------------------------------

class TestSlotClassification:
    def test_static_single_candidate(self):
        slot = InferenceSlot(
            consumer_type="read_act", consumer_field="buf_in",
            flow_kind="buffer", flow_type="buf_t",
            candidates=[(0, "write_act", "buf_out")],
        )
        assert classify_slot(slot) == SlotComplexity.STATIC

    def test_simple_two_candidates(self):
        slot = InferenceSlot(
            consumer_type="read_act", consumer_field="buf_in",
            flow_kind="buffer", flow_type="buf_t",
            candidates=[
                (0, "write_act", "buf_out"),
                (1, "fill_act", "buf_out"),
            ],
        )
        assert classify_slot(slot) == SlotComplexity.SIMPLE

    def test_simple_three_candidates(self):
        slot = InferenceSlot(
            consumer_type="c", consumer_field="f",
            flow_kind="buffer", flow_type="t",
            candidates=[(i, f"a{i}", "o") for i in range(3)],
        )
        assert classify_slot(slot) == SlotComplexity.SIMPLE

    def test_complex_four_candidates(self):
        slot = InferenceSlot(
            consumer_type="c", consumer_field="f",
            flow_kind="buffer", flow_type="t",
            candidates=[(i, f"a{i}", "o") for i in range(4)],
        )
        assert classify_slot(slot) == SlotComplexity.COMPLEX

    def test_complex_deep_chain(self):
        slot = InferenceSlot(
            consumer_type="c", consumer_field="f",
            flow_kind="buffer", flow_type="t",
            candidates=[(0, "a0", "o"), (1, "a1", "o")],
            depth=2,
        )
        assert classify_slot(slot) == SlotComplexity.COMPLEX

    def test_pre_elaborated_no_candidates(self):
        slot = InferenceSlot(
            consumer_type="c", consumer_field="f",
            flow_kind="buffer", flow_type="t",
            candidates=[],
        )
        assert classify_slot(slot) == SlotComplexity.PRE_ELABORATED


# -----------------------------------------------------------------------
# Selector function tests
# -----------------------------------------------------------------------

class TestSelectorFunction:
    def test_single_candidate_constant(self, emitter):
        slot = InferenceSlot(
            consumer_type="read_act", consumer_field="buf_in",
            flow_kind="buffer", flow_type="buf_t",
            candidates=[(42, "write_act", "buf_out")],
        )
        func = emit_selector_function(slot)
        text = emitter.emit_one(func)
        assert "return 42;" in text
        assert "select_producer_for_read_act_buf_in" in func.name

    def test_two_candidates_random_select(self, emitter):
        slot = InferenceSlot(
            consumer_type="consumer", consumer_field="in_f",
            flow_kind="buffer", flow_type="t",
            candidates=[
                (0, "prod_a", "out_f"),
                (1, "prod_b", "out_f"),
            ],
        )
        func = emit_selector_function(slot)
        text = emitter.emit_one(func)
        assert "candidates" in text
        assert "seed % candidates.size()" in text
        assert "0" in text and "1" in text

    def test_no_candidates_fatal(self, emitter):
        slot = InferenceSlot(
            consumer_type="c", consumer_field="f",
            flow_kind="buffer", flow_type="t",
            candidates=[],
        )
        func = emit_selector_function(slot)
        text = emitter.emit_one(func)
        assert "$fatal" in text


# -----------------------------------------------------------------------
# Infer-and-execute task tests
# -----------------------------------------------------------------------

class TestInferAndExecuteTask:
    def test_sequential_buffer_single_candidate(self, emitter):
        slot = InferenceSlot(
            consumer_type="read_act", consumer_field="buf_in",
            flow_kind="buffer", flow_type="buf_t",
            candidates=[(0, "write_act", "buf_out")],
        )
        task = emit_infer_and_execute_task(slot)
        text = emitter.emit_one(task)

        assert "infer_and_execute_read_act_buf_in" in task.name
        assert "zsp_create_action" in text
        assert "producer.pre_solve();" in text
        assert "producer.randomize()" in text
        assert "producer.body();" in text
        assert "consumer.buf_in = producer.buf_out;" in text
        assert "consumer.pre_solve();" in text
        assert "consumer.body();" in text

    def test_sequential_buffer_multi_candidate(self, emitter):
        slot = InferenceSlot(
            consumer_type="consumer_act", consumer_field="buf_in",
            flow_kind="buffer", flow_type="buf_t",
            candidates=[
                (0, "write_act", "buf_out"),
                (1, "fill_act", "data_out"),
            ],
        )
        task = emit_infer_and_execute_task(slot)
        text = emitter.emit_one(task)

        # Should use case on producer_type for dynamic binding
        assert "case (producer_type)" in text
        assert "$cast" in text
        assert "write_act" in text
        assert "fill_act" in text
        assert "buf_out" in text
        assert "data_out" in text

    def test_stream_concurrent_fork(self, emitter):
        slot = InferenceSlot(
            consumer_type="consumer_act", consumer_field="stream_in",
            flow_kind="stream", flow_type="frame_stream_s",
            candidates=[(0, "producer_act", "stream_out")],
        )
        task = emit_infer_and_execute_task(slot)
        text = emitter.emit_one(task)

        assert "fork" in text
        assert "join" in text
        assert "zsp_stream_channel" in text
        assert "_ch.put(" in text
        assert "_ch.get(consumer.stream_in)" in text

    def test_with_consumer_constraints(self, emitter):
        slot = InferenceSlot(
            consumer_type="read_act", consumer_field="buf_in",
            flow_kind="buffer", flow_type="buf_t",
            candidates=[(0, "write_act", "buf_out")],
        )
        constraints = ["buf_out.addr < 32'h8000"]
        task = emit_infer_and_execute_task(slot, consumer_constraints=constraints)
        text = emitter.emit_one(task)

        assert "randomize() with" in text
        assert "buf_out.addr < 32'h8000" in text
