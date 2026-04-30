"""End-to-end test for 01-HelloWorld example.

Exercises the full PSS-text-to-execution pipeline from example.pss:
  Parser -> AstToIrTranslator -> IrToRuntimeBuilder -> ScenarioRunner
"""
from __future__ import annotations
import asyncio
import os
import warnings

import pytest

from zuspec.fe.pss import Parser, AstToIrTranslator, IrToRuntimeBuilder
from zuspec.dataclasses.rt.scenario_runner import ScenarioRunner

EXAMPLE_PSS = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..', '..',
    '01-HelloWorld', 'example.pss',
)

# Suppress warnings from skipped constraints on unbound flow inputs
pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


def _build():
    p = Parser()
    p.parse([EXAMPLE_PSS])
    root = p.link()
    ctx = AstToIrTranslator().translate(root)
    return IrToRuntimeBuilder(ctx).build()


@pytest.mark.anyio
async def test_entry_a_prints_world_a(capsys):
    """entry_a infers a producer, executes world_a, and prints 'world_a'."""
    classes = _build()
    top = classes.pss_top()
    runner = ScenarioRunner(top, seed=42)
    result = await runner.run(classes['pss_top::entry_a'])
    out = capsys.readouterr().out
    assert "world_a" in out, f"Expected 'world_a' in output, got: {out!r}"


@pytest.mark.anyio
async def test_entry_a_runs_multiple_seeds():
    """entry_a runs without error across several seeds."""
    classes = _build()
    for seed in range(10):
        top = classes.pss_top()
        runner = ScenarioRunner(top, seed=seed)
        result = await runner.run(classes['pss_top::entry_a'])
        assert result is not None
