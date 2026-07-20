# AI Orchestrator

A CLI coding agent for planning, building, testing, and deploying apps —
powered by your own hosted models instead of third-party CLI tools.

## Architecture

- **Model access** — [LangChain](https://python.langchain.com) (`langchain-openai`) talks
  directly to any OpenAI-compatible endpoint. Configure providers in `.env`:
  - `lightning` — a self-hosted gateway (e.g. a Lightning AI GPU instance running vLLM/Ollama
    behind an OpenAI-compatible proxy)
  - `nvidia` — NVIDIA's NIM API (hosted open-source models)

  Calls retry transient failures automatically; if the active provider errors out mid-chat,
  the session falls back to the other configured provider and keeps going.
- **Agent loop** — [LangGraph](https://langchain-ai.github.io/langgraph/)'s `create_react_agent`
  runs a tool-using loop with SQLite-backed conversation state (`.orchestrator/chat_state.sqlite`),
  so context persists across chat sessions per project.
- **Runtime model switching** — use `/model <provider> [model]` inside the chat REPL to switch
  models mid-conversation without losing context.
- **Capability-based model routing** — the orchestrator chooses a model for each task role.
  The chat workflow uses `analyze -> implement -> verify` by default, while the internal role
  catalog still supports planner, repository_search, documentation, coding/debugging, testing,
  and deployment when a stage needs them. Defaults prefer NVIDIA reasoning/tool-use models for
  planning, repository/documentation work, verification, and deployment, while Lightning
  `qwen2.5-coder:14b` handles code generation and
  debugging. Override role picks in `.env` with values like
  `PLANNER_MODEL=nvidia:openai/gpt-oss-120b` or `CODING_MODEL=lightning:qwen2.5-coder:14b`.
  The chat UI shows only the planner/orchestrator model; internal routing still sees every
  configured provider model for role fallback.
- **Knowledge graph + context resolver** — the project is indexed into
  `.orchestrator/knowledge_graph.json` (files, functions/classes, import relationships),
  incrementally so re-indexing only re-parses changed files. Given a bug report or feature
  description, `resolve_issue(...)` scores the graph and points the agent at the most likely
  files/symbols *before* it starts exploring blind — essential for working in an existing,
  unfamiliar codebase. Auto-built at the start of every chat session and refreshed on every
  `plan` run, so it stays in sync as the code changes.
- **Skills** — step-by-step methodologies for `plan`/`build`/`test`/`deploy`/`debug`
  (`ai_orchestrator/skills/*.md`), pulled into context on demand via the `load_skill_instructions`
  tool, the matching `/plan` `/build` `/test` `/deploy` `/debug` slash commands, or automatically
  attached to each pipeline stage based on its name.
- **Tools** — see the full list below. File writes, edits, deletes, and shell commands always
  require interactive confirmation; reads, search, and knowledge-graph tools do not.
- **Memory** — `remember`/`recall` tools persist facts/decisions across sessions via
  `.orchestrator/context.json`, independent of any single conversation's history.

### Tools available to the agent

| Category | Tools |
| --- | --- |
| Filesystem | `read_file`, `list_dir`, `project_tree`, `glob_files`, `search_code`, `write_file`, `edit_file`, `delete_file` |
| Shell | `run_shell`, `run_tests` (auto-detects pytest/Django/npm/go/cargo), `git_status`, `git_diff` |
| Knowledge gateway | `web_search`, `fetch_url` — so a small/open-weight model can pull current docs instead of relying on stale training data |
| Knowledge graph | `build_knowledge_graph`, `resolve_issue`, `kg_stats` |
| Memory | `remember`, `recall` |
| Skills | `load_skill_instructions` |
| Scaffolding | `scaffold_project` |

## Quick Start

```bash
cd ai_orchestrator
pip install -e .

# Copy your .env with LIGHTNING_*/NVIDIA_* credentials into the project root
cp .env.example .env  # then fill in your keys

ai-orchestrator chat
```

`pip install -e .` registers the `ai-orchestrator` command (via the `[project.scripts]` entry
point in `pyproject.toml`) on your PATH for as long as the environment it was installed into is
active — no need to invoke it as `python -m ai_orchestrator` afterwards.

### Installing from a zip

To set this up on another machine (or share it) without cloning the repo, zip the installable
parts and hand that off instead:

```bash
zip -r ai-orchestrator.zip ai_orchestrator pyproject.toml README.md .env.example scripts \
  -x "*/__pycache__/*" "*.pyc"
```

Then, wherever you want to use it:

```bash
unzip ai-orchestrator.zip -d ai-orchestrator && cd ai-orchestrator
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # fill in your provider keys
```

## Using it in an existing project

`ai_orchestrator/` is a standalone CLI tool, not a dependency you copy into your project — install it once (anywhere, into any venv you like) and just `cd` into your project to use it there. It
does *not* need to live inside the project it's working on.

```
~/tools/ai_orchestrator/        # the orchestrator's own source — lives anywhere
  ai_orchestrator/
  pyproject.toml
  ...

~/projects/todo/                # your actual project — orchestrator is never copied in here
  frontend/
  backend/
  .venv/                        # any venv with ai-orchestrator installed (todo's own or shared)
  .env                          # orchestrator's LIGHTNING_*/NVIDIA_* keys go here
  .orchestrator/                # created automatically: knowledge graph + chat history
```

Steps:

```bash
pip install -e ~/tools/ai_orchestrator          # once, into whichever venv you'll activate below
cp ~/tools/ai_orchestrator/.env.example ~/projects/todo/.env   # then fill in your keys
cd ~/projects/todo
ai-orchestrator chat
```

Notes:
- The orchestrator reads `.env` and writes `.orchestrator/` in whatever directory you launch
  `ai-orchestrator chat` from — that's why `.env` belongs at the root of `todo/`, not inside
  `ai_orchestrator/`.
- Don't pass `--project-dir` for an existing repo like this — that flag is for the separate
  `init`/`plan`/`run` scaffolding pipeline and points the agent at `<project-dir>/workspace/`
  instead of the directory itself. Running `ai-orchestrator chat` with no flags from inside
  `todo/` operates on `todo/` directly (though in that mode the knowledge graph and chat
  history are rebuilt each session rather than cached to disk).

## Building / rebuilding the knowledge graph

The knowledge graph (`.orchestrator/knowledge_graph.json`) is what lets the agent point itself
at the right files instead of exploring an unfamiliar codebase blind — see
[Architecture](#architecture) above.

- **Automatic** — (re)built the moment a chat session starts, incrementally: only files that
  changed since the last build are re-parsed, so it's cheap even on a large repo.
- **Manual rebuild inside the chat REPL** — force a full re-index at any time:
  ```
  /kg rebuild
  ```
  (`/kg` alone just prints current stats — file count, import-edge count — without rebuilding.)
- **Manual rebuild from the CLI, without opening chat** — refresh the graph for a scaffolded
  project as part of `plan`:
  ```bash
  ai-orchestrator plan ./my-app
  ```
- **Let the agent trigger it mid-conversation** — the agent has a `build_knowledge_graph` tool
  it can call itself (e.g. after you tell it you added a bunch of new files), and `kg_stats` /
  `resolve_issue` tools to inspect or query the graph without a manual rebuild.

**Persisting it to disk (existing projects):** the graph is only written to
`.orchestrator/knowledge_graph.json` when the chat session has a project dir associated with
it, and — per [Using it in an existing project](#using-it-in-an-existing-project) — `--project-dir`
points the agent at `<project-dir>/workspace/`, not the directory itself, so it's not a drop-in
flag for an arbitrary existing repo laid out like `frontend/`/`backend/`. Two ways to get a
persisted graph for a project like that today:
- Run plain `ai-orchestrator chat` from the project root and use `/kg rebuild` for a fresh index
  within that session — it stays fast for the rest of the session, but isn't cached to disk, so
  the next session rebuilds it again from scratch.
- Or lay the project out to match the scaffolding convention (actual code under a `workspace/`
  subfolder) and use `--project-dir`, which does cache to disk between sessions.

## Commands

```bash
ai-orchestrator chat                          # interactive chat with the coding agent
ai-orchestrator init ./my-app --name my-app    # scaffold a new orchestration project
ai-orchestrator plan ./my-app                  # generate stage task packets + refresh the KG
ai-orchestrator run ./my-app --execute          # run the multi-stage build pipeline
ai-orchestrator context show ./my-app          # inspect shared project context
```

## Inside the chat REPL

```
/model                          show the planner/orchestrator model
/model nvidia openai/gpt-oss-20b  switch provider + model
/providers                      show the planner/orchestrator model
/tools                          list tools available to the agent
/skills                         list available skills
/plan <task>                    run analyze -> implement -> verify
/build <task>                   work through <task> following the Build skill
/test [task]                    run/write tests following the Test skill
/deploy [task]                  prepare a deployment following the Deploy skill
/debug <task>                   investigate a bug following the Debug skill
/kg                             show knowledge graph stats
/kg rebuild                     force a full re-index of the project
/clear                          start a fresh conversation thread
/help                           show all commands
```
