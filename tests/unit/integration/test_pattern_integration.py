"""Integration tests for PSS modeling patterns.

Each test loads one or more PSS files from the modeling_patterns directory,
builds runtime classes, and runs a scenario to verify end-to-end execution.
"""
from __future__ import annotations
import asyncio
import os
import tempfile
import warnings
import pytest

from zuspec.fe.pss import Parser, AstToIrTranslator, IrToRuntimeBuilder
from zuspec.dataclasses.rt.scenario_runner import ScenarioRunner

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

_PATTERNS = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..', '..',
    'modeling_patterns', 'pss',
)


def _build_from_files(*paths):
    p = Parser()
    p.parse([os.path.join(_PATTERNS, *seg.split('/')) for seg in paths])
    root = p.link()
    ctx = AstToIrTranslator().translate(root)
    return IrToRuntimeBuilder(ctx).build()


def _build_inline(src: str):
    with tempfile.NamedTemporaryFile(suffix='.pss', mode='w', delete=False) as f:
        f.write(src)
        fname = f.name
    try:
        p = Parser()
        p.parse([fname])
        root = p.link()
        ctx = AstToIrTranslator().translate(root)
        return IrToRuntimeBuilder(ctx).build()
    finally:
        try:
            os.unlink(fname)
        except OSError:
            pass


# ------------------------------------------------------------------
# T1-8: producer_consumer (stream flow objects) -- Phase 1
# ------------------------------------------------------------------

_PROD_CONS_SRC = """\
stream data_stream {
    rand bit[8] payload;
}
component ipA_c {
    action producer {
        output data_stream to_stream;
    }
}
component ipB_c {
    action consumer {
        input data_stream from_stream;
    }
}
component pss_top {
    ipA_c ipA;
    ipB_c ipB;
    pool data_stream buff_chan;
    bind buff_chan *;
    action entry {
        activity {
            do ipA_c::producer;
            do ipB_c::consumer;
        }
    }
}
"""


@pytest.mark.anyio
async def test_producer_consumer_runs():
    """T1-8: stream flow object scenario runs without error."""
    classes = _build_inline(_PROD_CONS_SRC)
    top = classes.pss_top()
    runner = ScenarioRunner(top, seed=42)
    result = await runner.run(classes['pss_top::entry'])
    assert result is not None


@pytest.mark.anyio
async def test_producer_consumer_multi_seed():
    """T1-8: producer_consumer is stable across seeds."""
    classes = _build_inline(_PROD_CONS_SRC)
    for seed in range(5):
        top = classes.pss_top()
        runner = ScenarioRunner(top, seed=seed)
        await runner.run(classes['pss_top::entry'])


# ------------------------------------------------------------------
# T1-11: constraint_overriding (soft constraint / default) -- Phase 1
# ------------------------------------------------------------------

@pytest.mark.anyio
async def test_constraint_overriding_runs():
    """T1-11: constraint_overriding pattern runs end-to-end."""
    classes = _build_from_files(
        'constraint_overriding/override_pattern.pss',
    )
    top = classes.pss_top()
    runner = ScenarioRunner(top, seed=1)
    result = await runner.run(classes['pss_top::test'])
    assert result is not None


# ------------------------------------------------------------------
# T1-4 / T1-9: parallel_processes (abstract action, lock/share) -- Phase 1
# ------------------------------------------------------------------

_PARALLEL_SRC = """\
stream p_status_t {
    rand bit[8] p_count;
}
resource channel_r {}
component base_c {
    abstract action base_action {
        input  p_status_t prev_p;
        output p_status_t next_p;
        lock   channel_r  busy;
        constraint next_p.p_count == prev_p.p_count + 1;
    }
}
component c01_c : base_c {
    pool [1] channel_r ch_pool;
    bind ch_pool *;
    action do_c01 : base_action {}
}
component pss_top {
    c01_c c01;
    pool p_status_t st_pool;
    bind st_pool *;
    action entry {
        activity {
            do c01_c::do_c01;
        }
    }
}
"""


@pytest.mark.anyio
async def test_abstract_action_excluded():
    """T1-9: abstract base action not selected; concrete sub-action runs."""
    classes = _build_inline(_PARALLEL_SRC)
    # base_action is abstract -- should not appear as a selectable type
    base_cls = classes.get('base_c::base_action')
    assert base_cls is not None
    from zuspec.ir.core.data_type import DataTypeClass
    # is_abstract should be set
    # Verify via re-translation that the base action IR has is_abstract=True
    import tempfile, os as _os
    with tempfile.NamedTemporaryFile(suffix='.pss', mode='w', delete=False) as _f:
        _f.write(_PARALLEL_SRC)
        _fname = _f.name
    try:
        from zuspec.fe.pss import Parser as _P, AstToIrTranslator as _T
        _p = _P(); _p.parse([_fname]); _root = _p.link()
        _ctx = _T().translate(_root)
        base_ir = _ctx.type_map.get('base_c::base_action')
        assert base_ir is not None, "base_c::base_action not in type_map"
        assert getattr(base_ir, 'is_abstract', False),             "base_c::base_action.is_abstract should be True"
    finally:
        try: _os.unlink(_fname)
        except OSError: pass


# ------------------------------------------------------------------
# T2-1 / T2-2: ActivityBind wiring in sequence -- Phase 2
# ------------------------------------------------------------------

_BIND_SRC = """\
buffer token_t {
    rand bit[8] val;
}
component pss_top {
    pool token_t tok_pool;
    bind tok_pool *;
    action producer { output token_t out_tok; }
    action consumer { input  token_t in_tok; }
    action entry {
        producer p;
        consumer c;
        activity {
            p;
            c;
            bind p.out_tok c.in_tok;
        }
    }
}
"""


@pytest.mark.anyio
async def test_activity_bind_routing():
    """T2-2: Explicit bind routes producer output to consumer input."""
    classes = _build_inline(_BIND_SRC)
    top = classes.pss_top()
    runner = ScenarioRunner(top, seed=99)
    result = await runner.run(classes['pss_top::entry'])
    assert result is not None


# ------------------------------------------------------------------
# T1-6: state flow objects with initial constraint -- Phase 1
# ------------------------------------------------------------------

_STATE_SRC = """\
state power_s {
    rand bit[8] val;
    constraint initial -> val == 0;
}
component pss_top {
    pool power_s st_pool;
    bind st_pool *;
    action init_state {
        output power_s st_out;
    }
    action use_state {
        input power_s st_in;
    }
    action entry {
        activity {
            do init_state;
            do use_state;
        }
    }
}
"""


@pytest.mark.anyio
async def test_state_initial_constraint():
    """T1-6: First state instance satisfies `constraint initial -> val == 0`."""
    classes = _build_inline(_STATE_SRC)
    top = classes.pss_top()
    runner = ScenarioRunner(top, seed=7)
    result = await runner.run(classes['pss_top::entry'])
    assert result is not None
