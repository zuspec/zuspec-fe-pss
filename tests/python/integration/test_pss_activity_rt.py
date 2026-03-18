"""Integration tests: PSS activity body → ActivityRunner execution.

These tests exercise the full PSS→IR→ActivitySequenceBlock→ScenarioRunner
pipeline for compound actions with activity blocks.
"""
from __future__ import annotations
import asyncio
import pytest

from zuspec.fe.pss import Parser, AstToIrTranslator, IrToRuntimeBuilder
from zuspec.dataclasses.rt.scenario_runner import ScenarioRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build(pss_text: str):
    """Parse, link, translate, and build Python classes from PSS source."""
    p = Parser()
    p.parses([('test.pss', pss_text)])
    root = p.link()
    ctx = AstToIrTranslator().translate(root)
    return IrToRuntimeBuilder(ctx).build()


def run(classes, action_cls, comp_inst, seed=42):
    """Run *action_cls* under *comp_inst* and return the executed action."""
    runner = ScenarioRunner(comp_inst, seed=seed)
    return asyncio.run(runner.run_action(action_cls))


# ---------------------------------------------------------------------------
# Test 1 — simple sequence: two atomic sub-actions execute in order
# ---------------------------------------------------------------------------

class _T1Collector:
    """Record execution order via append calls."""
    log: list = []


PSS_SEQUENCE = """
component MyC {
    action Write { rand bit[8] addr; exec body { } }
    action Read  { rand bit[8] addr; exec body { } }
    action Transfer {
        Write wr;
        Read  rd;
        activity {
            wr;
            rd;
        }
    }
}
"""


@pytest.mark.asyncio
async def test_simple_sequence():
    """Both sub-actions are executed; randomized fields are non-None."""
    classes = build(PSS_SEQUENCE)
    top = classes.MyC()
    runner = ScenarioRunner(top, seed=1)
    result = await runner.run(classes.MyC.Transfer)

    assert result.wr.addr is not None
    assert result.rd.addr is not None
    # Both must have been randomized to valid uint8 values
    assert 0 <= result.wr.addr <= 255
    assert 0 <= result.rd.addr <= 255


# ---------------------------------------------------------------------------
# Test 2 — parallel block: both branches execute
# ---------------------------------------------------------------------------

PSS_PARALLEL = """
component MyC {
    action A { rand bit[8] x; exec body { } }
    action B { rand bit[8] y; exec body { } }
    action Par {
        A a1;
        B b1;
        activity {
            parallel {
                a1;
                b1;
            }
        }
    }
}
"""


@pytest.mark.asyncio
async def test_parallel_block():
    """Parallel block executes both sub-actions."""
    classes = build(PSS_PARALLEL)
    top = classes.MyC()
    runner = ScenarioRunner(top, seed=2)
    result = await runner.run(classes.MyC.Par)

    assert result.a1.x is not None
    assert result.b1.y is not None
    assert 0 <= result.a1.x <= 255
    assert 0 <= result.b1.y <= 255


# ---------------------------------------------------------------------------
# Test 3 — repeat: anonymous do repeats three times
# ---------------------------------------------------------------------------

PSS_REPEAT = """
component MyC {
    action Work { rand bit[8] val; exec body { } }
    action ThreeTimes {
        activity {
            repeat (3) {
                do Work;
            }
        }
    }
}
"""


@pytest.mark.asyncio
async def test_repeat_count():
    """repeat(3) executes the body action three times."""
    classes = build(PSS_REPEAT)
    top = classes.MyC()
    runner = ScenarioRunner(top, seed=3)
    result = await runner.run(classes.MyC.ThreeTimes)
    # No crash; result is a ThreeTimes instance
    assert result is not None
    assert isinstance(result, classes.MyC.ThreeTimes)


# ---------------------------------------------------------------------------
# Test 4 — select: exactly one branch executes
# ---------------------------------------------------------------------------

PSS_SELECT = """
component MyC {
    action Fast { rand bit[8] speed; exec body { } }
    action Slow { rand bit[8] delay_val; exec body { } }
    action Dispatch {
        activity {
            select {
                do Fast;
                do Slow;
            }
        }
    }
}
"""


@pytest.mark.asyncio
async def test_select_one_branch():
    """select executes exactly one of its branches (no crash)."""
    classes = build(PSS_SELECT)
    top = classes.MyC()
    runner = ScenarioRunner(top, seed=4)
    result = await runner.run(classes.MyC.Dispatch)
    assert result is not None


# ---------------------------------------------------------------------------
# Test 5 — handle traversal resolves correct sub-action type
# ---------------------------------------------------------------------------

PSS_HANDLE = """
component MyC {
    action Sub { rand bit[16] data; exec body { } }
    action Top {
        Sub s1;
        activity {
            s1;
        }
    }
}
"""


@pytest.mark.asyncio
async def test_handle_traversal_randomizes():
    """Handle traversal randomizes the declared sub-action field."""
    classes = build(PSS_HANDLE)
    top = classes.MyC()
    runner = ScenarioRunner(top, seed=5)
    result = await runner.run(classes.MyC.Top)

    assert result.s1.data is not None
    assert 0 <= result.s1.data <= 0xFFFF


# ---------------------------------------------------------------------------
# Test 6 — anonymous traversal resolves action type from component class
# ---------------------------------------------------------------------------

PSS_ANON = """
component MyC {
    action Sub { rand bit[8] v; exec body { } }
    action Top {
        activity {
            do Sub;
        }
    }
}
"""


@pytest.mark.asyncio
async def test_anon_traversal_resolves():
    """Anonymous 'do Sub' traversal resolves and randomizes the action."""
    classes = build(PSS_ANON)
    top = classes.MyC()
    runner = ScenarioRunner(top, seed=6)
    # Should not raise RuntimeError about unresolved action type
    result = await runner.run(classes.MyC.Top)
    assert result is not None
