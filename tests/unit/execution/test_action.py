from __future__ import annotations
import asyncio
from zuspec.fe.pss import Parser, AstToIrTranslator, AstToIrContext, IrToRuntimeBuilder


def _build(pss_text: str):
    p = Parser()
    p.parses([('test.pss', pss_text)])
    root = p.link()
    ctx = AstToIrTranslator().translate(root)
    return IrToRuntimeBuilder(ctx).build()


def test_action():
    content = """
component MyC {
  bit[32] val;

  action MyA {
    bit[32] val;

    exec body {
      val = 15;
    }
  }
}

component Top {
  MyC c1;
  MyC c2;

  exec init_down {
    c1.val = 21;
    c2.val = 22;
  }
}
"""

    # Parse and link the PSS source
    p = Parser()
    p.parses([('test_action.pss', content)])
    root = p.link()

    # Translate AST to IR
    translator = AstToIrTranslator()
    ctx = translator.translate(root)

    # Build Python classes from IR
    classes = IrToRuntimeBuilder(ctx).build()

    Top = classes.Top
    MyA = classes.MyC.MyA  # action nested on component class

    top = Top()

    async def run():
        a = await MyA()(top)
        assert a.comp.val in [21, 22], f"Expected c1.val or c2.val (21 or 22), got {a.comp.val}"
        assert a.val == 15, f"Expected a.val == 15, got {a.val}"

    asyncio.run(run())


def test_message_builtin_prints(capsys):
    """message(NONE, ...) in exec body must print to stdout."""
    classes = _build("""
        component BusCtrl {
            action Write {
                exec body {
                    message(NONE, "Hello World!");
                }
            }
        }
    """)

    top = classes.BusCtrl()

    async def run():
        await classes.BusCtrl.Write()(top)

    asyncio.run(run())

    captured = capsys.readouterr()
    assert "Hello World!" in captured.out


def test_message_builtin_severity_constants(capsys):
    """NONE severity constant is recognised and message prints."""
    classes = _build("""
        component C {
            action A {
                exec body {
                    message(NONE, "sev-none");
                }
            }
        }
    """)

    async def run():
        await classes.C.A()(classes.C())

    asyncio.run(run())

    out = capsys.readouterr().out
    assert "sev-none" in out, f"Expected 'sev-none' in output, got: {out!r}"



def test_print_builtin_outputs(capsys):
    """print(fmt, ...) in exec body must produce stdout output."""
    classes = _build("""
        component C {
            action A {
                exec body {
                    print("hello %d\\n", 42);
                }
            }
        }
    """)

    import asyncio
    async def run():
        await classes.C.A()(classes.C())

    asyncio.run(run())

    out = capsys.readouterr().out
    assert "hello 42\n" in out, f"Expected 'hello 42\\n' in output, got: {out!r}"


def test_print_builtin_no_args(capsys):
    """print(fmt) with no varargs must work (plain string)."""
    classes = _build("""
        component C {
            action A {
                exec body {
                    print("plain\\n");
                }
            }
        }
    """)

    import asyncio
    async def run():
        await classes.C.A()(classes.C())

    asyncio.run(run())

    out = capsys.readouterr().out
    assert "plain\n" in out, f"Expected 'plain\\n' in output, got: {out!r}"
