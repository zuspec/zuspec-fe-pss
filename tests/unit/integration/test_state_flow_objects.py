"""T1-6: State struct _initial tagging and flow_kind propagation."""
from __future__ import annotations
import os
import tempfile
import pytest

from zuspec.fe.pss import Parser, AstToIrTranslator, IrToRuntimeBuilder

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

PSS_SRC = """\
state power_s {
    rand bit[8] val;
}
component pss_top {
    action producer { output power_s state_out; }
    action consumer { input power_s state_in; }
    action test {
        producer p;
        consumer c;
        activity { p; c; }
    }
}
"""


def _build(src: str):
    with tempfile.NamedTemporaryFile(suffix='.pss', mode='w', delete=False) as f:
        f.write(src)
        fname = f.name
    try:
        p = Parser()
        p.parse([fname])
        root = p.link()
        ctx = AstToIrTranslator().translate(root)
        return ctx, IrToRuntimeBuilder(ctx).build()
    finally:
        try:
            os.unlink(fname)
        except OSError:
            pass


def test_state_struct_flow_kind():
    """State struct IR should have flow_kind == 'state'."""
    ctx, _ = _build(PSS_SRC)
    power_ir = ctx.type_map.get("power_s")
    assert power_ir is not None, "power_s not found in type_map"
    assert power_ir.flow_kind == "state", \
        f"Expected flow_kind='state', got {power_ir.flow_kind!r}"


def test_state_struct_python_class_tagged():
    """Runtime Python class for state struct should have _pss_flow_kind attribute."""
    ctx, classes = _build(PSS_SRC)
    power_cls = classes.get("power_s")
    assert power_cls is not None, "power_s Python class not found"
    assert getattr(power_cls, "_pss_flow_kind", None) == "state", \
        f"Expected _pss_flow_kind='state', got {getattr(power_cls, '_pss_flow_kind', None)!r}"


PSS_INITIAL_SRC = """\
state init_state_s {
    rand bit[8] val;
    constraint initial -> val == 0;
}
component pss_top {
    pool init_state_s st;
    bind st *;
    action step { input init_state_s a; output init_state_s b; }
}
"""


def test_initial_constraint_field_injected():
    """Pre-processor injects `initial` field; has_initial_constraint is set."""
    ctx, _ = _build(PSS_INITIAL_SRC)
    st_ir = ctx.type_map.get("init_state_s")
    assert st_ir is not None
    field_names = [f.name for f in st_ir.fields]
    assert "initial" in field_names, f"initial not injected; fields={field_names}"
    assert st_ir.has_initial_constraint, "has_initial_constraint should be True"


def test_initial_field_defaults_true():
    """State struct Python class should have initial=1 (True) as default."""
    ctx, classes = _build(PSS_INITIAL_SRC)
    st_cls = classes.get("init_state_s")
    assert st_cls is not None
    inst = st_cls()
    assert inst.initial == 1, f"Expected initial=1, got {inst.initial}"
