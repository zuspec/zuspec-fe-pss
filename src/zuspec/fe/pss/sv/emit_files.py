"""Organize SV IR nodes into output files and write them.

All generated classes (structs, components, actions, import interfaces)
are wrapped in a single ``package zsp_gen_pkg`` that imports
``zsp_rt_pkg``.  The top-level module imports both packages.

| File              | Contents                                      |
|-------------------|-----------------------------------------------|
| zsp_rt_pkg.sv     | Runtime library (copied from share/)          |
| zsp_gen_pkg.sv    | Package with all generated classes            |
| zsp_top.sv        | Top-level module / test harness               |
| zsp_filelist.f    | File list for simulator compilation           |
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from zuspec.be.sv.ir.sv import (
    SVClass,
    SVForwardDecl,
    SVModuleDecl,
    SVPackage,
    SVRawItem,
    SVTypedefEnum,
    SVTypedefStruct,
)
from zuspec.be.sv.ir.sv_emit import SVEmitter


_FILE_RT       = "zsp_rt_pkg.sv"
_FILE_GEN_PKG  = "zsp_gen_pkg.sv"
_FILE_TOP      = "zsp_top.sv"
_FILE_FILELIST = "zsp_filelist.f"

_COMPILE_ORDER = [
    _FILE_RT,
    _FILE_GEN_PKG,
    _FILE_TOP,
]


def classify_node(node: Any) -> str:
    """Return the output filename for a given SV IR node."""
    if isinstance(node, SVModuleDecl):
        return _FILE_TOP
    return _FILE_GEN_PKG


def classify_nodes(nodes: List[Any]) -> Dict[str, List[Any]]:
    """Classify nodes into per-file buckets."""
    buckets: Dict[str, List[Any]] = {f: [] for f in _COMPILE_ORDER}
    for node in nodes:
        dest = classify_node(node)
        buckets.setdefault(dest, []).append(node)
    return buckets


def emit_files(
    nodes: List[Any],
    output_dir: str,
    runtime_lib_path: Optional[Path] = None,
    top_module_node: Optional[SVModuleDecl] = None,
) -> List[Path]:
    """Write SV IR nodes to organized output files.

    All generated classes are wrapped in ``package zsp_gen_pkg`` which
    imports ``zsp_rt_pkg``.  The top module imports both.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    emitter = SVEmitter()
    all_nodes = list(nodes)
    if top_module_node is not None:
        all_nodes.append(top_module_node)

    buckets = classify_nodes(all_nodes)
    written: List[Path] = []

    # Copy runtime library
    if runtime_lib_path and runtime_lib_path.exists():
        rt_dst = out / _FILE_RT
        shutil.copy2(str(runtime_lib_path), str(rt_dst))
        written.append(rt_dst)

    filelist_entries: List[str] = []
    if runtime_lib_path and runtime_lib_path.exists():
        filelist_entries.append(_FILE_RT)

    # Emit generated package (all classes wrapped in a package)
    gen_nodes = buckets.get(_FILE_GEN_PKG, [])
    if gen_nodes:
        pkg_lines: List[str] = []
        pkg_lines.append("package zsp_gen_pkg;")
        pkg_lines.append("  import zsp_rt_pkg::*;")
        pkg_lines.append("")
        sv_body = emitter.emit_all(gen_nodes)
        for line in sv_body.splitlines():
            pkg_lines.append(f"  {line}" if line.strip() else "")
        pkg_lines.append("")
        pkg_lines.append("endpackage : zsp_gen_pkg")

        filepath = out / _FILE_GEN_PKG
        filepath.write_text("\n".join(pkg_lines) + "\n")
        written.append(filepath)
        filelist_entries.append(_FILE_GEN_PKG)

    # Emit top module (needs to import both packages)
    top_nodes = buckets.get(_FILE_TOP, [])
    if top_nodes:
        # Prepend import of generated package to the module body
        for node in top_nodes:
            if isinstance(node, SVModuleDecl):
                # Insert import zsp_gen_pkg::* after the existing import zsp_rt_pkg::*
                new_body = []
                for line in node.body_lines:
                    new_body.append(line)
                    if "import zsp_rt_pkg::*;" in line:
                        new_body.append("import zsp_gen_pkg::*;")
                node.body_lines = new_body

        sv_text = emitter.emit_all(top_nodes)
        filepath = out / _FILE_TOP
        filepath.write_text(sv_text + "\n")
        written.append(filepath)
        filelist_entries.append(_FILE_TOP)

    # Write filelist
    filelist_path = out / _FILE_FILELIST
    filelist_path.write_text("\n".join(filelist_entries) + "\n")
    written.append(filelist_path)

    return written


def emit_filelist(
    filenames: List[str],
    output_dir: str,
) -> Path:
    """Write a simulator file list."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / _FILE_FILELIST
    path.write_text("\n".join(filenames) + "\n")
    return path
