# Quasnex — Multi-Model AI Coding Orchestrator

Quasnex is a multi-model AI coding orchestrator that helps you plan, build,
test, and ship applications from your terminal. Connect self-hosted or hosted
models through OpenAI-compatible endpoints, then route coding tasks to the
models configured for each role.

The core workflow is **analyze → implement → verify**: understand the task and
repository, make changes, and check the result.

The CLI uses a compact `[Q]` mark and a pulse moving between three connected
nodes, representing that workflow. The animation runs while Quasnex indexes
your repository or works on a chat request, with text describing the current
activity. It indicates activity, not a completion percentage or active model count.

```text
[Q] Quasnex — Multi-Model AI Coding Orchestrator
[Q] ●──○──○ Quasnex  Indexing repository · building code context
```

The terminal UI uses a compact developer-tool layout with cyan/violet status
chips, lightweight separators, a command palette, model registry, animated
progress states, and Markdown response cards that adapt to the terminal width.

## Architecture

- **Model access** — [LangChain](https://python.langchain.com) (`langchain-openai`) talks
  directly to any OpenAI-compatible endpoint. Configure providers in `.env`:
  - `lightning` — a self-hosted gateway (e.g. a Lightning AI GPU instance running vLLM/Ollama
    behind an OpenAI-compatible proxy)
  - `nvidia` — NVIDIA's NIM API (hosted open-source models)
  - `openrouter` — OpenRouter's hosted gateway and model catalog

  Calls retry transient failures automatically; if the routed provider errors out mid-chat,
  the session falls back to another configured candidate and keeps going.
- **Agent loop** — [LangGraph](https://langchain-ai.github.io/langgraph/)'s `create_react_agent`
  runs a tool-using loop with SQLite-backed conversation state (`.orchestrator/chat_state.sqlite`),
  so context persists across chat sessions per project.
- **Planner-driven automatic routing** — every normal chat query first goes to the configured
  planner model for a small, tool-free routing pass. It assesses the domain, complexity,
  workload, and whether the request needs a direct answer or the full workflow, then chooses
  an exact model from the allowed candidates for that capability. The choice is validated
  locally; invalid output or a routing-call failure uses a safe deterministic fallback.
- **Cross-provider delegation** — the thinking model and execution model do not need to use the
  same provider. For example, an OpenRouter-hosted thinking model can delegate coding to an
  NVIDIA-hosted model; Quasnex rebuilds the execution agent against the selected route.
- **Capability-based model registry** — available routes are grouped into planner,
  repository_search, documentation, coding, debugging, testing, and deployment roles. A
  file-changing request keeps the `analyze -> execute -> verify` workflow, with the selected
  model handling the main execution step. Defaults prefer NVIDIA reasoning/tool-use models for
  planning, repository/documentation work, verification, and deployment, while a configured
  code model handles code generation and debugging. Override preferred role candidates in
  `.env` with values like
  `PLANNER_MODEL=openrouter:openrouter/auto` or `CODING_MODEL=lightning:qwen2.5-coder:14b`.
  The selected route and routing rationale are shown before execution.
- **Team-lead model boundary** — `/model` exposes only eligible thinking models: the configured
  planner route, OSS-120B, and configured Nemotron models. Coding, debugging, testing,
  repository-search, documentation, and deployment models stay internal; the selected thinking
  model delegates work to them automatically. The choice persists across sessions, while
  `/model auto` resets the controller to the configured `PLANNER_MODEL` route.
- **Provider discovery** — `/providers` lists configured providers and model counts without
  exposing the internal worker-model selection menu.
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
| Skills | `list_available_skills`, `load_skill_instructions`, `load_skill_resource` |
| MCP | `list_mcp_servers`, `list_mcp_tools`, `call_mcp_tool` |
| Scaffolding | `scaffold_project` |

## Quick Start

```bash
cd ai_orchestrator
pip install -e .

# Copy your .env with LIGHTNING_*/NVIDIA_*/OPENROUTER_* credentials into the project root
cp .env.example .env  # then fill in your keys

quasnex chat
```

### OpenRouter setup

Create an OpenRouter API key, then add this to the `.env` in the project where
you run the orchestrator:

```dotenv
DEFAULT_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-replace-me
OPENROUTER_MODELS=openrouter/auto
```

List additional model slugs in `OPENROUTER_MODELS` as a comma-separated value.
Every thinking or worker model used by a capability route must be in that list:

```dotenv
OPENROUTER_MODELS=nvidia/nemotron-3.5-lightning:free,nvidia/nemotron-3-ultra-550b-a55b:free
PLANNER_MODEL=openrouter:nvidia/nemotron-3-ultra-550b-a55b:free
```

Restart the chat after editing `.env`. Quasnex automatically routes each request.
`/model` lists only eligible thinking models; worker choices remain internal. A configured
model whose slug contains `gpt-oss-120b` or `nemotron` is automatically included in this list.

Each provider has its own comma-separated inventory. Add a model by adding its exact API slug;
delete it by removing that slug:

```dotenv
LIGHTNING_MODELS=qwen2.5-coder:14b,qwen2.5-coder:7b
NVIDIA_MODELS=openai/gpt-oss-120b,nvidia/nemotron-3-ultra-550b-a55b
OPENROUTER_MODELS=nvidia/nemotron-3.5-lightning:free,nvidia/nemotron-3-ultra-550b-a55b:free
```

Providers can be enabled or disabled independently:

```dotenv
LIGHTNING_PROVIDER=false
NVIDIA_PROVIDER=true
OPENROUTER_PROVIDER=true
```

A disabled provider and all its models are removed from `/providers`, thinking-model selection,
automatic delegation, and fallback routing. Role overrides pointing to a deliberately disabled
provider are ignored, and `DEFAULT_PROVIDER` falls back to the first enabled provider.

Run `/model reload` after saving `.env` to use the new inventory without restarting the app.
Model slugs containing suffixes such as `:free` are preserved exactly. If the selected thinking
model was removed, Quasnex safely returns to `PLANNER_MODEL`. Capability overrides such as
`CODING_MODEL` must still reference a model present in that provider's `*_MODELS` list.

The optional `OPENROUTER_SITE_URL` and `OPENROUTER_APP_NAME` settings enable
OpenRouter app attribution. In an existing REPL session, run:

```text
/model openrouter nvidia/nemotron-3-ultra-550b-a55b:free
```

`pip install -e .` registers the `quasnex` command (via the `[project.scripts]` entry
point in `pyproject.toml`) on your PATH for as long as the environment it was installed into is
active. The older `cosnex`, `forgeflow`, and `ai-orchestrator` executables remain available
as compatibility aliases.

### Installing from a zip

To set this up on another machine (or share it) without cloning the repo, zip the installable
parts and hand that off instead:

```bash
zip -r quasnex.zip ai_orchestrator pyproject.toml README.md .env.example scripts \
  -x "*/__pycache__/*" "*.pyc"
```

Then, wherever you want to use it:

```bash
unzip quasnex.zip -d quasnex && cd quasnex
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
  .venv/                        # any venv with Quasnex installed (todo's own or shared)
  .env                          # Quasnex provider keys and model lists go here
  .orchestrator/                # created automatically: knowledge graph + chat history
```

Steps:

```bash
pip install -e ~/tools/ai_orchestrator          # once, into whichever venv you'll activate below
cp ~/tools/ai_orchestrator/.env.example ~/projects/todo/.env   # then fill in your keys
cd ~/projects/todo
quasnex chat
```

Notes:
- Quasnex reads `.env` and writes `.orchestrator/` in whatever directory you launch
  `quasnex chat` from — that's why `.env` belongs at the root of `todo/`, not inside
  `ai_orchestrator/`.
- Don't pass `--project-dir` for an existing repo like this — that flag is for the separate
  `init`/`plan`/`run` scaffolding pipeline and points the agent at `<project-dir>/workspace/`
  instead of the directory itself. Running `quasnex chat` with no flags from inside
  `todo/` operates on `todo/` directly (though in that mode the knowledge graph and chat
  history are rebuilt each session rather than cached to disk).

## External MCP servers and skills

Quasnex can use tools from external MCP servers and instructions from external
skill folders during `/build`, `/debug`, `/plan`, and ordinary chat tasks.
These integrations are also available to the agent used by the stage pipeline.

### Set up integrations

From the Quasnex source checkout, install the optional MCP dependency into your
active Python environment:

```bash
python -m pip install -e ".[mcp]"
```

Then, from the application you want to build or debug:

```bash
quasnex integrations init
quasnex integrations list
```

`init` creates `.quasnex.json` with disabled sample servers. Edit it to point at
your servers, then enable the ones you want. Existing configuration is preserved.
For a scaffolded project, keep this file beside `orchestrator.toml`, and use
`quasnex integrations init --project-dir ./my-app`.

### Connect MCP servers

Example `.quasnex.json`:

```json
{
  "mcpServers": {
    "local-tools": {
      "transport": "stdio",
      "command": "/absolute/path/to/python",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": {"SERVICE_TOKEN": "${SERVICE_TOKEN}"},
      "timeout": 30
    },
    "remote-tools": {
      "transport": "streamable-http",
      "url": "https://your-server.example/mcp",
      "headers": {"Authorization": "Bearer ${MCP_API_TOKEN}"},
      "timeout": 60
    }
  },
  "skills": ["/absolute/path/to/my-skills"]
}
```

Replace the example paths and URL, and remove any entries you don't use. A stdio
server can use any executable, including `node`, `npx`, or `uvx`; `args` are passed
directly without a shell. Its working directory defaults to your project root;
set `cwd` to change it. Legacy SSE servers use `"transport": "sse"`.

`${VARIABLE}` values are resolved from the project's `.env`, falling back to the
process environment. Only explicitly configured `env` values and the MCP SDK's
basic process environment are passed to local servers. Missing variables report
an error. Set `"enabled": false` to disable an entry. Configuration changes are
read on the next integration operation; no chat restart is needed.

Inside chat:

```text
/mcp
/mcp tools local-tools
/build Add the dashboard using the relevant tools from local-tools
/debug Use remote-tools to investigate the failing API request
```

The agent discovers each server's tool names and input schemas before calling
them. Quasnex asks for confirmation before connecting or invoking an MCP tool,
using the same confirmation UI as filesystem and shell actions. Each operation
opens and closes its own session, so server session state is not retained between
calls. This integration supports MCP **tools**; MCP resources, prompts, and OAuth
login flows are not exposed yet. Use configured authentication headers where needed.
The client uses the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x).

### Add external skills

For a project-specific skill, create this structure:

```text
my-app/
  .quasnex/
    skills/
      api-debug/
        SKILL.md
        references.md
```

Example `SKILL.md`:

```markdown
# API debugging

1. Reproduce the failing request and inspect the relevant code.
2. Discover configured MCP tools that can inspect API logs or documentation.
3. Read references.md for project-specific debugging steps.
4. Fix the cause, run focused tests, and report the result.
```

For skills stored elsewhere, add paths to the `skills` array in `.quasnex.json`.
Each path can be a `SKILL.md` file, a folder containing one, or a collection of
skill folders. Flat `.md` instruction files are also supported. Relative paths
are resolved against the project root; `~` paths are supported.

Skill names come from the containing folder for `SKILL.md`, or the filename for
other Markdown files. Names must use letters, numbers, hyphens, or underscores.
Duplicate names, including names of built-in skills, report a configuration error.
Quasnex reads instructions and companion text files; it does not automatically
install dependencies or execute scripts bundled with a skill.

```text
/skills
/skill api-debug Fix the login endpoint returning 500
/build Build a settings page using my frontend skill
/debug Use api-debug to investigate the login failure
```

The agent can discover skills with `list_available_skills`, load their instructions
with `load_skill_instructions`, and read companion files with `load_skill_resource`.
The built-in `plan`, `build`, `test`, `deploy`, and `debug` skills remain available.

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
  quasnex plan ./my-app
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
- Run plain `quasnex chat` from the project root and use `/kg rebuild` for a fresh index
  within that session — it stays fast for the rest of the session, but isn't cached to disk, so
  the next session rebuilds it again from scratch.
- Or lay the project out to match the scaffolding convention (actual code under a `workspace/`
  subfolder) and use `--project-dir`, which does cache to disk between sessions.

## Commands

```bash
quasnex chat                          # interactive chat with the coding agent
quasnex init ./my-app --name my-app    # scaffold a new orchestration project
quasnex plan ./my-app                  # generate stage task packets + refresh the KG
quasnex run ./my-app --execute          # run the multi-stage build pipeline
quasnex context show ./my-app          # inspect shared project context
```

## Inside the chat REPL

```
/model                          select from eligible thinking models
/model auto                     reset to the configured thinking model
/model reload                   reload provider models from .env
/model list                     list eligible thinking models
/model openrouter openrouter/auto   select it only when it is PLANNER_MODEL
/providers                      list configured providers and model counts
/tools                          list tools available to the agent
/skills                         list available skills
/skill <name> <task>             apply a built-in or external skill
/mcp                            list configured MCP servers
/mcp tools <server>              discover a server's tools and input schemas
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
