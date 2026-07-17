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

python -m ai_orchestrator chat
```

## Commands

```bash
python -m ai_orchestrator chat                          # interactive chat with the coding agent
python -m ai_orchestrator init ./my-app --name my-app    # scaffold a new orchestration project
python -m ai_orchestrator plan ./my-app                  # generate stage task packets + refresh the KG
python -m ai_orchestrator run ./my-app --execute          # run the multi-stage build pipeline
python -m ai_orchestrator context show ./my-app          # inspect shared project context
```

## Inside the chat REPL

```
/model                          show the active provider/model
/model nvidia openai/gpt-oss-20b  switch provider + model
/providers                      list all configured providers and their models
/tools                          list tools available to the agent
/skills                         list available skills
/plan <task>                    work through <task> following the Plan skill
/build <task>                   work through <task> following the Build skill
/test [task]                    run/write tests following the Test skill
/deploy [task]                  prepare a deployment following the Deploy skill
/debug <task>                   investigate a bug following the Debug skill
/kg                             show knowledge graph stats
/kg rebuild                     force a full re-index of the project
/clear                          start a fresh conversation thread
/help                           show all commands
```
