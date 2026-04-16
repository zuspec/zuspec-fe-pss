"""SV-native runtime inference (Layer 1) and slot classification.

For each unbound flow-object input slot on a consumer action, this module:
1. Classifies the slot's complexity.
2. Emits a selector function that picks a producer type from the ICL
   (inference candidate list) at runtime.
3. Emits an infer-and-execute task that creates the inferred producer,
   runs it, binds the flow object, then runs the consumer.

DPI inference (Layer 2) is structured as an extension point but the
implementation is deferred to Phase 8.

Design reference: pss-to-sv-execution-design.md S12
"""
from __future__ import annotations

import dataclasses as dc
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from zuspec.be.sv.ir.sv import (
    SVFunctionDecl,
    SVTaskDecl,
    SVArg,
    SVRawItem,
)

if TYPE_CHECKING:
    from .context import LoweringContext
    from .lower_factory import ActionTypeEntry


# -----------------------------------------------------------------------
# Slot classification
# -----------------------------------------------------------------------

class SlotComplexity:
    """Complexity tiers for unbound flow-object slots."""
    STATIC = "static"        # ICL size 1 -- inline the single producer
    SIMPLE = "simple"        # ICL size 2-3, depth 1 -- SV-native selector
    COMPLEX = "complex"      # ICL size > 3, or depth > 1 -- DPI
    RUNTIME = "runtime"      # Depends on runtime state -- DPI with context
    PRE_ELABORATED = "pre_elaborated"  # Generation-time fallback


@dc.dataclass
class InferenceSlot:
    """Describes one unbound flow-object input slot on a consumer.

    Attributes:
        consumer_type:    Mangled SV class name of the consumer action.
        consumer_field:   Name of the unbound input field on the consumer.
        flow_kind:        ``"buffer"``, ``"stream"``, or ``"state"``.
        flow_type:        Mangled SV type name of the flow object.
        candidates:       List of (type_id, sv_class_name, output_field)
                          for each ICL candidate producer.
        complexity:       Classified complexity tier.
        depth:            Inference chain depth (1 = single level).
    """
    consumer_type: str
    consumer_field: str
    flow_kind: str
    flow_type: str
    candidates: List[Tuple[int, str, str]] = dc.field(default_factory=list)
    complexity: str = SlotComplexity.SIMPLE
    depth: int = 1


def classify_slot(slot: InferenceSlot) -> str:
    """Classify a slot's complexity based on ICL size and depth.

    Args:
        slot: The inference slot to classify.

    Returns:
        One of the SlotComplexity constants.
    """
    n = len(slot.candidates)
    if n == 0:
        return SlotComplexity.PRE_ELABORATED
    if n == 1:
        return SlotComplexity.STATIC
    if n <= 3 and slot.depth <= 1:
        return SlotComplexity.SIMPLE
    return SlotComplexity.COMPLEX


# -----------------------------------------------------------------------
# Selector function generation
# -----------------------------------------------------------------------

def emit_selector_function(
    slot: InferenceSlot,
    registry: Optional[Dict[str, "ActionTypeEntry"]] = None,
) -> SVFunctionDecl:
    """Emit a selector function for an unbound slot.

    The selector picks a producer type ID from the ICL candidates
    using ``$urandom`` to randomize the selection.

    For ICL size 1, returns the single candidate (constant).
    For ICL size > 1, returns ``candidates[seed % size]``.

    Args:
        slot: The inference slot.
        registry: Optional action type registry for TYPE_ID constants.

    Returns:
        SVFunctionDecl for the selector.
    """
    func_name = f"select_producer_for_{slot.consumer_type}_{slot.consumer_field}"
    body: List[str] = []

    if len(slot.candidates) == 0:
        body.append('$fatal(1, "No inference candidates for '
                     f'{slot.consumer_type}.{slot.consumer_field}");')
        body.append("return -1;")
    elif len(slot.candidates) == 1:
        type_id = slot.candidates[0][0]
        body.append(f"return {type_id};")
    else:
        # Build candidates array
        ids = [str(c[0]) for c in slot.candidates]
        body.append(f"int candidates[$] = '{{ {', '.join(ids)} }};")
        body.append(f"return candidates[seed % candidates.size()];")

    return SVFunctionDecl(
        name=func_name,
        args=[SVArg(name="seed", dtype="int")],
        return_type="int",
        body_lines=body,
    )


# -----------------------------------------------------------------------
# Infer-and-execute task generation
# -----------------------------------------------------------------------

def emit_infer_and_execute_task(
    slot: InferenceSlot,
    consumer_constraints: Optional[List[str]] = None,
) -> SVTaskDecl:
    """Emit an infer-and-execute task for an unbound slot.

    The task:
    1. Calls the selector to pick a producer type.
    2. Calls ``zsp_create_action()`` to instantiate the producer.
    3. Randomizes and executes the producer's body.
    4. Binds the flow object from producer to consumer.
    5. Randomizes and executes the consumer.

    For stream flow objects, the producer is forked alongside the consumer.

    Args:
        slot: The inference slot.
        consumer_constraints: Optional SV constraint expressions to inject
            into the producer's ``randomize() with { ... }`` block
            (flow-object constraint propagation).

    Returns:
        SVTaskDecl for the infer-and-execute task.
    """
    task_name = f"infer_and_execute_{slot.consumer_type}_{slot.consumer_field}"
    selector_name = f"select_producer_for_{slot.consumer_type}_{slot.consumer_field}"

    body: List[str] = []

    # Select producer type
    body.append(f"int producer_type = {selector_name}($urandom);")
    body.append(f"zsp_action producer = zsp_create_action(producer_type, comp);")
    body.append("")

    if slot.flow_kind == "stream":
        # Concurrent: fork producer alongside consumer
        body.extend(_emit_stream_inference(slot, consumer_constraints))
    else:
        # Sequential: producer before consumer (buffer/state)
        body.extend(_emit_sequential_inference(slot, consumer_constraints))

    return SVTaskDecl(
        name=task_name,
        args=[
            SVArg(name="consumer", dtype=slot.consumer_type),
            SVArg(name="comp", dtype="zsp_component"),
        ],
        body_lines=body,
    )


def _emit_sequential_inference(
    slot: InferenceSlot,
    consumer_constraints: Optional[List[str]] = None,
) -> List[str]:
    """Emit sequential inference pattern (buffer/state)."""
    lines: List[str] = []

    # Execute producer
    lines.append("// Execute inferred producer")
    lines.append("producer.pre_solve();")

    if consumer_constraints:
        with_body = "; ".join(consumer_constraints)
        lines.append(f"if (!producer.randomize() with {{ {with_body}; }})")
    else:
        lines.append("if (!producer.randomize())")
    lines.append('  $fatal(1, "inferred producer randomize failed");')
    lines.append("producer.post_solve();")
    lines.append("producer.body();")
    lines.append("")

    # Bind flow object
    lines.append("// Bind flow object from producer to consumer")
    # The actual field binding depends on the producer type, which is
    # dynamic at runtime. For SV-native inference we use a simplified
    # approach where the output field is known at generation time for
    # each candidate.
    if len(slot.candidates) == 1:
        _, _, out_field = slot.candidates[0]
        lines.append(f"consumer.{slot.consumer_field} = producer.{out_field};")
    else:
        # Multiple candidates may have different output field names.
        # Emit a case on producer_type to select the right field.
        lines.append("case (producer_type)")
        for type_id, sv_name, out_field in slot.candidates:
            lines.append(f"  {type_id}: begin")
            lines.append(f"    {sv_name} typed_p;")
            lines.append(f"    $cast(typed_p, producer);")
            lines.append(f"    consumer.{slot.consumer_field} = typed_p.{out_field};")
            lines.append(f"  end")
        lines.append("endcase")
    lines.append("")

    # Execute consumer with flow-object fields fixed
    lines.append("// Execute consumer with flow-object fields fixed")
    lines.append("consumer.pre_solve();")
    lines.append("if (!consumer.randomize())")
    lines.append('  $fatal(1, "consumer randomize failed");')
    lines.append("consumer.post_solve();")
    lines.append("consumer.body();")

    return lines


def _emit_stream_inference(
    slot: InferenceSlot,
    consumer_constraints: Optional[List[str]] = None,
) -> List[str]:
    """Emit concurrent inference pattern (stream)."""
    lines: List[str] = []

    lines.append(f"// Stream inference: fork producer alongside consumer")
    lines.append(f"zsp_stream_channel #({slot.flow_type}) _ch = new();")
    lines.append("")
    lines.append("fork")

    # Producer branch
    lines.append("  begin")
    lines.append("    producer.pre_solve();")
    if consumer_constraints:
        with_body = "; ".join(consumer_constraints)
        lines.append(f"    if (!producer.randomize() with {{ {with_body}; }})")
    else:
        lines.append("    if (!producer.randomize())")
    lines.append('      $fatal(1, "inferred producer randomize failed");')
    lines.append("    producer.post_solve();")
    lines.append("    producer.body();")
    # Put flow object into channel -- similar case logic as sequential
    if len(slot.candidates) == 1:
        _, _, out_field = slot.candidates[0]
        lines.append(f"    _ch.put(producer.{out_field});")
    else:
        lines.append("    case (producer_type)")
        for type_id, sv_name, out_field in slot.candidates:
            lines.append(f"      {type_id}: begin")
            lines.append(f"        {sv_name} typed_p;")
            lines.append(f"        $cast(typed_p, producer);")
            lines.append(f"        _ch.put(typed_p.{out_field});")
            lines.append(f"      end")
        lines.append("    endcase")
    lines.append("  end")

    # Consumer branch
    lines.append("  begin")
    lines.append(f"    _ch.get(consumer.{slot.consumer_field});")
    lines.append("    consumer.pre_solve();")
    lines.append("    if (!consumer.randomize())")
    lines.append('      $fatal(1, "consumer randomize failed");')
    lines.append("    consumer.post_solve();")
    lines.append("    consumer.body();")
    lines.append("  end")

    lines.append("join")

    return lines


# -----------------------------------------------------------------------
# DPI inference placeholder (Layer 2 -- deferred to Phase 8)
# -----------------------------------------------------------------------

def emit_dpi_inference_imports() -> List[str]:
    """Emit DPI import declarations for the inference engine.

    These are emitted when ``inference_mode`` is ``"dpi"`` or ``"full"``,
    but the actual DPI library implementation is deferred to Phase 8.

    Returns:
        SV import declaration lines.
    """
    return [
        'import "DPI-C" function int zsp_dpi_infer('
        '    int consumer_type_id, string unbound_field,'
        '    int comp_instance_id, int seed);',
        'import "DPI-C" function int    zsp_dpi_plan_length(int plan_id);',
        'import "DPI-C" function int    zsp_dpi_plan_action_type(int plan_id, int idx);',
        'import "DPI-C" function int    zsp_dpi_plan_ordering(int plan_id, int idx);',
        'import "DPI-C" function string zsp_dpi_plan_output_field(int plan_id, int idx);',
        'import "DPI-C" function string zsp_dpi_plan_input_field(int plan_id, int idx);',
        'import "DPI-C" function void   zsp_dpi_plan_destroy(int plan_id);',
    ]


def emit_dpi_inference_task(
    slot: InferenceSlot,
) -> SVTaskDecl:
    """Emit a DPI-based inference task for a complex slot.

    The task calls ``zsp_dpi_infer()`` to get a plan, then executes
    the plan's actions in order. This is a structural placeholder --
    the DPI library itself is built in Phase 8.

    Args:
        slot: The inference slot classified as COMPLEX.

    Returns:
        SVTaskDecl for the DPI inference task.
    """
    task_name = f"dpi_infer_and_execute_{slot.consumer_type}_{slot.consumer_field}"

    body: List[str] = []
    body.append(f'int plan = zsp_dpi_infer(0, "{slot.consumer_field}", 0, $urandom);')
    body.append("")
    body.append("if (plan < 0)")
    body.append(f'  $fatal(1, "DPI inference failed for '
                f'{slot.consumer_type}.{slot.consumer_field}");')
    body.append("")
    body.append("// Execute plan actions sequentially")
    body.append("for (int i = 0; i < zsp_dpi_plan_length(plan); i++) begin")
    body.append("  int act_type = zsp_dpi_plan_action_type(plan, i);")
    body.append("  zsp_action act = zsp_create_action(act_type, comp);")
    body.append("  act.pre_solve();")
    body.append("  if (!act.randomize())")
    body.append('    $fatal(1, "inferred action randomize failed");')
    body.append("  act.post_solve();")
    body.append("  act.body();")
    body.append("end")
    body.append("")
    body.append("// Execute consumer")
    body.append("consumer.pre_solve();")
    body.append("if (!consumer.randomize())")
    body.append('  $fatal(1, "consumer randomize failed");')
    body.append("consumer.post_solve();")
    body.append("consumer.body();")
    body.append("")
    body.append("zsp_dpi_plan_destroy(plan);")

    return SVTaskDecl(
        name=task_name,
        args=[
            SVArg(name="consumer", dtype=slot.consumer_type),
            SVArg(name="comp", dtype="zsp_component"),
        ],
        body_lines=body,
    )
