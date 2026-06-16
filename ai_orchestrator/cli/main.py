"""Command-line interface main entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from .commands.init import handle_init
from .commands.chat import handle_chat
from .commands.context import handle_context
from .commands.plan import handle_plan
from .commands.run import handle_run


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(prog="ai-orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init command
    init_parser = subparsers.add_parser("init", help="Create a reusable web app orchestration project")
    init_parser.add_argument("project_dir", type=Path)
    init_parser.add_argument("--name", help="Project name to write into orchestrator.toml")
    init_parser.add_argument("--force", action="store_true", help="Merge template into a non-empty directory")

    # plan command
    plan_parser = subparsers.add_parser("plan", help="Generate task packets for every stage")
    plan_parser.add_argument("project_dir", type=Path)

    # run command
    run_parser = subparsers.add_parser("run", help="Dry-run or execute configured agent commands")
    run_parser.add_argument("project_dir", type=Path)
    run_parser.add_argument("--stage", help="Run only one stage by name")
    run_parser.add_argument("--execute", action="store_true", help="Execute configured agent commands")

    # context command
    ctx_parser = subparsers.add_parser("context", help="Manage shared project context")
    ctx_sub = ctx_parser.add_subparsers(dest="ctx_command", required=True)

    set_parser = ctx_sub.add_parser("set", help="Set a user preference (key=value)")
    set_parser.add_argument("project_dir", type=Path)
    set_parser.add_argument("pairs", nargs="+", metavar="KEY=VALUE")

    show_parser = ctx_sub.add_parser("show", help="Print the current shared context")
    show_parser.add_argument("project_dir", type=Path)

    # chat command
    chat_parser = subparsers.add_parser("chat", help="Start interactive chat with AI orchestrator")
    chat_parser.add_argument("--project-dir", type=Path, help="Project directory for context")

    args = parser.parse_args()

    # Dispatch to command handlers
    if args.command == "chat":
        handle_chat(args.project_dir)
    elif args.command == "init":
        handle_init(args.project_dir, args.name, args.force)
    elif args.command == "context":
        handle_context(args)
    elif args.command == "plan":
        handle_plan(args.project_dir)
    elif args.command == "run":
        handle_run(args)


if __name__ == "__main__":
    main()
