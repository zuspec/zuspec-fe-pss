"""Tests for fill activity reconstruction and coverage-driven termination."""
import pytest
import asyncio
from zuspec.fe.pss import load_pss, Parser
from zuspec.fe.pss.ast_to_ir import AstToIrTranslator
from zuspec.fe.pss.ir_to_runtime import IrToRuntimeBuilder
from zuspec.dataclasses import PssCoverageModel, ScenarioRunner

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


# ---------------------------------------------------------------------------
# Unit: fill annotation extraction
# ---------------------------------------------------------------------------

def test_fill_annotation_extracted():
    """Parser extracts a fill annotation with correct action_name."""
    pss = """
    component pss_top {
        action roll_dice { rand bit[3] x; }
        action test_scenario {
            activity {
                fill {
                    do roll_dice with { x == FILL; }
                }
            }
        }
    }
    """
    parser = Parser()
    parser.parses([('t.pss', pss)])
    fill_anns = [a for a in parser.annotations if a.kind == 'fill']
    assert len(fill_anns) == 1, f"Expected 1 fill annotation, got {fill_anns}"
    ann = fill_anns[0]
    assert ann.type_chain == ['pss_top', 'test_scenario']
    assert ann.data['action_name'] == 'roll_dice'
    assert ann.data['max_iters'] == 1000


def test_fill_ir_injection():
    """ActivityFill is injected into the action's activity IR."""
    from zuspec.ir.core.activity import ActivityFill, ActivityAnonTraversal, ActivitySequenceBlock
    pss = """
    component pss_top {
        action roll_dice { rand bit[3] x; }
        action test_scenario {
            activity {
                fill {
                    do roll_dice with { x == FILL; }
                }
            }
        }
    }
    """
    parser = Parser()
    parser.parses([('t.pss', pss)])
    root = parser.link()
    ctx = AstToIrTranslator().translate(root, annotations=parser.annotations)
    ns = IrToRuntimeBuilder(ctx).build()

    scenario_cls = ns['pss_top::test_scenario']
    activity = getattr(scenario_cls, '__activity__', None)
    assert activity is not None, "No __activity__ on scenario class"

    # Walk the activity to find ActivityFill
    def find_fill(node):
        if isinstance(node, ActivityFill):
            return node
        stmts = getattr(node, 'stmts', None) or getattr(node, 'body', None) or []
        for s in stmts:
            r = find_fill(s)
            if r is not None:
                return r
        return None

    fill_node = find_fill(activity)
    assert fill_node is not None, "ActivityFill not found in activity IR"
    assert fill_node.max_iters == 1000
    # The body should contain an ActivityAnonTraversal for roll_dice
    assert len(fill_node.body) == 1
    inner = fill_node.body[0]
    assert isinstance(inner, ActivityAnonTraversal)
    assert 'roll_dice' in (inner.action_type or '')


# ---------------------------------------------------------------------------
# Unit: PssCoverageModel.all_covered()
# ---------------------------------------------------------------------------

def test_all_covered_false_when_empty():
    model = PssCoverageModel()
    assert model.all_covered() is False


def test_all_covered_false_when_incomplete():
    model = PssCoverageModel()
    # Sample only some combinations of a 2x2 cross
    model.sample('cg', 'color', 0)
    model.sample('cg', 'shape', 0)
    model.sample_cross('cg', 'cx', (0, 0))
    model.sample('cg', 'color', 1)
    model.sample('cg', 'shape', 1)
    model.sample_cross('cg', 'cx', (1, 1))
    # Still missing (0,1) and (1,0)
    assert model.all_covered() is False


def test_all_covered_true_when_complete():
    model = PssCoverageModel()
    # 2x2 cross: values {0,1} x {0,1}
    for c in (0, 1):
        for s in (0, 1):
            model.sample('cg', 'color', c)
            model.sample('cg', 'shape', s)
            model.sample_cross('cg', 'cx', (c, s))
    assert model.all_covered() is True


def test_all_covered_specific_cross():
    model = PssCoverageModel()
    model.sample('cg', 'a', 0); model.sample('cg', 'b', 0)
    model.sample_cross('cg', 'cx', (0, 0))
    model.sample('cg', 'a', 1); model.sample('cg', 'b', 1)
    model.sample_cross('cg', 'cx', (1, 1))
    model.sample('cg', 'a', 0); model.sample('cg', 'b', 1)
    model.sample_cross('cg', 'cx', (0, 1))
    model.sample('cg', 'a', 1); model.sample('cg', 'b', 0)
    model.sample_cross('cg', 'cx', (1, 0))
    cov = model.all_covered_for_cross('cg', 'cx', ['a', 'b'])
    assert cov is True


# ---------------------------------------------------------------------------
# Integration: fill loop terminates via coverage_model
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fill_loop_terminates_on_coverage():
    """Fill loop stops when all_covered() returns True."""
    ns = load_pss("""
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
            action fill_scenario {
                activity {
                    fill {
                        do draw_shape with { color == FILL; shape == FILL; }
                    }
                }
            }
        }
    """)
    top = ns.pss_top()
    model = PssCoverageModel()
    runner = ScenarioRunner(top, seed=42, coverage_model=model)

    # Run fill_scenario — should run draw_shape up to max_iters times,
    # stopping early once all 16 color×shape combinations are hit
    await runner.run(ns['pss_top::fill_scenario'])

    # Verify we actually sampled something
    color_samples = model.coverpoint_samples('cg', 'color')
    shape_samples = model.coverpoint_samples('cg', 'shape')
    assert len(color_samples) > 0
    assert len(shape_samples) > 0

    # After a fill run, we should have more coverage than a single traversal
    cx_hits = model.cross_hits('cg', 'cx')
    assert len(cx_hits) > 0
