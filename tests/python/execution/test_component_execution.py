"""Execution tests: component init_down and action constraint solving.

Phase 2: verify that exec init_down {} runs at component instantiation time
         (mapped to __post_init__ by IrToRuntimeBuilder).

Phase 3: verify that rand fields on actions are constrained correctly when
         an action is executed via ScenarioRunner.
"""
from __future__ import annotations
import asyncio
import pytest

from zuspec.fe.pss import Parser, AstToIrTranslator, IrToRuntimeBuilder
from zuspec.dataclasses.rt.scenario_runner import ScenarioRunner


def build(pss_text: str):
    p = Parser()
    p.parses([('test.pss', pss_text)])
    root = p.link()
    ctx = AstToIrTranslator().translate(root)
    return IrToRuntimeBuilder(ctx).build()


# ---------------------------------------------------------------------------
# Phase 2 — init_down runs at instantiation time
# ---------------------------------------------------------------------------

def test_init_down_sets_field_on_instantiation():
    """exec init_down { val = 99; } must run when the component is created."""
    classes = build("""
        component MyC {
            bit[32] val;
            exec init_down { val = 99; }
            action MyA { exec body { } }
        }
    """)
    comp = classes.MyC()
    assert comp.val == 99, f"Expected val=99 after init_down, got {comp.val}"


def test_init_down_nested_child():
    """Parent init_down can write into a child component's field."""
    classes = build("""
        component Child {
            bit[32] val;
            action MyA { exec body { } }
        }
        component Parent {
            Child c;
            exec init_down { c.val = 42; }
            action MyA { exec body { } }
        }
    """)
    parent = classes.Parent()
    assert parent.c.val == 42, f"Expected c.val=42 after parent init_down, got {parent.c.val}"


def test_init_down_multiple_children():
    """init_down can write distinct values into multiple children."""
    classes = build("""
        component Worker {
            bit[32] id;
            action MyA { exec body { } }
        }
        component Top {
            Worker w1;
            Worker w2;
            exec init_down {
                w1.id = 1;
                w2.id = 2;
            }
            action MyA { exec body { } }
        }
    """)
    top = classes.Top()
    assert top.w1.id == 1, f"Expected w1.id=1, got {top.w1.id}"
    assert top.w2.id == 2, f"Expected w2.id=2, got {top.w2.id}"


# ---------------------------------------------------------------------------
# Phase 3 — action constraints are satisfied after execution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_action_constraint_ordering():
    """rand fields on an action must satisfy constraint x < y after execution."""
    classes = build("""
        component MyC {
            action MyA {
                rand bit[8] x;
                rand bit[8] y;
                constraint x < y;
                exec body { }
            }
        }
    """)
    comp = classes.MyC()
    for seed in range(10):
        runner = ScenarioRunner(comp, seed=seed)
        result = await runner.run(classes.MyC.MyA)
        assert result.x < result.y, (
            f"seed={seed}: constraint x < y violated: x={result.x}, y={result.y}"
        )


@pytest.mark.asyncio
async def test_action_constraint_upper_bound():
    """Action rand field constraint limits value to a sub-range."""
    classes = build("""
        component MyC {
            action MyA {
                rand bit[8] burst;
                constraint burst <= 16;
                exec body { }
            }
        }
    """)
    comp = classes.MyC()
    for seed in range(15):
        runner = ScenarioRunner(comp, seed=seed)
        result = await runner.run(classes.MyC.MyA)
        assert result.burst <= 16, (
            f"seed={seed}: burst={result.burst} violates constraint burst <= 16"
        )


@pytest.mark.asyncio
async def test_action_constraint_alignment():
    """Action rand field constraint enforces alignment."""
    classes = build("""
        component MyC {
            action MyA {
                rand bit[8] addr;
                constraint addr % 4 == 0;
                exec body { }
            }
        }
    """)
    comp = classes.MyC()
    for seed in range(15):
        runner = ScenarioRunner(comp, seed=seed)
        result = await runner.run(classes.MyC.MyA)
        assert result.addr % 4 == 0, (
            f"seed={seed}: addr={result.addr} not 4-byte aligned"
        )
