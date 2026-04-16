"""Lower PSS flow objects (buffer, stream, state) to SV statements.

Buffer, stream, and state flow objects are PSS abstractions for passing
data between actions.  Each maps to a different SV runtime pattern:

- **Buffer**: Sequential producer/consumer -- local variable passing.
- **Stream**: Parallel producer/consumer -- ``zsp_stream_channel`` mailbox.
- **State**: Persistent read/write -- ``zsp_state_pool`` operations.
"""
from __future__ import annotations

import dataclasses as dc
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import LoweringContext


# -----------------------------------------------------------------------
# Data structures describing flow-object bindings
# -----------------------------------------------------------------------

@dc.dataclass
class FlowBinding:
    """One flow-object binding between a producer and a consumer.

    Attributes:
        flow_type:       Mangled SV type name of the flow object
                         (e.g. ``data_buffer_s``).
        flow_kind:       ``"buffer"``, ``"stream"``, or ``"state"``.
        producer_var:    SV variable name of the producing action instance.
        consumer_var:    SV variable name of the consuming action instance.
        producer_field:  Name of the output field on the producer action
                         (e.g. ``buf_out``).
        consumer_field:  Name of the input field on the consumer action
                         (e.g. ``buf_in``).
        label:           Optional user-assigned label for the flow variable.
        pool_expr:       For state objects: SV expression for the state pool
                         on the component (e.g. ``comp.power_pool``).
    """
    flow_type: str
    flow_kind: str
    producer_var: str
    consumer_var: str
    producer_field: str
    consumer_field: str
    label: Optional[str] = None
    pool_expr: Optional[str] = None


# -----------------------------------------------------------------------
# Buffer lowering  (sequential producer -> consumer)
# -----------------------------------------------------------------------

def emit_buffer_decl(binding: FlowBinding) -> List[str]:
    """Declare a local variable for a buffer flow object.

    The variable is declared at the activity scope; the producer writes
    it after body, and the consumer reads it before randomize.

    Returns:
        SV declaration line(s).
    """
    var_name = _flow_var_name(binding)
    return [f"{binding.flow_type} {var_name};"]


def emit_buffer_producer_capture(binding: FlowBinding) -> List[str]:
    """Emit the statement that captures the producer's output into the
    local buffer variable.  Placed after the producer's ``body()`` call.

    Returns:
        SV statement line(s).
    """
    var_name = _flow_var_name(binding)
    return [f"{var_name} = {binding.producer_var}.{binding.producer_field};"]


def emit_buffer_consumer_inject(binding: FlowBinding) -> List[str]:
    """Emit the statement that injects the buffer value into the consumer
    before randomize.  The consumer's flow-input field is assigned the
    buffered value, making it non-rand (state).

    Returns:
        SV statement line(s).
    """
    var_name = _flow_var_name(binding)
    return [f"{binding.consumer_var}.{binding.consumer_field} = {var_name};"]


def emit_buffer_consumer_constraint(binding: FlowBinding) -> List[str]:
    """Emit randomize-with constraints that pin the consumer's flow-input
    fields to their injected values.

    When the consumer is randomized, the flow-input field must be treated
    as fixed (non-rand).  We achieve this by constraining it in the
    ``randomize() with { ... }`` block.

    Returns:
        SV constraint expression string(s) for the with-block.
    """
    var_name = _flow_var_name(binding)
    return [f"{binding.consumer_field} == {var_name}"]


# -----------------------------------------------------------------------
# Stream lowering  (parallel producer || consumer via mailbox)
# -----------------------------------------------------------------------

def emit_stream_decl(binding: FlowBinding) -> List[str]:
    """Declare a ``zsp_stream_channel`` for a stream flow object.

    Returns:
        SV declaration + construction lines.
    """
    var_name = _flow_var_name(binding)
    return [
        f"zsp_stream_channel #({binding.flow_type}) {var_name} = new();",
    ]


def emit_stream_producer_put(binding: FlowBinding) -> List[str]:
    """Emit the ``channel.put()`` call placed after the producer's body.

    Returns:
        SV statement line(s).
    """
    var_name = _flow_var_name(binding)
    return [f"{var_name}.put({binding.producer_var}.{binding.producer_field});"]


def emit_stream_consumer_get(binding: FlowBinding) -> List[str]:
    """Emit the ``channel.get()`` call placed before the consumer's randomize.

    Returns:
        SV statement line(s).
    """
    var_name = _flow_var_name(binding)
    return [f"{var_name}.get({binding.consumer_var}.{binding.consumer_field});"]


# -----------------------------------------------------------------------
# State lowering  (persistent pool read/write)
# -----------------------------------------------------------------------

def emit_state_write(binding: FlowBinding) -> List[str]:
    """Emit the ``pool.write()`` call placed after the writer's body.

    The writer pushes its output to the state pool on the component.

    Returns:
        SV statement line(s).
    """
    pool = binding.pool_expr or "comp.state_pool"
    return [f"{pool}.write({binding.producer_var}.{binding.producer_field});"]


def emit_state_read(binding: FlowBinding) -> List[str]:
    """Emit the ``pool.read()`` call placed before the reader's randomize.

    The reader pulls the current state value from the pool.

    Returns:
        SV statement line(s).
    """
    pool = binding.pool_expr or "comp.state_pool"
    return [
        f"{binding.consumer_var}.{binding.consumer_field} = {pool}.read();",
    ]


# -----------------------------------------------------------------------
# Integrated traversal helpers
# -----------------------------------------------------------------------

def emit_flow_traversal_sequential(
    bindings: List[FlowBinding],
    producer_body_lines: List[str],
    consumer_body_lines: List[str],
    comp_expr: str = "comp",
) -> List[str]:
    """Emit a complete sequential producer/consumer traversal with
    flow-object wiring for buffer and state bindings.

    This wraps the producer and consumer lifecycle blocks with the
    appropriate flow-object declarations, captures, and injections.

    Args:
        bindings: Flow bindings between the producer and consumer.
        producer_body_lines: Pre-generated SV lines for the producer
            traversal (before flow capture).
        consumer_body_lines: Pre-generated SV lines for the consumer
            traversal (before flow injection).
        comp_expr: SV expression for the component.

    Returns:
        Combined SV statement lines with flow wiring.
    """
    lines: List[str] = []

    # Declarations
    for b in bindings:
        if b.flow_kind == "buffer":
            lines.extend(emit_buffer_decl(b))
        elif b.flow_kind == "state":
            pass  # state uses pool, no local var needed

    # Producer body + capture
    lines.extend(producer_body_lines)
    for b in bindings:
        if b.flow_kind == "buffer":
            lines.extend(emit_buffer_producer_capture(b))
        elif b.flow_kind == "state":
            lines.extend(emit_state_write(b))

    # Consumer injection + body
    for b in bindings:
        if b.flow_kind == "buffer":
            lines.extend(emit_buffer_consumer_inject(b))
        elif b.flow_kind == "state":
            lines.extend(emit_state_read(b))
    lines.extend(consumer_body_lines)

    return lines


def emit_flow_traversal_parallel(
    bindings: List[FlowBinding],
    producer_body_lines: List[str],
    consumer_body_lines: List[str],
    comp_expr: str = "comp",
) -> List[str]:
    """Emit a parallel producer/consumer traversal with stream flow wiring.

    Stream bindings use ``zsp_stream_channel`` (mailbox-based) to pass
    data between concurrently running producer and consumer.

    Args:
        bindings: Stream flow bindings.
        producer_body_lines: SV lines for the producer traversal.
        consumer_body_lines: SV lines for the consumer traversal.
        comp_expr: SV expression for the component.

    Returns:
        SV statement lines with fork/join and stream wiring.
    """
    lines: List[str] = []

    # Stream channel declarations
    for b in bindings:
        if b.flow_kind == "stream":
            lines.extend(emit_stream_decl(b))

    # Fork producer and consumer
    lines.append("fork")

    # Producer branch
    lines.append("  begin")
    for l in producer_body_lines:
        lines.append(f"    {l}")
    for b in bindings:
        if b.flow_kind == "stream":
            for l in emit_stream_producer_put(b):
                lines.append(f"    {l}")
    lines.append("  end")

    # Consumer branch
    lines.append("  begin")
    for b in bindings:
        if b.flow_kind == "stream":
            for l in emit_stream_consumer_get(b):
                lines.append(f"    {l}")
    for l in consumer_body_lines:
        lines.append(f"    {l}")
    lines.append("  end")

    lines.append("join")

    return lines


def emit_flow_object_wiring(
    bindings: List[FlowBinding],
    action_var: str,
    role: str,
) -> Dict[str, List[str]]:
    """Emit flow-object wiring statements for a single action traversal.

    Returns a dict with keys ``"pre_randomize"``, ``"post_body"``, and
    ``"with_constraints"`` containing the SV lines/expressions to inject
    at the corresponding points in the traversal lifecycle.

    Args:
        bindings: All flow bindings involving this action.
        action_var: SV variable name of the action.
        role: ``"producer"`` or ``"consumer"``.

    Returns:
        Dict mapping lifecycle phase to list of SV lines/expressions.
    """
    pre_rand: List[str] = []
    post_body: List[str] = []
    with_constraints: List[str] = []

    for b in bindings:
        if role == "producer":
            if b.flow_kind == "buffer":
                post_body.extend(emit_buffer_producer_capture(b))
            elif b.flow_kind == "stream":
                post_body.extend(emit_stream_producer_put(b))
            elif b.flow_kind == "state":
                post_body.extend(emit_state_write(b))

        elif role == "consumer":
            if b.flow_kind == "buffer":
                pre_rand.extend(emit_buffer_consumer_inject(b))
                with_constraints.extend(emit_buffer_consumer_constraint(b))
            elif b.flow_kind == "stream":
                pre_rand.extend(emit_stream_consumer_get(b))
            elif b.flow_kind == "state":
                pre_rand.extend(emit_state_read(b))

    return {
        "pre_randomize": pre_rand,
        "post_body": post_body,
        "with_constraints": with_constraints,
    }


# -----------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------

def _flow_var_name(binding: FlowBinding) -> str:
    """Derive a local variable name for a flow-object binding."""
    if binding.label:
        return binding.label
    # Use producer/consumer field names to form a unique variable
    return f"_flow_{binding.producer_field}_{binding.consumer_field}"
