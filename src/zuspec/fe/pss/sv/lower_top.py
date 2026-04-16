"""Generate the top-level SV test harness module (``zsp_test_top``).

Produces an ``SVModuleDecl`` containing:
- ``import zsp_rt_pkg::*``
- Component tree construction
- Root action instantiation, randomization, and activity invocation
- Seed control via ``$value$plusargs``
- ``$finish`` at completion
- Optional deadlock watchdog fork
"""
from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from zuspec.be.sv.ir.sv import SVModuleDecl

if TYPE_CHECKING:
    from .context import LoweringContext


def generate_top_module(
    comp_type: str,
    root_action_type: str,
    import_if_type: Optional[str] = None,
    import_if_driver: Optional[str] = None,
    module_name: str = "zsp_test_top",
    watchdog_ns: int = 0,
    has_activity: bool = True,
) -> SVModuleDecl:
    """Generate the top-level test harness module.

    Args:
        comp_type: Mangled SV class name of the top-level component.
        root_action_type: Mangled SV class name of the root action.
        import_if_type: Optional import interface class name. If the
            component has import functions, this must be provided.
        import_if_driver: Optional driver class name to instantiate
            as the import interface implementation.
        module_name: Name of the generated module.
        watchdog_ns: Deadlock watchdog timeout in nanoseconds. 0 disables.
        has_activity: If True, call ``root.activity()`` (compound action).
            If False, call ``root.body()`` (atomic action).

    Returns:
        SVModuleDecl with the test harness body.
    """
    body: List[str] = []
    body.append("import zsp_rt_pkg::*;")
    body.append("")
    body.append("initial begin")

    # All declarations at the top of the block (SV requires decls before stmts)
    body.append("  automatic int seed;")
    body.append("  automatic int verbosity;")
    if import_if_type and import_if_driver:
        body.append(f"  automatic {import_if_driver} _drv;")
        body.append(f"  automatic {import_if_type} _imp;")
    body.append(f"  automatic {comp_type} top;")
    body.append("")

    # Seed control
    body.append('  if (!$value$plusargs("zsp_seed=%d", seed))')
    body.append("    seed = 42;")
    body.append("")

    # Verbosity control
    body.append('  if ($value$plusargs("zsp_verbosity=%d", verbosity))')
    body.append("    zsp_rt_pkg::zsp_rt_verbosity = verbosity;")
    body.append("")

    # Import interface construction
    if import_if_type and import_if_driver:
        body.append(f"  _drv = new();")
        body.append(f"  _imp = new();")
        body.append(f"  _imp.drv = _drv;")
        body.append("")

    # Component tree construction
    body.append(f'  top = new("top", null);')
    if import_if_type and import_if_driver:
        body.append(f"  top.import_if = _imp;")
    body.append("")

    # Watchdog fork (optional)
    if watchdog_ns > 0:
        body.append("  fork")
        body.append("    begin")
        body.append(f"      #{watchdog_ns};")
        body.append('      $fatal(1, "[ZSP] Deadlock watchdog timeout");')
        body.append("    end")
        body.append("  join_none")
        body.append("")

    # Root action lifecycle
    body.append("  begin")
    body.append(f"    automatic {root_action_type} root = new();")
    body.append("    root.comp = top;")
    body.append("    root.pre_solve();")
    body.append(f'    if (!root.randomize()) $fatal(1, "root action randomize failed");')
    body.append("    root.post_solve();")
    if has_activity:
        body.append("    root.activity();")
    else:
        body.append("    root.body();")
    body.append("  end")
    body.append("")

    # Completion
    body.append('  $display("[ZSP] Scenario complete");')
    body.append("  $finish;")
    body.append("end")

    return SVModuleDecl(name=module_name, body_lines=body)


def generate_top_module_auto(
    ctx: LoweringContext,
    comp_type: str,
    root_action_type: str,
    **kwargs,
) -> SVModuleDecl:
    """Generate the top module with context-aware defaults.

    Looks up the component in the context to detect whether it has
    an import interface and configures the top module accordingly.

    Args:
        ctx: Lowering context with type info.
        comp_type: Top-level component SV class name.
        root_action_type: Root action SV class name.
        **kwargs: Forwarded to ``generate_top_module()``.

    Returns:
        SVModuleDecl.
    """
    # Detect import interface
    import_if_type = kwargs.pop("import_if_type", None)
    if import_if_type is None:
        import_if_type = f"{comp_type}_import_if"
        # Check if the import_if was actually generated
        if import_if_type not in ctx.sv_name_map.values():
            import_if_type = None

    return generate_top_module(
        comp_type=comp_type,
        root_action_type=root_action_type,
        import_if_type=import_if_type,
        **kwargs,
    )
