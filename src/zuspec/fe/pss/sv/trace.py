"""Trace macro emission helpers for generated SV code.

Provides functions that return SV statement lines invoking the
``ZSP_TRACE_*`` macros from ``zsp_rt_pkg``.  These are injected into
the activity lowering output at action traversals, resource operations,
and parallel/schedule/select entry/exit points.

Trace calls are controlled by the ``zsp_rt_verbosity`` level at
simulation time and add no overhead when verbosity is 0.
"""
from __future__ import annotations

from typing import List


def trace_action(action_type: str, comp_expr: str) -> str:
    """Emit a ``ZSP_TRACE_ACTION`` macro call.

    Inserted at each action traversal.
    """
    return f'`ZSP_TRACE_ACTION("{action_type}", {comp_expr}.get_full_name());'


def trace_resource(op: str, pool_expr: str, id_expr: str) -> str:
    """Emit a ``ZSP_TRACE_RESOURCE`` macro call.

    Inserted at lock/unlock/share/unshare operations.

    Args:
        op: Operation name (``"LOCK"``, ``"UNLOCK"``, ``"SHARE"``, ``"UNSHARE"``).
        pool_expr: SV expression for the pool.
        id_expr: SV expression for the instance id.
    """
    return f'`ZSP_TRACE_RESOURCE("{op}", "{pool_expr}", {id_expr});'


def trace_msg(msg: str) -> str:
    """Emit a ``ZSP_TRACE`` macro call with a message.

    Used at parallel/schedule/select entry/exit points.
    """
    return f'`ZSP_TRACE("{msg}");'


def trace_parallel_enter(label: str = "parallel") -> str:
    """Trace entering a parallel block."""
    return trace_msg(f"{label} enter")


def trace_parallel_exit(label: str = "parallel") -> str:
    """Trace exiting a parallel block."""
    return trace_msg(f"{label} exit")


def trace_schedule_enter(label: str = "schedule") -> str:
    """Trace entering a schedule block."""
    return trace_msg(f"{label} enter")


def trace_schedule_exit(label: str = "schedule") -> str:
    """Trace exiting a schedule block."""
    return trace_msg(f"{label} exit")


def trace_select_enter(label: str = "select") -> str:
    """Trace entering a select block."""
    return trace_msg(f"{label} enter")


def trace_select_exit(label: str = "select") -> str:
    """Trace exiting a select block."""
    return trace_msg(f"{label} exit")


def wrap_traversal_with_trace(
    action_type: str,
    comp_expr: str,
    traversal_lines: List[str],
) -> List[str]:
    """Wrap a traversal's SV lines with trace macro calls.

    Inserts ``ZSP_TRACE_ACTION`` before the traversal block.

    Args:
        action_type: Human-readable action type name for the trace.
        comp_expr: SV expression for the component.
        traversal_lines: The existing traversal SV lines.

    Returns:
        New list with trace line prepended.
    """
    return [trace_action(action_type, comp_expr)] + traversal_lines


def wrap_resource_ops_with_trace(
    resource_lines: List[str],
    op: str,
    pool_expr: str,
    id_expr: str,
) -> List[str]:
    """Prepend a resource trace call before resource operation lines.

    Args:
        resource_lines: The existing resource operation SV lines.
        op: Operation name for the trace.
        pool_expr: Pool expression for the trace.
        id_expr: Instance id expression for the trace.

    Returns:
        New list with trace line prepended.
    """
    return [trace_resource(op, pool_expr, id_expr)] + resource_lines
