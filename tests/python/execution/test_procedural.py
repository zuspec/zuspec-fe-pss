"""Tests for PSS procedural statements executed via Python RT.

Covers LRM §22.7: variable declarations, assignments (plain and compound),
repeat, while, repeat-while, foreach, if-else, match, break/continue, return.
"""
from __future__ import annotations
import asyncio
import pytest
from zuspec.fe.pss import Parser, AstToIrTranslator, AstToIrContext, IrToRuntimeBuilder


def _build(pss_text: str):
    p = Parser()
    p.parses([('test.pss', pss_text)])
    root = p.link()
    ctx = AstToIrTranslator().translate(root)
    return IrToRuntimeBuilder(ctx).build()


def _run(action_cls, comp):
    """Run an action body synchronously and return the action instance."""
    result = None

    async def _inner():
        nonlocal result
        result = await action_cls()(comp)

    asyncio.run(_inner())
    return result


# ---------------------------------------------------------------------------
# §22.7.2  Variable declarations
# ---------------------------------------------------------------------------

def test_var_decl_with_init():
    """Local variable declared with inline initialiser."""
    classes = _build("""
        component C { action A {
            bit[32] result;
            exec body {
                int v = 42;
                result = v;
            }
        }}
    """)
    a = _run(classes.C.A, classes.C())
    assert a.result == 42


def test_var_decl_no_init():
    """Local variable declared without initialiser defaults to 0."""
    classes = _build("""
        component C { action A {
            bit[32] result;
            exec body {
                int v;
                result = v;
            }
        }}
    """)
    a = _run(classes.C.A, classes.C())
    assert a.result == 0


def test_var_decl_arithmetic():
    """Arithmetic using local variables."""
    classes = _build("""
        component C { action A {
            bit[32] result;
            exec body {
                int a = 10;
                int b = 3;
                result = a + b * 2;
            }
        }}
    """)
    a = _run(classes.C.A, classes.C())
    assert a.result == 16  # 10 + 3*2


# ---------------------------------------------------------------------------
# §22.7.3  Plain assignment
# ---------------------------------------------------------------------------

def test_assign_to_action_field():
    """Plain assignment writes to action field."""
    classes = _build("""
        component C { action A {
            bit[32] val;
            exec body { val = 99; }
        }}
    """)
    a = _run(classes.C.A, classes.C())
    assert a.val == 99


def test_assign_sequential():
    """Sequential assignments; last one wins."""
    classes = _build("""
        component C { action A {
            bit[32] x;
            exec body { x = 1; x = 2; x = 3; }
        }}
    """)
    a = _run(classes.C.A, classes.C())
    assert a.x == 3


# ---------------------------------------------------------------------------
# §22.7.3  Compound (augmented) assignments
# ---------------------------------------------------------------------------

def test_augassign_plus():
    classes = _build("""
        component C { action A {
            bit[32] v;
            exec body { v = 10; v += 5; }
        }}
    """)
    assert _run(classes.C.A, classes.C()).v == 15


def test_augassign_minus():
    classes = _build("""
        component C { action A {
            bit[32] v;
            exec body { v = 20; v -= 7; }
        }}
    """)
    assert _run(classes.C.A, classes.C()).v == 13


def test_augassign_shl():
    classes = _build("""
        component C { action A {
            bit[32] v;
            exec body { v = 1; v <<= 4; }
        }}
    """)
    assert _run(classes.C.A, classes.C()).v == 16


def test_augassign_shr():
    classes = _build("""
        component C { action A {
            bit[32] v;
            exec body { v = 64; v >>= 3; }
        }}
    """)
    assert _run(classes.C.A, classes.C()).v == 8


def test_augassign_or():
    classes = _build("""
        component C { action A {
            bit[32] v;
            exec body { v = 0xF0; v |= 0x0F; }
        }}
    """)
    assert _run(classes.C.A, classes.C()).v == 0xFF


def test_augassign_and():
    classes = _build("""
        component C { action A {
            bit[32] v;
            exec body { v = 0xFF; v &= 0x0F; }
        }}
    """)
    assert _run(classes.C.A, classes.C()).v == 0x0F


# ---------------------------------------------------------------------------
# §22.7.6  repeat(N) and repeat(i : N)
# ---------------------------------------------------------------------------

def test_repeat_no_index():
    """repeat(N) body runs exactly N times."""
    classes = _build("""
        component C { action A {
            bit[32] count;
            exec body {
                count = 0;
                repeat (5) { count += 1; }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).count == 5


def test_repeat_with_index():
    """repeat(i : N) provides 0-based index."""
    classes = _build("""
        component C { action A {
            bit[32] total;
            exec body {
                total = 0;
                repeat (i : 5) { total += i; }
            }
        }}
    """)
    # 0+1+2+3+4 = 10
    assert _run(classes.C.A, classes.C()).total == 10


def test_repeat_zero():
    """repeat(0) body never executes."""
    classes = _build("""
        component C { action A {
            bit[32] count;
            exec body {
                count = 0;
                repeat (0) { count += 1; }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).count == 0


def test_repeat_count_from_var():
    """repeat count taken from a local variable."""
    classes = _build("""
        component C { action A {
            bit[32] total;
            exec body {
                int n = 4;
                total = 0;
                repeat (n) { total += 1; }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).total == 4


def test_repeat_nested():
    """Nested repeat: outer × inner iterations."""
    classes = _build("""
        component C { action A {
            bit[32] count;
            exec body {
                count = 0;
                repeat (3) { repeat (4) { count += 1; } }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).count == 12


# ---------------------------------------------------------------------------
# §22.7.7  while and repeat-while
# ---------------------------------------------------------------------------

def test_while_basic():
    """while loop terminates when condition becomes false."""
    classes = _build("""
        component C { action A {
            bit[32] result;
            exec body {
                int n = 8; int count = 0;
                while (n > 1) { n = n / 2; count += 1; }
                result = count;
            }
        }}
    """)
    # floor(log2(8)) = 3
    assert _run(classes.C.A, classes.C()).result == 3


def test_while_no_iterations():
    """while with initially-false condition skips body."""
    classes = _build("""
        component C { action A {
            bit[32] count;
            exec body {
                count = 0;
                while (0) { count += 1; }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).count == 0


def test_repeat_while_runs_once():
    """repeat-while body runs at least once even if condition starts false."""
    classes = _build("""
        component C { action A {
            bit[32] count;
            exec body {
                count = 0;
                repeat { count += 1; } while (0);
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).count == 1


def test_repeat_while_multiple():
    """repeat-while loops until condition false."""
    classes = _build("""
        component C { action A {
            bit[32] count;
            exec body {
                count = 0;
                repeat { count += 1; } while (count < 3);
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).count == 3


# ---------------------------------------------------------------------------
# §22.7.8  foreach
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="PSS parser does not produce foreach in exec body (AstBuilderInt limitation)")
def test_foreach_sum_array():
    """foreach iterates all elements of a fixed-size array."""
    classes = _build("""
        component C { action A {
            bit[8] arr[4]; bit[32] sum;
            exec body {
                arr[0] = 1; arr[1] = 2; arr[2] = 3; arr[3] = 4;
                sum = 0;
                foreach (el : arr) { sum += el; }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).sum == 10


@pytest.mark.xfail(reason="PSS parser does not support foreach index variable syntax in this version")
def test_foreach_with_index():
    """foreach (el[i] : arr) provides both element and 0-based index."""
    classes = _build("""
        component C { action A {
            bit[8] arr[3]; bit[32] idx_sum;
            exec body {
                arr[0] = 10; arr[1] = 20; arr[2] = 30;
                idx_sum = 0;
                foreach (el [i] : arr) { idx_sum += i; }
            }
        }}
    """)
    # indices 0+1+2 = 3
    assert _run(classes.C.A, classes.C()).idx_sum == 3


# ---------------------------------------------------------------------------
# §22.7.9  if-else
# ---------------------------------------------------------------------------

def test_if_true_branch():
    """if: condition true → if-body runs."""
    classes = _build("""
        component C { action A {
            bit[32] result;
            exec body {
                if (1) { result = 1; } else { result = 2; }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).result == 1


def test_if_false_branch():
    """if: condition false → else-body runs."""
    classes = _build("""
        component C { action A {
            bit[32] result;
            exec body {
                if (0) { result = 1; } else { result = 2; }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).result == 2


def test_if_no_else():
    """if without else: body skipped when condition false."""
    classes = _build("""
        component C { action A {
            bit[32] result;
            exec body {
                result = 0;
                if (0) { result = 99; }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).result == 0


def test_if_nested():
    """Nested if-else selects correct inner branch."""
    classes = _build("""
        component C { action A {
            bit[32] result;
            exec body {
                int x = 5;
                if (x < 0) { result = 1; }
                else if (x < 3) { result = 2; }
                else if (x < 7) { result = 3; }
                else { result = 4; }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).result == 3


def test_if_comparison():
    """if with relational expression."""
    classes = _build("""
        component C { action A {
            bit[32] max;
            exec body {
                int a = 7; int b = 3;
                if (a > b) { max = a; } else { max = b; }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).max == 7


# ---------------------------------------------------------------------------
# §22.7.10  match
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="PSS parser does not produce match in exec body (AstBuilderInt limitation)")
def test_match_exact_value():
    """match selects correct arm by exact value."""
    classes = _build("""
        component C { action A {
            bit[8] bucket;
            exec body {
                int x = 2;
                match (x) {
                    [1]: bucket = 10;
                    [2]: bucket = 20;
                    [3]: bucket = 30;
                    default: bucket = 0;
                }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).bucket == 20


@pytest.mark.xfail(reason="PSS parser does not produce match in exec body (AstBuilderInt limitation)")
def test_match_default():
    """match default arm fires when no other arm matches."""
    classes = _build("""
        component C { action A {
            bit[8] bucket;
            exec body {
                int x = 99;
                match (x) {
                    [1]: bucket = 1;
                    [2]: bucket = 2;
                    default: bucket = 99;
                }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).bucket == 99


def test_match_no_match_no_default():
    """match with no matching arm and no default does nothing."""
    classes = _build("""
        component C { action A {
            bit[8] bucket;
            exec body {
                bucket = 7;
                int x = 5;
                match (x) {
                    [1]: bucket = 1;
                    [2]: bucket = 2;
                }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).bucket == 7


# ---------------------------------------------------------------------------
# §22.7.11  break / continue
# ---------------------------------------------------------------------------

def test_break_in_repeat():
    """break exits repeat early."""
    classes = _build("""
        component C { action A {
            bit[32] count;
            exec body {
                count = 0;
                repeat (i : 10) {
                    if (i == 5) { break; }
                    count += 1;
                }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).count == 5


def test_continue_in_repeat():
    """continue skips current iteration."""
    classes = _build("""
        component C { action A {
            bit[32] sum;
            exec body {
                sum = 0;
                repeat (i : 5) {
                    if (i == 2) { continue; }
                    sum += i;
                }
            }
        }}
    """)
    # 0+1+3+4 = 8  (skip i==2)
    assert _run(classes.C.A, classes.C()).sum == 8


def test_break_in_while():
    """break exits while early."""
    classes = _build("""
        component C { action A {
            bit[32] count;
            exec body {
                count = 0;
                while (1) {
                    if (count == 3) { break; }
                    count += 1;
                }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).count == 3


@pytest.mark.xfail(reason="PSS parser does not produce foreach in exec body (AstBuilderInt limitation)")
def test_break_in_foreach():
    """break exits foreach early."""
    classes = _build("""
        component C { action A {
            bit[8] arr[5]; bit[32] sum;
            exec body {
                arr[0] = 1; arr[1] = 2; arr[2] = 3; arr[3] = 4; arr[4] = 5;
                sum = 0;
                foreach (el[i] : arr) {
                    if (i == 3) { break; }
                    sum += el;
                }
            }
        }}
    """)
    # 1+2+3 = 6
    assert _run(classes.C.A, classes.C()).sum == 6


def test_break_inner_doesnt_exit_outer():
    """break in inner repeat doesn't exit outer repeat."""
    classes = _build("""
        component C { action A {
            bit[32] outer_count;
            exec body {
                outer_count = 0;
                repeat (3) {
                    repeat (i : 5) {
                        if (i == 2) { break; }
                    }
                    outer_count += 1;
                }
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).outer_count == 3


# ---------------------------------------------------------------------------
# §22.7.5  return
# ---------------------------------------------------------------------------

def test_return_stops_body():
    """bare return stops exec body early."""
    classes = _build("""
        component C { action A {
            bit[32] val;
            exec body {
                val = 1;
                return;
                val = 2;
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).val == 1


def test_return_from_conditional():
    """return inside an if branch stops body."""
    classes = _build("""
        component C { action A {
            bit[32] val;
            exec body {
                val = 10;
                if (1) { return; }
                val = 20;
            }
        }}
    """)
    assert _run(classes.C.A, classes.C()).val == 10
