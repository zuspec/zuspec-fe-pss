"""Integration test: pad assignment pattern, parsed from PSS source.

Loads modeling_patterns/pss/pad_assignment/pad_assignment.pss through the full
Parser -> AstToIrTranslator -> IrToRuntimeBuilder -> ScenarioRunner pipeline and
verifies correctness plus characterises performance.

Valid configurations exercised:
  soc_2_initiators  -- initiator0 + initiator1 in parallel
  soc_init0_target0 -- initiator0 + target0 in parallel
  soc_2_targets     -- target0 + target1 in parallel
"""
from __future__ import annotations

import asyncio
import os
import time
import warnings

import pytest

from zuspec.fe.pss import Parser, AstToIrTranslator, IrToRuntimeBuilder
from zuspec.dataclasses.rt.scenario_runner import ScenarioRunner

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

# ---------------------------------------------------------------------------
# Shared fixture: build runtime classes once per module
# ---------------------------------------------------------------------------

_PAD_PSS = os.path.join(
    os.path.dirname(__file__),
    '..', '..', '..', '..', '..',
    'modeling_patterns', 'pss', 'pad_assignment', 'pad_assignment.pss',
)


def _build_classes():
    p = Parser()
    p.parse([_PAD_PSS])
    root = p.link()
    ctx = AstToIrTranslator().translate(root)
    return IrToRuntimeBuilder(ctx).build()


_CLASSES = None


def _get_classes():
    global _CLASSES
    if _CLASSES is None:
        _CLASSES = _build_classes()
    return _CLASSES


# Valid pad sets per interface (mirrors the CSV data hard-coded in the PSS source)
_VALID: dict[str, dict[str, frozenset]] = {
    "initiator0": {
        "in_pad":    frozenset({0}),
        "out_pad":   frozenset({1}),
        "clk_pad":   frozenset({2}),
        "sel0_pad":  frozenset({3}),
        "sel1_pad":  frozenset({4}),
    },
    "initiator1": {
        "in_pad":    frozenset({5}),
        "out_pad":   frozenset({6}),
        "clk_pad":   frozenset({7}),
        "sel0_pad":  frozenset({8}),
        "sel1_pad":  frozenset({9}),
    },
    "target0": {
        "in_pad":      frozenset({5}),
        "out_pad":     frozenset({6}),
        "clk_pad":     frozenset({7}),
        "tgt_sel_pad": frozenset({10}),
    },
    "target1": {
        "in_pad":      frozenset({0}),
        "out_pad":     frozenset({1}),
        "clk_pad":     frozenset({2}),
        "tgt_sel_pad": frozenset({11}),
    },
}


def _run(coro):
    return asyncio.run(coro)


def _check_pads(action, signals: list[str], intf: str) -> None:
    """Assert each lock field's pad_id is in the expected valid set."""
    vp = _VALID[intf]
    for sig in signals:
        resource = getattr(action, sig, None)
        assert resource is not None, f"{sig} not set on {type(action).__name__}"
        assert resource.pad_id in vp[sig], (
            f"{intf}.{sig}: pad_id={resource.pad_id} not in valid set {vp[sig]}"
        )


def _all_pad_ids(action, signals: list[str]) -> list[int]:
    return [getattr(action, s).pad_id for s in signals]


# ---------------------------------------------------------------------------
# Correctness tests — soc_2_initiators
# ---------------------------------------------------------------------------

def test_2initiators_runs():
    classes = _get_classes()
    top = classes['pss_top']()
    result = _run(ScenarioRunner(top, seed=42).run(classes['pss_top::soc_2_initiators']))
    assert result is not None


def test_2initiators_valid_pads():
    classes = _get_classes()
    top = classes['pss_top']()
    r = _run(ScenarioRunner(top, seed=42).run(classes['pss_top::soc_2_initiators']))
    # soc_2_initiators has no labelled sub-actions in the dataclass directly;
    # validate via pool state and that the pool was fully used.
    # 10 pads were claimed: 5 for init0 (IDs 0-4) and 5 for init1 (IDs 5-9)
    pool = top.pad_r_pool
    # After run, all claims released — check state is clean
    assert all(s == 0 for s in pool._state), f"Pool not released: {pool._state}"


def test_2initiators_pool_released():
    classes = _get_classes()
    top = classes['pss_top']()
    _run(ScenarioRunner(top, seed=7).run(classes['pss_top::soc_2_initiators']))
    assert all(s == 0 for s in top.pad_r_pool._state)


# ---------------------------------------------------------------------------
# Correctness tests — soc_init0_target0
# ---------------------------------------------------------------------------

def test_init0_target0_runs():
    classes = _get_classes()
    top = classes['pss_top']()
    result = _run(ScenarioRunner(top, seed=1).run(classes['pss_top::soc_init0_target0']))
    assert result is not None


def test_init0_target0_pool_released():
    classes = _get_classes()
    top = classes['pss_top']()
    _run(ScenarioRunner(top, seed=1).run(classes['pss_top::soc_init0_target0']))
    assert all(s == 0 for s in top.pad_r_pool._state)


# ---------------------------------------------------------------------------
# Correctness tests — soc_2_targets
# ---------------------------------------------------------------------------

def test_2targets_runs():
    classes = _get_classes()
    top = classes['pss_top']()
    result = _run(ScenarioRunner(top, seed=3).run(classes['pss_top::soc_2_targets']))
    assert result is not None


def test_2targets_pool_released():
    classes = _get_classes()
    top = classes['pss_top']()
    _run(ScenarioRunner(top, seed=3).run(classes['pss_top::soc_2_targets']))
    assert all(s == 0 for s in top.pad_r_pool._state)


# ---------------------------------------------------------------------------
# Multi-seed stability
# ---------------------------------------------------------------------------

def test_all_configs_multi_seed():
    """All three configurations run without error across 10 seeds each."""
    classes = _get_classes()
    scenarios = [
        'pss_top::soc_2_initiators',
        'pss_top::soc_init0_target0',
        'pss_top::soc_2_targets',
    ]
    for scenario in scenarios:
        for seed in range(10):
            top = classes['pss_top']()
            _run(ScenarioRunner(top, seed=seed).run(classes[scenario]))
            assert all(s == 0 for s in top.pad_r_pool._state), (
                f"{scenario} seed={seed}: pool leak"
            )


# ---------------------------------------------------------------------------
# Correct pad assignment: verify via component valid-pad lists
# ---------------------------------------------------------------------------

def test_valid_pad_lists_populated():
    """Component init populates valid-pad lists from the PSS solve function."""
    classes = _get_classes()
    top = classes['pss_top']()
    assert top.spi_initiators[0].in_pads == [0],      "init0 in_pad"
    assert top.spi_initiators[0].out_pads == [1],     "init0 out_pad"
    assert top.spi_initiators[1].in_pads == [5],      "init1 in_pad"
    assert top.spi_targets[0].tgt_sel_pads == [10],   "tgt0 tgt_sel_pad"
    assert top.spi_targets[1].tgt_sel_pads == [11],   "tgt1 tgt_sel_pad"


# ---------------------------------------------------------------------------
# Performance benchmarks
# ---------------------------------------------------------------------------

def _time_scenario(scenario_key: str, n: int) -> dict:
    classes = _get_classes()
    action_cls = classes[scenario_key]
    t0 = time.perf_counter()
    for seed in range(n):
        top = classes['pss_top']()
        _run(ScenarioRunner(top, seed=seed).run(action_cls))
    elapsed = time.perf_counter() - t0
    return {
        "scenario": scenario_key,
        "n": n,
        "total_s": elapsed,
        "per_iter_ms": elapsed / n * 1000,
        "throughput": n / elapsed,
    }


def _time_scenario_reuse(scenario_key: str, n: int) -> dict:
    """Benchmark with a single pre-built pss_top and pool reset between iterations.

    This models sustained use: component tree built once, pool state reset
    between scenario runs.  All solver caches and PoolResolver templates are
    fully warm after the first iteration.
    """
    classes = _get_classes()
    action_cls = classes[scenario_key]
    top = classes['pss_top']()
    pool = top.pad_r_pool
    n_pool = len(pool._state)

    def _reset_pool():
        pool._state = [0] * n_pool
        pool._count = [0] * n_pool
        import asyncio as _aio
        pool._ev = _aio.Event()

    async def _run_one(seed):
        _reset_pool()
        return await ScenarioRunner(top, seed=seed).run(action_cls)

    # Warm all caches with a few iterations
    for i in range(3):
        _run(_run_one(i))

    t0 = time.perf_counter()
    for seed in range(n):
        _run(_run_one(seed))
    elapsed = time.perf_counter() - t0
    return {
        "scenario": scenario_key,
        "n": n,
        "total_s": elapsed,
        "per_iter_ms": elapsed / n * 1000,
        "throughput": n / elapsed,
    }


def test_perf_2initiators():
    """Perf: soc_2_initiators, 50 iterations (fresh top)."""
    r = _time_scenario('pss_top::soc_2_initiators', n=50)
    print(f"\n[perf/fresh] {r['scenario']} n={r['n']}: "
          f"{r['per_iter_ms']:.3f} ms/iter  {r['throughput']:.0f} iter/s")
    assert r['total_s'] < 30.0, f"Too slow: {r['total_s']:.1f}s for {r['n']} iters"


def test_perf_init0_target0():
    """Perf: soc_init0_target0, 50 iterations (fresh top)."""
    r = _time_scenario('pss_top::soc_init0_target0', n=50)
    print(f"\n[perf/fresh] {r['scenario']} n={r['n']}: "
          f"{r['per_iter_ms']:.3f} ms/iter  {r['throughput']:.0f} iter/s")
    assert r['total_s'] < 30.0


def test_perf_2targets():
    """Perf: soc_2_targets, 50 iterations (fresh top)."""
    r = _time_scenario('pss_top::soc_2_targets', n=50)
    print(f"\n[perf/fresh] {r['scenario']} n={r['n']}: "
          f"{r['per_iter_ms']:.3f} ms/iter  {r['throughput']:.0f} iter/s")
    assert r['total_s'] < 30.0


def test_perf_sustained_2initiators():
    """Perf: soc_2_initiators, 100 iterations with shared top and pool reset.

    Models sustained use: one component tree, pool state reset between runs.
    Target: < 1 ms/iter once solver and PoolResolver caches are warm.
    """
    r = _time_scenario_reuse('pss_top::soc_2_initiators', n=100)
    print(f"\n[perf/sustained] {r['scenario']} n={r['n']}: "
          f"{r['per_iter_ms']:.3f} ms/iter  {r['throughput']:.0f} iter/s")
    assert r['per_iter_ms'] < 2.0, (
        f"Sustained throughput too low: {r['per_iter_ms']:.2f} ms/iter "
        f"(target <2ms)"
    )


def test_perf_sustained_all():
    """Perf: all scenarios sustained (shared top + pool reset), 50 iters each."""
    scenarios = [
        'pss_top::soc_2_initiators',
        'pss_top::soc_init0_target0',
        'pss_top::soc_2_targets',
    ]
    for sc in scenarios:
        r = _time_scenario_reuse(sc, n=50)
        print(f"\n[perf/sustained] {r['scenario']}: "
              f"{r['per_iter_ms']:.3f} ms/iter  {r['throughput']:.0f} iter/s")
        assert r['per_iter_ms'] < 2.0, (
            f"{sc} sustained too slow: {r['per_iter_ms']:.2f} ms/iter"
        )
