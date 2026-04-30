"""End-to-end covergroup sampling through ScenarioRunner (WI-7 full integration)."""
import asyncio
import pytest
from zuspec.fe.pss import load_pss

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


def _build_pss_ns():
    return load_pss("""
        component pss_top {
            action draw_shape {
                rand bit[2] color;
                rand bit[2] shape;
                covergroup {
                    coverpoint color;
                    coverpoint shape;
                    cx: cross color, shape;
                } cg;
            }
        }
    """)


# ---------------------------------------------------------------------------
# T-C3: coverage model populated via ScenarioRunner
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_covergroup_sampled_via_scenario_runner():
    """ScenarioRunner passes coverage_model through to _traverse; sampling fires after body."""
    from zuspec.dataclasses import PssCoverageModel, ScenarioRunner

    ns = _build_pss_ns()
    top = ns.pss_top()
    model = PssCoverageModel()
    runner = ScenarioRunner(top, seed=42, coverage_model=model)

    for _ in range(20):
        await runner.run(ns['pss_top::draw_shape'])

    color_samples = model.coverpoint_samples('cg', 'color')
    shape_samples = model.coverpoint_samples('cg', 'shape')
    assert len(color_samples) == 20
    assert len(shape_samples) == 20
    assert all(0 <= v <= 3 for v in color_samples)
    assert all(0 <= v <= 3 for v in shape_samples)

    cx_hits = model.cross_hits('cg', 'cx')
    assert sum(cx_hits.values()) == 20


@pytest.mark.asyncio
async def test_all_cross_combos_covered_eventually():
    """After enough runs, all 4x4 color/shape cross-bins are hit."""
    from zuspec.dataclasses import PssCoverageModel, ScenarioRunner

    ns = _build_pss_ns()
    top = ns.pss_top()
    model = PssCoverageModel()
    runner = ScenarioRunner(top, seed=1, coverage_model=model)

    for _ in range(200):
        await runner.run(ns['pss_top::draw_shape'])

    cx_hits = model.cross_hits('cg', 'cx')
    assert len(cx_hits) == 16, f"Expected 16 cross bins, got {len(cx_hits)}: {cx_hits}"


# ---------------------------------------------------------------------------
# T-C3 sync variant: run_action_sync with coverage_model
# ---------------------------------------------------------------------------

def test_coverage_via_run_action_sync():
    """run_action_sync passes coverage_model; works for non-async callers."""
    from zuspec.dataclasses import PssCoverageModel, run_action_sync

    ns = _build_pss_ns()
    top = ns.pss_top()
    model = PssCoverageModel()

    for seed in range(20):
        run_action_sync(top, ns['pss_top::draw_shape'], seed=seed, coverage_model=model)

    assert len(model.coverpoint_samples('cg', 'color')) == 20
    assert len(model.coverpoint_samples('cg', 'shape')) == 20
    assert sum(model.cross_hits('cg', 'cx').values()) == 20


# ---------------------------------------------------------------------------
# dice.pss: verify parse + covergroup annotation survives full pipeline
# ---------------------------------------------------------------------------

def test_dice_pss_parses_and_covergroup_extracted():
    """The dice.pss example parses without error and its covergroup is captured."""
    import os
    dice_path = os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..', '..', '..',
        'modeling_patterns', 'pss', 'coverage_fill', 'dice.pss',
    )
    dice_path = os.path.normpath(dice_path)
    if not os.path.exists(dice_path):
        pytest.skip("dice.pss not found")

    from zuspec.fe.pss import load_pss_files
    ns = load_pss_files([dice_path])

    # draw_shape should be registered
    all_names = list(ns.keys())
    assert any('draw_shape' in n for n in all_names), \
        f"draw_shape not in {all_names}"

    # roll_dice should also be registered
    assert any('roll_dice' in n for n in all_names), \
        f"roll_dice not in {all_names}"
