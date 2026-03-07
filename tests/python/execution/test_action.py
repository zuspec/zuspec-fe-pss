from __future__ import annotations
import asyncio
from zuspec.fe.pss import Parser, AstToIrTranslator, AstToIrContext, IrToRuntimeBuilder


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
