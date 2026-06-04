# AI Orchestrator

Portable orchestration framework for building web applications with Gemini owning frontend work and Codex owning architecture, backend, testing, deployment, and release readiness.

## Quick Start

```bash
python -m ai_orchestrator.cli init ./my-app --name my-app
python -m ai_orchestrator.cli plan ./my-app
python -m ai_orchestrator.cli run ./my-app
```

Use `python3` instead of `python` on systems where only `python3` is installed.

`run` defaults to dry-run mode. It writes task packets under `.orchestrator/runs/<timestamp>/tasks/` and prints the exact Gemini/Codex command for each stage.

To execute the configured agent commands:

```bash
python -m ai_orchestrator.cli run ./my-app --execute
```

Run one stage:

```bash
python -m ai_orchestrator.cli run ./my-app --stage 10_frontend_gemini
```

## Framework Shape

Each generated project contains:

- `brief.md`: the product brief for the application.
- `orchestrator.toml`: agents, commands, stack defaults, and stage flow.
- `workspace/`: the application repository the agents build.
- `.orchestrator/notes/`: completion notes written by each agent.
- `.orchestrator/runs/`: generated task packets, handoff files, and run state.

## Default Agent Split

- Gemini owns frontend UX, UI implementation, responsive layout, accessibility, client-side behavior, and frontend integration boundaries.
- Codex owns architecture, backend, APIs, persistence, testing, integration, deployment, documentation, and release readiness.

## Customizing Commands

Edit `orchestrator.toml`:

```toml
[agents.gemini_frontend]
command = "gemini --prompt-file {task_file}"

[agents.codex_engineering]
command = "codex exec --prompt-file {task_file}"
```

Available placeholders:

- `{task_file}`
- `{workspace}`
- `{stage}`
- `{run_dir}`

## Moving the Framework

The generated project folder is self-contained. Copy the folder to another machine, update `brief.md`, adjust commands in `orchestrator.toml` if your agent CLIs differ, then run `plan` or `run`.

## Verify

```bash
python3 -m unittest discover
```
