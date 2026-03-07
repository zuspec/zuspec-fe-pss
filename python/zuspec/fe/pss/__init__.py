
import os
from .parser import Parser, ParseException
from .ast_to_ir import AstToIrTranslator, AstToIrContext
from .ir_to_runtime import IrToRuntimeBuilder, ClassRegistry


def load_pss(pss_text: str) -> ClassRegistry:
    """Parse PSS source text and return a registry of randomizable Python classes.

    Each PSS ``struct`` becomes a plain Python dataclass whose fields can be
    randomized with ``zuspec.dataclasses.randomize()``.

    Example::

        from zuspec.fe.pss import load_pss
        from zuspec.dataclasses import randomize

        ns = load_pss(\"\"\"
            struct Packet {
                rand bit[8] addr;
                constraint addr % 4 == 0;
            }
        \"\"\")
        pkt = ns.Packet()
        randomize(pkt, seed=42)
        assert pkt.addr % 4 == 0
    """
    parser = Parser()
    parser.parses([('inline.pss', pss_text)])
    root = parser.link()
    ctx = AstToIrTranslator().translate(root)
    return IrToRuntimeBuilder(ctx).build()

def get_deps():
    return []

def get_libs():
    return ["zsp-parser"]

def get_libdirs():
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    return [pkg_dir]

def get_incdirs():
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.isdir(os.path.join(pkg_dir, "include")):
        return [os.path.join(pkg_dir, "include")]
    else:
        root_dir = os.path.abspath(os.path.join(pkg_dir, "../.."))
        return [os.path.join(root_dir, "src", "include")]
