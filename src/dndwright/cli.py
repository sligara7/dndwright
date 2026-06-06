"""Command-line interface for dndwright.

Usable without writing Python:

    dndwright eval character.json          # compute a sheet (FILE or '-' for stdin)
    dndwright graph --format mermaid       # export the built-in DAG
    dndwright content magic_items          # dump bundled content (or list categories)
    dndwright validate ruleset.json        # check a ruleset (built-in if omitted)

Pure stdlib (argparse + json); no extra dependencies. ``main()`` returns a process
exit code so it works both as a console-script and when called in tests.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__


def _read_json(path: str) -> Any:
    """Load JSON from ``path`` ('-' = stdin)."""
    if path == "-":
        text = sys.stdin.read()
    else:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    return json.loads(text)


def _cmd_eval(args: argparse.Namespace) -> int:
    from .rules.character_evaluator import CharacterInputError, evaluate_character

    data = _read_json(args.file)
    if not isinstance(data, dict):
        print(f"error: expected a JSON object, got {type(data).__name__}", file=sys.stderr)
        return 1
    try:
        sheet = evaluate_character(data, strict=args.strict)
    except CharacterInputError as e:
        print(str(e), file=sys.stderr)
        return 1
    indent = None if args.compact else 2
    print(json.dumps(sheet, indent=indent, default=str))
    return 0


def _cmd_graph(args: argparse.Namespace) -> int:
    from .rules.dnd_5e_2024 import DND_5E_2024_RULESET
    from .rules.export import to_dot, to_mermaid

    if args.format == "dot":
        print(to_dot(DND_5E_2024_RULESET, cluster=not args.no_cluster))
    else:
        print(to_mermaid(DND_5E_2024_RULESET, direction=args.direction,
                         cluster=not args.no_cluster))
    return 0


def _cmd_content(args: argparse.Namespace) -> int:
    from .content import categories, load_content

    cats = categories()
    if not args.category:
        print("\n".join(cats))
        return 0
    if args.category not in cats:
        print(f"unknown category {args.category!r}; choose from {cats}",
              file=sys.stderr)
        return 2
    items = load_content(args.category)
    if args.names:
        print("\n".join(str(i.get("name", "")) for i in items))
    else:
        print(json.dumps(items, indent=2, default=str))
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    from .rules.schema import Ruleset
    from .rules.validation import validate_ruleset

    if args.file:
        ruleset = Ruleset.model_validate(_read_json(args.file))
    else:
        from .rules.dnd_5e_2024 import DND_5E_2024_RULESET

        ruleset = DND_5E_2024_RULESET

    issues = validate_ruleset(ruleset)
    if not issues:
        print("OK — no issues")
        return 0
    for i in issues:
        where = f" [{i.node_id}]" if i.node_id else ""
        print(f"{i.severity.upper():7} {i.code}{where}: {i.message}", file=sys.stderr)
    has_error = any(i.severity == "error" for i in issues)
    return 1 if has_error else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dndwright",
        description="D&D 5e (2024) rules & character-sheet computation engine.",
    )
    parser.add_argument("--version", action="version", version=f"dndwright {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_eval = sub.add_parser("eval", help="compute a character sheet from JSON")
    p_eval.add_argument("file", nargs="?", default="-",
                        help="character JSON file, or '-' for stdin (default)")
    p_eval.add_argument("--compact", action="store_true", help="single-line JSON output")
    p_eval.add_argument("--strict", action="store_true",
                        help="fail on malformed input instead of coercing it")
    p_eval.set_defaults(func=_cmd_eval)

    p_graph = sub.add_parser("graph", help="export the built-in computation DAG")
    p_graph.add_argument("--format", choices=["mermaid", "dot"], default="mermaid")
    p_graph.add_argument("--direction", default="TD", help="Mermaid flow direction (TD, LR, …)")
    p_graph.add_argument("--no-cluster", action="store_true", help="do not group by node.group")
    p_graph.set_defaults(func=_cmd_graph)

    p_content = sub.add_parser("content", help="list or dump bundled content")
    p_content.add_argument("category", nargs="?",
                           help="content category; omit to list categories")
    p_content.add_argument("--names", action="store_true", help="print only item names")
    p_content.set_defaults(func=_cmd_content)

    p_val = sub.add_parser("validate", help="validate a ruleset (built-in if no file)")
    p_val.add_argument("file", nargs="?", help="ruleset JSON file (default: built-in)")
    p_val.set_defaults(func=_cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    from pydantic import ValidationError

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except ValidationError as e:
        # e.g. `validate` on valid JSON that isn't a well-formed ruleset.
        print(f"error: invalid ruleset: {e.error_count()} validation error(s)\n{e}",
              file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
