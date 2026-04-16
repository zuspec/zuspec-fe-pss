"""Tests for DPI inference (Layer 2) -- structural placeholders.

DPI library implementation is deferred to Phase 8. These tests verify
the generated SV structures (import declarations, task body) are
syntactically correct without requiring the DPI library.
"""

import pytest
from zuspec.be.sv.ir.sv_emit import SVEmitter

from zuspec.fe.pss.sv.lower_inference import (
    InferenceSlot,
    emit_dpi_inference_imports,
    emit_dpi_inference_task,
)


@pytest.fixture
def emitter():
    return SVEmitter()


class TestDpiImportDeclarations:
    def test_dpi_imports_emitted(self):
        lines = emit_dpi_inference_imports()
        text = "\n".join(lines)

        assert 'import "DPI-C"' in text
        assert "zsp_dpi_infer" in text
        assert "zsp_dpi_plan_length" in text
        assert "zsp_dpi_plan_action_type" in text
        assert "zsp_dpi_plan_ordering" in text
        assert "zsp_dpi_plan_destroy" in text

    def test_import_count(self):
        lines = emit_dpi_inference_imports()
        assert len(lines) == 7


class TestDpiInferenceTask:
    def test_dpi_task_structure(self, emitter):
        slot = InferenceSlot(
            consumer_type="read_act", consumer_field="buf_in",
            flow_kind="buffer", flow_type="buf_t",
            candidates=[(0, "write_act", "buf_out")],
        )
        task = emit_dpi_inference_task(slot)
        text = emitter.emit_one(task)

        assert "dpi_infer_and_execute_read_act_buf_in" in task.name
        assert "zsp_dpi_infer" in text
        assert "plan < 0" in text
        assert "$fatal" in text
        assert "zsp_dpi_plan_length" in text
        assert "zsp_create_action" in text
        assert "consumer.pre_solve();" in text
        assert "consumer.body();" in text
        assert "zsp_dpi_plan_destroy" in text

    def test_dpi_task_args(self):
        slot = InferenceSlot(
            consumer_type="my_act", consumer_field="in_f",
            flow_kind="state", flow_type="st_t",
            candidates=[],
        )
        task = emit_dpi_inference_task(slot)
        assert len(task.args) == 2
        assert task.args[0].name == "consumer"
        assert task.args[0].dtype == "my_act"
        assert task.args[1].name == "comp"

    def test_multi_level_plan_execution(self, emitter):
        """Verify the plan execution loop handles multi-level chains."""
        slot = InferenceSlot(
            consumer_type="sink_act", consumer_field="data_in",
            flow_kind="buffer", flow_type="data_t",
            candidates=[(0, "src_a", "out"), (1, "src_b", "out")],
            depth=2,
        )
        task = emit_dpi_inference_task(slot)
        text = emitter.emit_one(task)

        # Should have a loop over plan entries
        assert "for (int i = 0; i < zsp_dpi_plan_length(plan); i++)" in text
        assert "zsp_dpi_plan_action_type(plan, i)" in text
