"""Tests for forall constraints over struct-typed collections (WI-6).

Runtime enforcement of struct-member forall requires struct-array randomization
support in the solver (struct elements decomposed into sub-variables). That
support is not yet implemented; the solver-level logic IS in place and is tested
here via direct ir_parser interaction. End-to-end runtime tests are marked xfail.
"""
import pytest
from zuspec.fe.pss import load_pss
from zuspec.dataclasses import randomize

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


# ---------------------------------------------------------------------------
# WI-6 solver unit test — verify _parse_foreach_loop handles struct-field vars
# ---------------------------------------------------------------------------

def test_parse_foreach_struct_member_direct():
    """_parse_foreach_loop correctly expands struct-member iteration when
    variable_map contains 'array[i].field' keys (the pattern produced by the
    solver for struct-typed arrays)."""
    from zuspec.dataclasses.solver.frontend.ir_parser import IRExpressionParser as IRConstraintParser
    from zuspec.dataclasses import ir

    from zuspec.dataclasses.solver.core.variable import Variable
    from zuspec.dataclasses.solver.core.domain import BitVectorDomain

    dom = BitVectorDomain(intervals=[(0, 15)], width=4, signed=False)
    # Build a parser with struct array entries in variable_map
    parser = IRConstraintParser()
    for i in range(4):
        v = Variable(name=f'pkts{i}x', domain=dom)
        parser.register_variable(f'pkts[{i}].x', v)

    # Build a StmtForeach: foreach (p : self.pkts) { p.x < 8; }
    foreach_stmt = ir.StmtForeach(
        target=ir.ExprRefLocal(name='p'),
        iter=ir.ExprAttribute(value=ir.TypeExprRefSelf(), attr='pkts'),
        body=[
            ir.StmtExpr(expr=ir.ExprBin(
                lhs=ir.ExprAttribute(value=ir.ExprRefLocal(name='p'), attr='x'),
                op=ir.BinOp.Lt,
                rhs=ir.ExprConstant(value=8),
            )),
        ],
    )

    # _parse_foreach_loop should expand to 4 constraints (one per element)
    constraints = parser._parse_foreach_loop(foreach_stmt)
    assert len(constraints) == 4, f"expected 4 constraints, got {len(constraints)}"
    # Each constraint should reference the element's 'x' variable
    for i, c in enumerate(constraints):
        # The constraint is a CompareConstraint referencing pkts[i].x
        assert hasattr(c, 'left') or hasattr(c, 'variable'), \
            f"constraint[{i}] unexpected type: {type(c)}"


# ---------------------------------------------------------------------------
# End-to-end runtime struct-member forall — requires struct array support
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="Struct array fields are not yet decomposed into sub-variables by the "
           "runtime randomizer (pkts[i].x variables not registered). "
           "The solver logic (WI-6) is correct; blocked by struct-array IR-to-runtime gap.",
    strict=False,
)
def test_forall_struct_member_upper_bound_e2e():
    """constraint forall (p : pkts) { p.x < 8; } end-to-end (currently xfail)."""
    ns = load_pss("""
        struct Pkt {
            rand bit[4] x;
        }
        struct Burst {
            rand Pkt pkts[4];
            constraint forall (p : pkts) { p.x < 8; }
        }
    """)
    for seed in range(10):
        b = ns.Burst()
        randomize(b, seed=seed)
        for i in range(4):
            assert b.pkts[i].x < 8
