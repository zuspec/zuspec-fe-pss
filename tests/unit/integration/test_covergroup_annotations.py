"""Tests for covergroup annotation extraction and IR injection."""
import pytest
from zuspec.fe.pss import (
    load_pss, Parser, PssAnnotation,
    _parse_covergroup_body, _remove_covergroup_blocks,
)

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


# ---------------------------------------------------------------------------
# Unit: covergroup text removal
# ---------------------------------------------------------------------------

def test_remove_covergroup_simple():
    src = "action a { rand int x; covergroup { coverpoint x; } cg; }"
    out = _remove_covergroup_blocks(src)
    assert 'covergroup' not in out
    assert '// @ZSP_COV: cg' in out
    assert 'rand int x' in out   # non-covergroup content preserved


def test_remove_covergroup_with_cross():
    src = "action a { rand int x; covergroup { coverpoint x; coverpoint y; cx: cross x, y; } cg; }"
    out = _remove_covergroup_blocks(src)
    assert 'covergroup' not in out
    assert '// @ZSP_COV: cg' in out


def test_remove_preserves_comments():
    src = "// covergroup in comment\naction a { rand int x; }"
    out = _remove_covergroup_blocks(src)
    assert '// covergroup in comment' in out


# ---------------------------------------------------------------------------
# Unit: covergroup body parser
# ---------------------------------------------------------------------------

def test_parse_body_simple_coverpoints():
    body = "coverpoint color ; coverpoint shape ;"
    cps, cxs = _parse_covergroup_body(body)
    assert len(cps) == 2
    assert cxs == []
    names = {cp['name'] for cp in cps}
    assert 'color' in names
    assert 'shape' in names


def test_parse_body_named_coverpoints():
    body = "c : coverpoint color; s : coverpoint shape;"
    cps, cxs = _parse_covergroup_body(body)
    assert any(cp['name'] == 'c' for cp in cps)
    assert any(cp['name'] == 's' for cp in cps)


def test_parse_body_cross():
    body = "coverpoint color; coverpoint shape; cx: cross color, shape;"
    cps, cxs = _parse_covergroup_body(body)
    assert len(cxs) == 1
    assert cxs[0]['name'] == 'cx'
    assert set(cxs[0]['coverpoint_names']) == {'color', 'shape'}


def test_parse_body_cross_with_ignore():
    body = """
    coverpoint color ;
    coverpoint shape ;
    cross_color : cross color, shape {
        ignore_bins ib = cross with (color == BLUE && shape == SQUARE);
    };
    """
    cps, cxs = _parse_covergroup_body(body)
    assert len(cps) == 2
    assert len(cxs) == 1
    assert cxs[0]['name'] == 'cross_color'
    assert 'color' in cxs[0]['coverpoint_names']
    assert 'shape' in cxs[0]['coverpoint_names']


# ---------------------------------------------------------------------------
# Integration: annotation extraction
# ---------------------------------------------------------------------------

def test_covergroup_annotation_extracted():
    """Parser extracts covergroup annotations from raw PSS."""
    pss = """
    component pss_top {
        action draw_shape {
            rand int color;
            rand int shape;
            covergroup {
                coverpoint color;
                coverpoint shape;
                cross_color : cross color, shape;
            } cXs_cg;
        }
    }
    """
    parser = Parser()
    parser.parses([('t.pss', pss)])
    anns = [a for a in parser.annotations if a.kind == 'covergroup']
    assert len(anns) == 1
    ann = anns[0]
    assert ann.type_chain == ['pss_top', 'draw_shape']
    assert ann.data['instance_name'] == 'cXs_cg'
    assert len(ann.data['coverpoints']) == 2
    assert len(ann.data['crosses']) == 1
    assert ann.data['crosses'][0]['name'] == 'cross_color'


def test_covergroup_injected_into_ir():
    """Covergroup annotation is injected into the action's IR covergroups list."""
    pss = """
    component pss_top {
        action draw_shape {
            rand int color;
            rand int shape;
            covergroup {
                coverpoint color;
                coverpoint shape;
                cx: cross color, shape;
            } cg1;
        }
    }
    """
    from zuspec.fe.pss.ast_to_ir import AstToIrTranslator
    parser = Parser()
    parser.parses([('t.pss', pss)])
    root = parser.link()
    ctx = AstToIrTranslator().translate(root, annotations=parser.annotations)
    action_ir = ctx.type_map.get('pss_top::draw_shape') or ctx.type_map.get('draw_shape')
    assert action_ir is not None
    assert len(action_ir.covergroups) == 1
    cg = action_ir.covergroups[0]
    assert cg.instance_name == 'cg1'
    assert len(cg.coverpoints) == 2
    assert len(cg.crosses) == 1


def test_covergroup_parse_succeeds_with_cross():
    """PSS with a covergroup+cross should parse without raising ParseException."""
    from zuspec.fe.pss import load_pss
    # Just verify no exception is raised; covergroup is removed by preprocessor
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
        }
    """)
    # Action class should exist and be randomizable
    # Action registered as "pss_top::draw_shape" in the ClassRegistry
    all_names = list(ns.keys())
    assert any("draw_shape" in k for k in all_names), f"draw_shape not in {all_names}"
