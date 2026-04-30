"""Runtime tests for covergroup sampling after action body/activity (WI-7)."""
import pytest
from zuspec.fe.pss import load_pss, Parser
from zuspec.fe.pss.ast_to_ir import AstToIrTranslator
from zuspec.fe.pss.ir_to_runtime import IrToRuntimeBuilder
from zuspec.dataclasses.rt.coverage_model import PssCoverageModel, eval_cover_expr
from zuspec.dataclasses.rt.activity_runner import _sample_covergroups
from zuspec.dataclasses import ir as zdc_ir

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


# ---------------------------------------------------------------------------
# Unit: eval_cover_expr
# ---------------------------------------------------------------------------

def test_eval_cover_expr_simple_field():
    class FakeAction:
        color = 42

    expr = zdc_ir.ExprAttribute(value=zdc_ir.TypeExprRefSelf(), attr='color')
    assert eval_cover_expr(expr, FakeAction()) == 42


def test_eval_cover_expr_missing_field():
    class FakeAction:
        pass

    expr = zdc_ir.ExprAttribute(value=zdc_ir.TypeExprRefSelf(), attr='shape')
    assert eval_cover_expr(expr, FakeAction()) is None


# ---------------------------------------------------------------------------
# Unit: PssCoverageModel
# ---------------------------------------------------------------------------

def test_model_sample_and_retrieve():
    model = PssCoverageModel()
    model.sample('cg1', 'cp_color', 0)
    model.sample('cg1', 'cp_color', 1)
    model.sample('cg1', 'cp_color', 2)
    assert model.coverpoint_samples('cg1', 'cp_color') == [0, 1, 2]
    assert model.last_value('cg1', 'cp_color') == 2


def test_model_cross_hits():
    model = PssCoverageModel()
    model.sample('cg', 'color', 0)
    model.sample('cg', 'shape', 1)
    model.sample_cross('cg', 'cx', (0, 1))
    model.sample('cg', 'color', 0)
    model.sample('cg', 'shape', 1)
    model.sample_cross('cg', 'cx', (0, 1))
    model.sample('cg', 'color', 1)
    model.sample('cg', 'shape', 2)
    model.sample_cross('cg', 'cx', (1, 2))
    hits = model.cross_hits('cg', 'cx')
    assert hits[(0, 1)] == 2
    assert hits[(1, 2)] == 1


def test_model_empty_retrieval():
    model = PssCoverageModel()
    assert model.coverpoint_samples('missing', 'cp') == []
    assert model.cross_hits('missing', 'cx') == {}
    assert model.last_value('missing', 'cp') is None


# ---------------------------------------------------------------------------
# Integration: covergroup IR populates __pss_covergroups__ on action class
# ---------------------------------------------------------------------------

def test_covergroup_ir_has_pss_covergroups():
    """__pss_covergroups__ is attached to the generated action class."""
    pss = """
    component pss_top {
        action draw_shape {
            rand int color;
            rand int shape;
            covergroup {
                coverpoint color;
                coverpoint shape;
                cx: cross color, shape;
            } cg;
        }
    }
    """
    parser = Parser()
    parser.parses([('t.pss', pss)])
    root = parser.link()
    ctx = AstToIrTranslator().translate(root, annotations=parser.annotations)
    ns = IrToRuntimeBuilder(ctx).build()
    action_cls = ns['pss_top::draw_shape']
    cgs = getattr(action_cls, '__pss_covergroups__', [])
    assert len(cgs) == 1
    cg = cgs[0]
    assert cg.instance_name == 'cg'
    assert len(cg.coverpoints) == 2
    assert len(cg.crosses) == 1


# ---------------------------------------------------------------------------
# Integration: _sample_covergroups correctly samples into PssCoverageModel
# ---------------------------------------------------------------------------

def test_covergroup_sampled_after_randomize():
    """Covergroup values are sampled when _sample_covergroups is called."""
    pss = """
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
    """
    parser = Parser()
    parser.parses([('t.pss', pss)])
    root = parser.link()
    ctx_ir = AstToIrTranslator().translate(root, annotations=parser.annotations)
    ns = IrToRuntimeBuilder(ctx_ir).build()

    from zuspec.dataclasses import randomize
    action_cls = ns['pss_top::draw_shape']
    model = PssCoverageModel()

    for seed in range(20):
        action = action_cls()
        randomize(action, seed=seed)
        _sample_covergroups(action_cls, action, model)

    color_samples = model.coverpoint_samples('cg', 'color')
    shape_samples = model.coverpoint_samples('cg', 'shape')
    assert len(color_samples) == 20
    assert len(shape_samples) == 20
    assert all(0 <= v <= 3 for v in color_samples), f"bad color values: {color_samples}"
    assert all(0 <= v <= 3 for v in shape_samples), f"bad shape values: {shape_samples}"

    cx_hits = model.cross_hits('cg', 'cx')
    assert len(cx_hits) > 0, "no cross hits recorded"
    assert sum(cx_hits.values()) == 20


def test_covergroup_all_color_shape_combos_eventually_covered():
    """After many samples, all 4x4 color/shape combinations appear."""
    pss = """
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
    """
    parser = Parser()
    parser.parses([('t.pss', pss)])
    root = parser.link()
    ctx_ir = AstToIrTranslator().translate(root, annotations=parser.annotations)
    ns = IrToRuntimeBuilder(ctx_ir).build()

    from zuspec.dataclasses import randomize
    action_cls = ns['pss_top::draw_shape']
    model = PssCoverageModel()

    for seed in range(200):
        action = action_cls()
        randomize(action, seed=seed)
        _sample_covergroups(action_cls, action, model)

    cx_hits = model.cross_hits('cg', 'cx')
    # With 200 samples across a 4x4 grid, all 16 combinations should appear
    assert len(cx_hits) == 16, f"Expected 16 combos, got {len(cx_hits)}: {cx_hits}"
