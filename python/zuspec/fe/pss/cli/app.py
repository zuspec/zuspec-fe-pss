"""Argument parsing and top-level dispatch for the CLI."""
from __future__ import annotations

import argparse
import os
import sys


def _build_parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(
        prog="python -m zuspec.fe.pss",
        description="PSS compiler frontend -- syntax and semantic checker",
    )

    sub = top.add_subparsers(dest="command", required=False)

    p = sub.add_parser("parse", help="Parse (and link) PSS source files")
    p.add_argument("files", nargs="+", metavar="FILE", help=".pss source files")
    p.add_argument(
        "--syntax-only",
        action="store_true",
        default=False,
        help="Parse only; skip linking / symbol resolution",
    )
    p.add_argument(
        "--dump-ast",
        metavar="OUT",
        default=None,
        help="Write the linked AST to OUT as JSON",
    )
    p.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit diagnostics as JSON to stdout",
    )
    p.add_argument("-q", "--quiet", action="store_true", default=False)
    p.add_argument(
        "--color",
        action="store_true",
        default=None,
        dest="color",
        help="Force coloured output",
    )
    p.add_argument(
        "--no-color",
        action="store_false",
        dest="color",
        help="Disable coloured output",
    )
    p.add_argument(
        "--max-errors",
        type=int,
        default=20,
        metavar="N",
        help="Stop after N errors (0 = unlimited, default 20)",
    )

    return top


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Returns a process exit code."""
    parser = _build_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2

    if args.command is None:
        parser.print_help(sys.stderr)
        return 2

    # Validate files exist
    missing = [f for f in args.files if not os.path.isfile(f)]
    if missing:
        for m in missing:
            sys.stderr.write(f"error: file not found: {m}\n")
        return 2

    from .commands import cmd_parse

    try:
        return cmd_parse(
            files=args.files,
            syntax_only=args.syntax_only,
            dump_ast=args.dump_ast,
            use_json=args.json,
            quiet=args.quiet,
            color=args.color,
            max_errors=args.max_errors,
        )
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted\n")
        return 130
