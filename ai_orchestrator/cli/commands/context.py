"""Context command - Manage shared project context."""

from __future__ import annotations

import json
from pathlib import Path

from ai_orchestrator.core import context as ctx_store


def handle_context(args) -> None:
    """Handle the context command."""
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
        data = ctx_store.load(project_dir)
        print(json.dumps(data, indent=2))
