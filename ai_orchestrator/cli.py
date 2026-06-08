from __future__ import annotations

import argparse
from pathlib import Path

from .runner import Orchestrator
from .scaffold import init_project
from . import context as ctx_store


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a reusable web app orchestration project")
    init_parser.add_argument("project_dir", type=Path)
    init_parser.add_argument("--name", help="Project name to write into orchestrator.toml")
    init_parser.add_argument("--force", action="store_true", help="Merge template into a non-empty directory")

    plan_parser = subparsers.add_parser("plan", help="Generate task packets for every stage")
    plan_parser.add_argument("project_dir", type=Path)

    run_parser = subparsers.add_parser("run", help="Dry-run or execute configured agent commands")
    run_parser.add_argument("project_dir", type=Path)
    run_parser.add_argument("--stage", help="Run only one stage by name")
    run_parser.add_argument("--execute", action="store_true", help="Execute configured agent commands")

    ctx_parser = subparsers.add_parser("context", help="Manage shared project context")
    ctx_sub = ctx_parser.add_subparsers(dest="ctx_command", required=True)

    set_parser = ctx_sub.add_parser("set", help="Set a user preference (key=value)")
    set_parser.add_argument("project_dir", type=Path)
    set_parser.add_argument("pairs", nargs="+", metavar="KEY=VALUE")

    show_parser = ctx_sub.add_parser("show", help="Print the current shared context")
    show_parser.add_argument("project_dir", type=Path)

    args = parser.parse_args()

    if args.command == "init":
        init_project(args.project_dir, args.name, args.force)
        print(f"Created orchestrator project at {args.project_dir.resolve()}")
        return

    if args.command == "context":
        project_dir = args.project_dir.resolve()
        if args.ctx_command == "set":
            for pair in args.pairs:
                if "=" not in pair:
                    print(f"Skipping malformed pair (expected KEY=VALUE): {pair!r}")
                    continue
                key, _, value = pair.partition("=")
                ctx_store.set_user_preference(project_dir, key.strip(), value.strip())
                print(f"Set preference: {key.strip()} = {value.strip()}")
        elif args.ctx_command == "show":
            import json
            data = ctx_store.load(project_dir)
            print(json.dumps(data, indent=2))
        return

    orchestrator = Orchestrator(args.project_dir)

    if args.command == "plan":
        run_dir = orchestrator.plan()
        print(f"Generated orchestration plan at {run_dir}")
        return

    if args.command == "run":
        results = orchestrator.run(args.stage, args.execute)
        for result in results:
            mode = "executed" if result["executed"] else "dry-run"
            model = result.get("model_used") or "n/a"
            print(f"[{mode}] {result['stage']} -> {result['agent']} (model: {model})")
            print(f"  task: {result['task_file']}")
            print(f"  cmd:  {result['command']}")


if __name__ == "__main__":
    main()
