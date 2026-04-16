"""Tests for flow object lowering (buffer, stream, state).

Covers Phase 6 of the implementation plan:
- Buffer: sequential producer -> consumer via local variable
- Stream: parallel producer/consumer via mailbox channel
- State: write then read via state pool
- Consumer constraint injection into producer randomize
"""

import pytest

from zuspec.fe.pss.sv.lower_flow_objects import (
    FlowBinding,
    emit_buffer_decl,
    emit_buffer_producer_capture,
    emit_buffer_consumer_inject,
    emit_buffer_consumer_constraint,
    emit_stream_decl,
    emit_stream_producer_put,
    emit_stream_consumer_get,
    emit_state_write,
    emit_state_read,
    emit_flow_traversal_sequential,
    emit_flow_traversal_parallel,
    emit_flow_object_wiring,
)
from zuspec.fe.pss.sv.lower_flow_constraints import (
    PropagatedConstraint,
    extract_flow_constraints,
    propagate_constraints_to_producer,
    build_field_remap,
)
from zuspec.fe.pss.sv.context import LoweringContext


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

@pytest.fixture
def ctx():
    return LoweringContext()


@pytest.fixture
def buf_binding():
    """A buffer binding between a write and read action."""
    return FlowBinding(
        flow_type="data_buffer_s",
        flow_kind="buffer",
        producer_var="wr",
        consumer_var="rd",
        producer_field="buf_out",
        consumer_field="buf_in",
    )


@pytest.fixture
def stream_binding():
    """A stream binding between producer and consumer actions."""
    return FlowBinding(
        flow_type="frame_stream_s",
        flow_kind="stream",
        producer_var="prod",
        consumer_var="cons",
        producer_field="stream_out",
        consumer_field="stream_in",
    )


@pytest.fixture
def state_binding():
    """A state binding between writer and reader actions."""
    return FlowBinding(
        flow_type="power_state_s",
        flow_kind="state",
        producer_var="writer",
        consumer_var="reader",
        producer_field="state_out",
        consumer_field="state_in",
        pool_expr="comp.power_pool",
    )


# -----------------------------------------------------------------------
# Buffer tests
# -----------------------------------------------------------------------

class TestBufferLowering:
    def test_buffer_decl(self, buf_binding):
        lines = emit_buffer_decl(buf_binding)
        text = "\n".join(lines)
        assert "data_buffer_s" in text
        assert "_flow_buf_out_buf_in" in text
        assert text.endswith(";")

    def test_buffer_decl_with_label(self):
        b = FlowBinding(
            flow_type="data_buffer_s",
            flow_kind="buffer",
            producer_var="wr",
            consumer_var="rd",
            producer_field="buf_out",
            consumer_field="buf_in",
            label="my_buf",
        )
        lines = emit_buffer_decl(b)
        assert "data_buffer_s my_buf;" in lines

    def test_producer_capture(self, buf_binding):
        lines = emit_buffer_producer_capture(buf_binding)
        text = "\n".join(lines)
        assert "_flow_buf_out_buf_in = wr.buf_out;" in text

    def test_consumer_inject(self, buf_binding):
        lines = emit_buffer_consumer_inject(buf_binding)
        text = "\n".join(lines)
        assert "rd.buf_in = _flow_buf_out_buf_in;" in text

    def test_consumer_constraint(self, buf_binding):
        exprs = emit_buffer_consumer_constraint(buf_binding)
        assert len(exprs) == 1
        assert "buf_in == _flow_buf_out_buf_in" in exprs[0]

    def test_sequential_traversal(self, buf_binding):
        producer_lines = [
            "wr.comp = comp;",
            "if (!wr.randomize())",
            '  $fatal(1, "randomize failed");',
            "wr.body();",
        ]
        consumer_lines = [
            "rd.comp = comp;",
            "if (!rd.randomize())",
            '  $fatal(1, "randomize failed");',
            "rd.body();",
        ]
        lines = emit_flow_traversal_sequential(
            [buf_binding], producer_lines, consumer_lines
        )
        text = "\n".join(lines)

        # Declaration comes first
        assert "data_buffer_s _flow_buf_out_buf_in;" in text

        # Producer body appears
        assert "wr.body();" in text

        # Capture appears after producer body
        assert "_flow_buf_out_buf_in = wr.buf_out;" in text
        assert text.index("wr.body()") < text.index("_flow_buf_out_buf_in = wr.buf_out")

        # Consumer inject appears before consumer body
        assert "rd.buf_in = _flow_buf_out_buf_in;" in text
        assert text.index("rd.buf_in = _flow_buf_out_buf_in") < text.index("rd.body()")


# -----------------------------------------------------------------------
# Stream tests
# -----------------------------------------------------------------------

class TestStreamLowering:
    def test_stream_decl(self, stream_binding):
        lines = emit_stream_decl(stream_binding)
        text = "\n".join(lines)
        assert "zsp_stream_channel #(frame_stream_s)" in text
        assert "_flow_stream_out_stream_in" in text
        assert "new()" in text

    def test_producer_put(self, stream_binding):
        lines = emit_stream_producer_put(stream_binding)
        text = "\n".join(lines)
        assert "_flow_stream_out_stream_in.put(prod.stream_out);" in text

    def test_consumer_get(self, stream_binding):
        lines = emit_stream_consumer_get(stream_binding)
        text = "\n".join(lines)
        assert "_flow_stream_out_stream_in.get(cons.stream_in);" in text

    def test_parallel_traversal(self, stream_binding):
        producer_lines = [
            "prod.comp = comp;",
            "prod.body();",
        ]
        consumer_lines = [
            "cons.comp = comp;",
            "cons.body();",
        ]
        lines = emit_flow_traversal_parallel(
            [stream_binding], producer_lines, consumer_lines
        )
        text = "\n".join(lines)

        # Channel declaration before fork
        assert "zsp_stream_channel #(frame_stream_s)" in text
        assert "fork" in text
        assert "join" in text

        # Producer branch has body + put
        assert "prod.body();" in text
        assert ".put(prod.stream_out);" in text

        # Consumer branch has get + body
        assert ".get(cons.stream_in);" in text
        assert "cons.body();" in text

        # fork comes after decl, join at end
        assert text.index("zsp_stream_channel") < text.index("fork")
        assert text.index("fork") < text.index("join")


# -----------------------------------------------------------------------
# State tests
# -----------------------------------------------------------------------

class TestStateLowering:
    def test_state_write(self, state_binding):
        lines = emit_state_write(state_binding)
        text = "\n".join(lines)
        assert "comp.power_pool.write(writer.state_out);" in text

    def test_state_write_default_pool(self):
        b = FlowBinding(
            flow_type="my_state_s",
            flow_kind="state",
            producer_var="w",
            consumer_var="r",
            producer_field="s_out",
            consumer_field="s_in",
        )
        lines = emit_state_write(b)
        assert "comp.state_pool.write(w.s_out);" in lines

    def test_state_read(self, state_binding):
        lines = emit_state_read(state_binding)
        text = "\n".join(lines)
        assert "reader.state_in = comp.power_pool.read();" in text

    def test_sequential_traversal_with_state(self, state_binding):
        producer_lines = ["writer.body();"]
        consumer_lines = ["reader.body();"]
        lines = emit_flow_traversal_sequential(
            [state_binding], producer_lines, consumer_lines
        )
        text = "\n".join(lines)

        # State write after producer body
        assert "comp.power_pool.write(writer.state_out);" in text
        assert text.index("writer.body()") < text.index("comp.power_pool.write")

        # State read before consumer body
        assert "reader.state_in = comp.power_pool.read();" in text
        assert text.index("comp.power_pool.read()") < text.index("reader.body()")


# -----------------------------------------------------------------------
# Flow-object wiring helper tests
# -----------------------------------------------------------------------

class TestFlowObjectWiring:
    def test_producer_wiring_buffer(self, buf_binding):
        wiring = emit_flow_object_wiring([buf_binding], "wr", "producer")
        assert len(wiring["pre_randomize"]) == 0
        assert len(wiring["post_body"]) == 1
        assert "wr.buf_out" in wiring["post_body"][0]
        assert len(wiring["with_constraints"]) == 0

    def test_consumer_wiring_buffer(self, buf_binding):
        wiring = emit_flow_object_wiring([buf_binding], "rd", "consumer")
        assert len(wiring["pre_randomize"]) == 1
        assert "rd.buf_in" in wiring["pre_randomize"][0]
        assert len(wiring["with_constraints"]) == 1
        assert "buf_in ==" in wiring["with_constraints"][0]
        assert len(wiring["post_body"]) == 0

    def test_producer_wiring_stream(self, stream_binding):
        wiring = emit_flow_object_wiring([stream_binding], "prod", "producer")
        assert len(wiring["post_body"]) == 1
        assert ".put(" in wiring["post_body"][0]

    def test_consumer_wiring_stream(self, stream_binding):
        wiring = emit_flow_object_wiring([stream_binding], "cons", "consumer")
        assert len(wiring["pre_randomize"]) == 1
        assert ".get(" in wiring["pre_randomize"][0]

    def test_producer_wiring_state(self, state_binding):
        wiring = emit_flow_object_wiring([state_binding], "writer", "producer")
        assert len(wiring["post_body"]) == 1
        assert ".write(" in wiring["post_body"][0]

    def test_consumer_wiring_state(self, state_binding):
        wiring = emit_flow_object_wiring([state_binding], "reader", "consumer")
        assert len(wiring["pre_randomize"]) == 1
        assert ".read()" in wiring["pre_randomize"][0]

    def test_multiple_bindings(self, buf_binding, state_binding):
        wiring = emit_flow_object_wiring(
            [buf_binding, state_binding], "wr", "producer"
        )
        assert len(wiring["post_body"]) == 2


# -----------------------------------------------------------------------
# Constraint propagation tests
# -----------------------------------------------------------------------

class TestFlowConstraintPropagation:
    def test_extract_simple_constraint(self, ctx):
        constraints = [
            ("addr_range", ["buf_in.addr < 32'h8000"]),
        ]
        result = extract_flow_constraints(
            ctx,
            constraints,
            flow_fields={"buf_in"},
            field_remap={"buf_in": "buf_out"},
        )
        assert len(result) == 1
        assert result[0].remapped_expr == "buf_out.addr < 32'h8000"
        assert result[0].original_expr == "buf_in.addr < 32'h8000"

    def test_no_flow_field_reference(self, ctx):
        constraints = [
            ("unrelated", ["data_val > 0"]),
        ]
        result = extract_flow_constraints(
            ctx,
            constraints,
            flow_fields={"buf_in"},
        )
        assert len(result) == 0

    def test_multiple_constraints_mixed(self, ctx):
        constraints = [
            ("c1", ["buf_in.addr > 0", "local_field == 5"]),
            ("c2", ["buf_in.size < 256"]),
        ]
        result = extract_flow_constraints(
            ctx,
            constraints,
            flow_fields={"buf_in"},
            field_remap={"buf_in": "buf_out"},
        )
        # Should extract 2 (buf_in.addr > 0 and buf_in.size < 256)
        assert len(result) == 2
        remapped = [r.remapped_expr for r in result]
        assert "buf_out.addr > 0" in remapped
        assert "buf_out.size < 256" in remapped

    def test_propagate_constraints_shortcut(self):
        constraints = [
            ("range_c", ["buf_in < 32'hFFFF"]),
        ]
        result = propagate_constraints_to_producer(
            constraints,
            flow_fields={"buf_in"},
            field_remap={"buf_in": "buf_out"},
        )
        assert len(result) == 1
        assert result[0] == "buf_out < 32'hFFFF"

    def test_propagate_no_remap(self):
        constraints = [
            ("c", ["buf_in > 0"]),
        ]
        result = propagate_constraints_to_producer(
            constraints,
            flow_fields={"buf_in"},
        )
        # Without remap, field names stay the same
        assert result == ["buf_in > 0"]

    def test_build_field_remap_basic(self):
        remap = build_field_remap("buf_in", "buf_out")
        assert remap == {"buf_in": "buf_out"}

    def test_build_field_remap_with_subfields(self):
        remap = build_field_remap("buf_in", "buf_out", ["addr", "size"])
        assert remap == {
            "buf_in": "buf_out",
            "buf_in.addr": "buf_out.addr",
            "buf_in.size": "buf_out.size",
        }

    def test_constraint_remap_preserves_non_flow_refs(self, ctx):
        constraints = [
            ("mixed", ["buf_in.addr > 0 && other_field < 100"]),
        ]
        result = extract_flow_constraints(
            ctx,
            constraints,
            flow_fields={"buf_in"},
            field_remap={"buf_in": "buf_out"},
        )
        assert len(result) == 1
        # buf_in remapped, other_field untouched
        assert "buf_out.addr > 0" in result[0].remapped_expr
        assert "other_field < 100" in result[0].remapped_expr

    def test_subfield_remap_longer_match_first(self, ctx):
        """Ensure buf_in.addr is remapped before buf_in to avoid
        partial replacement issues."""
        constraints = [
            ("c", ["buf_in.addr == buf_in.size"]),
        ]
        remap = build_field_remap("buf_in", "buf_out", ["addr", "size"])
        result = extract_flow_constraints(
            ctx,
            constraints,
            flow_fields={"buf_in"},
            field_remap=remap,
        )
        assert len(result) == 1
        assert result[0].remapped_expr == "buf_out.addr == buf_out.size"

    def test_no_partial_match(self, ctx):
        """Field 'buf_in' should not match 'buf_input' or 'my_buf_in'."""
        constraints = [
            ("c", ["buf_input > 0"]),
            ("d", ["my_buf_in > 0"]),
        ]
        result = extract_flow_constraints(
            ctx,
            constraints,
            flow_fields={"buf_in"},
        )
        assert len(result) == 0
