import os
from typing import List, Union
from pssparser import Parser, ParseException
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


def load_pss_files(paths: List[Union[str, os.PathLike]]) -> ClassRegistry:
    """Parse one or more ``.pss`` files and return a registry of Python classes.

    Files are parsed together so they can reference each other's types.
    Use this when your PSS model is split across multiple source files.

    Example::

        from zuspec.fe.pss import load_pss_files
        from zuspec.dataclasses import randomize

        ns = load_pss_files(['bus.pss', 'cpu.pss'])
        cmd = ns.WriteCmd()
        randomize(cmd, seed=1)
    """
    str_paths = [str(p) for p in paths]
    parser = Parser()
    parser.parse(str_paths)
    root = parser.link()
    ctx = AstToIrTranslator().translate(root)
    if ctx.errors:
        raise PssTranslationError(ctx.errors)
    return IrToRuntimeBuilder(ctx).build()

def get_deps():
    return ["pssparser"]

def get_libs():
    return []

def get_libdirs():
    return []

def get_incdirs():
    return []


# ---------------------------------------------------------------------------
# PSS-to-SystemVerilog generation API
# ---------------------------------------------------------------------------

from pathlib import Path
import shutil


def _get_runtime_lib_path() -> Path:
    """Return the path to the bundled zsp_rt_pkg.sv runtime library."""
    return Path(__file__).parent / "share" / "sv" / "zsp_rt_pkg.sv"


def generate_sv(pss_text: str, output_dir: str, **options) -> List[Path]:
    """Parse PSS source text and generate SystemVerilog files.

    Steps:
        1. Parse PSS text to IR.
        2. Lower IR to SV IR nodes via ``pss_to_sv()``.
        3. Serialize SV IR to text via ``SVEmitter``.
        4. Write output files to *output_dir*.
        5. Copy ``zsp_rt_pkg.sv`` runtime library to *output_dir*.

    Returns:
        List of paths to the generated files.
    """
    parser = Parser()
    parser.parses([('inline.pss', pss_text)])
    root = parser.link()
    ir_ctx = AstToIrTranslator().translate(root)
    if ir_ctx.errors:
        raise PssTranslationError(ir_ctx.errors)
    return _generate_sv_from_ctx(ir_ctx, output_dir, **options)


def generate_sv_files(paths: List[Union[str, os.PathLike]], output_dir: str, **options) -> List[Path]:
    """Parse PSS source files and generate SystemVerilog files.

    Returns:
        List of paths to the generated files.
    """
    str_paths = [str(p) for p in paths]
    parser = Parser()
    parser.parse(str_paths)
    root = parser.link()
    ir_ctx = AstToIrTranslator().translate(root)
    if ir_ctx.errors:
        raise PssTranslationError(ir_ctx.errors)
    return _generate_sv_from_ctx(ir_ctx, output_dir, **options)


def _generate_sv_from_ctx(ir_ctx: AstToIrContext, output_dir: str, **options) -> List[Path]:
    """Internal: lower IR context and write SV output files.

    When ``multi_file=True`` (default), output is organized into separate
    files per node category (pkg, import_if, components, actions, top)
    with a simulator file list.  When ``multi_file=False``, all nodes are
    emitted to a single ``zsp_pkg.sv`` (legacy behaviour).

    ``inference_mode`` controls runtime inference code generation:
    ``"static"`` (default) -- no runtime inference code.
    ``"sv-native"`` -- SV-native selectors for simple slots.
    ``"dpi"`` -- DPI inference for complex, SV-native for simple.
    ``"full"`` -- DPI inference for all slots.
    """
    from .sv.pss_to_sv import pss_to_sv
    from .sv.emit_files import emit_files
    from .sv.lower_top import generate_top_module

    multi_file = options.pop('multi_file', True)
    inference_mode = options.pop('inference_mode', 'static')
    sv_nodes = pss_to_sv(ir_ctx)
    rt_src = _get_runtime_lib_path()

    # Optional top-level module generation
    comp_type = options.pop('comp_type', None)
    root_action_type = options.pop('root_action_type', None)
    top_node = None
    if comp_type and root_action_type:
        top_node = generate_top_module(
            comp_type=comp_type,
            root_action_type=root_action_type,
            import_if_type=options.pop('import_if_type', None),
            import_if_driver=options.pop('import_if_driver', None),
            watchdog_ns=options.pop('watchdog_ns', 0),
        )

    if multi_file:
        return emit_files(
            nodes=sv_nodes,
            output_dir=output_dir,
            runtime_lib_path=rt_src if rt_src.exists() else None,
            top_module_node=top_node,
        )

    # Legacy single-file mode
    from zuspec.be.sv.ir.sv_emit import SVEmitter

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    emitter = SVEmitter()

    all_nodes = list(sv_nodes)
    if top_node is not None:
        all_nodes.append(top_node)

    sv_text = emitter.emit_all(all_nodes)
    written: List[Path] = []

    gen_path = out / 'zsp_pkg.sv'
    gen_path.write_text(sv_text + "\n")
    written.append(gen_path)

    if rt_src.exists():
        rt_dst = out / 'zsp_rt_pkg.sv'
        shutil.copy2(str(rt_src), str(rt_dst))
        written.append(rt_dst)

    return written

