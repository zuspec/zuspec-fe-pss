
import os
from .parser import Parser, ParseException
from .ast_to_ir import AstToIrTranslator, AstToIrContext
from .ir_to_runtime import IrToRuntimeBuilder, ClassRegistry


class PssTranslationError(Exception):
    """Raised when PSS source cannot be fully translated to IR.

    Unlike :exc:`ParseException` (which covers syntax/resolution errors caught
    by the parser/linker), this exception signals failures that occur during
    the AST→IR translation pass — for example, field types that the translator
    does not yet handle.

    ``errors`` is a list of human-readable error strings, one per problem.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        joined = "\n  ".join(errors)
        super().__init__(f"PSS IR translation failed with {len(errors)} error(s):\n  {joined}")


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
    if ctx.errors:
        raise PssTranslationError(ctx.errors)
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
