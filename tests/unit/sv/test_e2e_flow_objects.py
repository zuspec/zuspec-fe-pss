"""End-to-end tests: flow objects (buffer, stream, state).

Builds IR models with flow-object bindings and verifies the generated
SV wiring patterns for each flow-object kind.
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
from zuspec.fe.pss.sv.context import LoweringContext
from zuspec.fe.pss.sv.lower_flow_objects import (
    FlowBinding,
    emit_flow_traversal_sequential,
    emit_flow_traversal_parallel,
    emit_flow_object_wiring,
)
from zuspec.fe.pss.sv.lower_flow_constraints import (
    propagate_constraints_to_producer,
    build_field_remap,
)


@pytest.fixture
def emitter():
    return SVEmitter()


@pytest.fixture
def ctx():
    return LoweringContext()


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="zsp_e2e_flow_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestBufferE2E:
    def test_sequential_producer_consumer(self):
        """Buffer: producer writes local var, consumer reads it."""
        binding = FlowBinding(
            flow_type="data_buffer_s",
            flow_kind="buffer",
            producer_var="wr",
            consumer_var="rd",
            producer_field="buf_out",
            consumer_field="buf_in",
        )
        producer_lines = [
            "wr.comp = comp;",
            "if (!wr.randomize())",
            '  $fatal(1, "randomize failed: wr");',
            "wr.body();",
        ]
        consumer_lines = [
            "rd.comp = comp;",
            "if (!rd.randomize())",
            '  $fatal(1, "randomize failed: rd");',
            "rd.body();",
        ]
        lines = emit_flow_traversal_sequential(
            [binding], producer_lines, consumer_lines
        )
        text = "\n".join(lines)

        # Full lifecycle: decl -> producer -> capture -> inject -> consumer
        assert "data_buffer_s _flow_buf_out_buf_in;" in text
        assert "wr.body();" in text
        assert "_flow_buf_out_buf_in = wr.buf_out;" in text
        assert "rd.buf_in = _flow_buf_out_buf_in;" in text
        assert "rd.body();" in text

        # Ordering
        assert text.index("data_buffer_s") < text.index("wr.body()")
        assert text.index("wr.body()") < text.index("= wr.buf_out")
        assert text.index("rd.buf_in =") < text.index("rd.body()")

    def test_buffer_type_in_sv_output(self, emitter, tmp_dir):
        """Buffer type (struct extending zsp_buffer) appears in SV output."""
        buf_dt = ir.DataTypeStruct(
            name="data_buffer_s", super=None,
            fields=[
                ir.Field(name="addr", datatype=ir.DataTypeInt(bits=32, signed=False),
                         rand_kind="rand"),
                ir.Field(name="size", datatype=ir.DataTypeInt(bits=16, signed=False),
                         rand_kind="rand"),
            ],
        )
        ir_ctx = AstToIrContext()
        ir_ctx.add_type("data_buffer_s", buf_dt)
        sv_nodes = pss_to_sv(ir_ctx)
        text = emitter.emit_all(sv_nodes)

        assert "class data_buffer_s" in text
        assert "rand bit [31:0] addr;" in text
        assert "rand bit [15:0] size;" in text

    def test_consumer_constraint_injection(self):
        """Consumer constraints on flow fields propagated to producer."""
        constraints = [
            ("addr_c", ["buf_in.addr < 32'h8000"]),
            ("size_c", ["buf_in.size > 0"]),
        ]
        remap = build_field_remap("buf_in", "buf_out", ["addr", "size"])
        result = propagate_constraints_to_producer(
            constraints,
            flow_fields={"buf_in"},
            field_remap=remap,
        )
        assert len(result) == 2
        assert "buf_out.addr < 32'h8000" in result
        assert "buf_out.size > 0" in result


class TestStreamE2E:
    def test_parallel_producer_consumer(self):
        """Stream: producer and consumer run in parallel via mailbox."""
        binding = FlowBinding(
            flow_type="frame_stream_s",
            flow_kind="stream",
            producer_var="prod",
            consumer_var="cons",
            producer_field="stream_out",
            consumer_field="stream_in",
        )
        producer_lines = ["prod.body();"]
        consumer_lines = ["cons.body();"]
        lines = emit_flow_traversal_parallel(
            [binding], producer_lines, consumer_lines
        )
        text = "\n".join(lines)

        # Channel declaration
        assert "zsp_stream_channel #(frame_stream_s)" in text

        # Fork/join structure
        assert "fork" in text
        assert "join" in text

        # Producer puts after body
        assert "prod.body();" in text
        assert ".put(prod.stream_out);" in text

        # Consumer gets before body
        assert ".get(cons.stream_in);" in text
        assert "cons.body();" in text

    def test_stream_wiring_producer(self):
        binding = FlowBinding(
            flow_type="s_t", flow_kind="stream",
            producer_var="p", consumer_var="c",
            producer_field="out", consumer_field="in_",
        )
        wiring = emit_flow_object_wiring([binding], "p", "producer")
        assert len(wiring["post_body"]) == 1
        assert ".put(p.out)" in wiring["post_body"][0]

    def test_stream_wiring_consumer(self):
        binding = FlowBinding(
            flow_type="s_t", flow_kind="stream",
            producer_var="p", consumer_var="c",
            producer_field="out", consumer_field="in_",
        )
        wiring = emit_flow_object_wiring([binding], "c", "consumer")
        assert len(wiring["pre_randomize"]) == 1
        assert ".get(c.in_)" in wiring["pre_randomize"][0]


class TestStateE2E:
    def test_write_then_read(self):
        """State: writer pushes to pool, reader pulls current value."""
        binding = FlowBinding(
            flow_type="power_state_s",
            flow_kind="state",
            producer_var="writer",
            consumer_var="reader",
            producer_field="state_out",
            consumer_field="state_in",
            pool_expr="comp.power_pool",
        )
        producer_lines = ["writer.body();"]
        consumer_lines = ["reader.body();"]
        lines = emit_flow_traversal_sequential(
            [binding], producer_lines, consumer_lines
        )
        text = "\n".join(lines)

        # Write after producer body
        assert "comp.power_pool.write(writer.state_out);" in text
        assert text.index("writer.body()") < text.index("comp.power_pool.write")

        # Read before consumer body
        assert "reader.state_in = comp.power_pool.read();" in text
        assert text.index("comp.power_pool.read()") < text.index("reader.body()")

    def test_state_pool_operations(self):
        binding = FlowBinding(
            flow_type="st_t", flow_kind="state",
            producer_var="w", consumer_var="r",
            producer_field="s_o", consumer_field="s_i",
            pool_expr="comp.st_pool",
        )
        wiring = emit_flow_object_wiring([binding], "w", "producer")
        assert "comp.st_pool.write(w.s_o);" in wiring["post_body"]

        wiring = emit_flow_object_wiring([binding], "r", "consumer")
        assert "r.s_i = comp.st_pool.read();" in wiring["pre_randomize"]


class TestMixedFlowObjects:
    def test_buffer_and_state_sequential(self):
        """Multiple flow bindings in one sequential traversal."""
        buf_b = FlowBinding(
            flow_type="buf_t", flow_kind="buffer",
            producer_var="p", consumer_var="c",
            producer_field="b_out", consumer_field="b_in",
        )
        state_b = FlowBinding(
            flow_type="st_t", flow_kind="state",
            producer_var="p", consumer_var="c",
            producer_field="s_out", consumer_field="s_in",
            pool_expr="comp.pool",
        )
        producer_lines = ["p.body();"]
        consumer_lines = ["c.body();"]
        lines = emit_flow_traversal_sequential(
            [buf_b, state_b], producer_lines, consumer_lines
        )
        text = "\n".join(lines)

        # Buffer decl
        assert "buf_t _flow_b_out_b_in;" in text
        # Buffer capture + state write
        assert "_flow_b_out_b_in = p.b_out;" in text
        assert "comp.pool.write(p.s_out);" in text
        # Buffer inject + state read
        assert "c.b_in = _flow_b_out_b_in;" in text
        assert "c.s_in = comp.pool.read();" in text

    def test_constraint_propagation_with_multi_field(self):
        """Complex constraint on multiple sub-fields."""
        constraints = [
            ("c1", ["buf_in.addr[1:0] == 0 && buf_in.size <= 4096"]),
        ]
        remap = build_field_remap("buf_in", "buf_out", ["addr", "size"])
        result = propagate_constraints_to_producer(
            constraints, flow_fields={"buf_in"}, field_remap=remap,
        )
        assert len(result) == 1
        assert "buf_out.addr[1:0] == 0" in result[0]
        assert "buf_out.size <= 4096" in result[0]
