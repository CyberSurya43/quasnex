# AI Orchestrator

Portable orchestration framework for building web applications with Gemini owning frontend work and Codex owning architecture, backend, testing, deployment, and release readiness.

## Quick Start
- Copy and paste the `ai_orchestrator` folder to your project folder.
- Move the `setup.py` and `pyproject.toml` to parent directory of you project and run the commands.

```bash
pip install -e .
ai-orchestrator init ./my-app --name my-app
ai-orchestrator plan ./my-app
ai-orchestrator run ./my-app
```

Use `python3` instead of `python` on systems where only `python3` is installed.

`run` defaults to dry-run mode. It writes task packets under `.orchestrator/runs/<timestamp>/tasks/` and prints the exact Gemini/Codex command for each stage.

To execute the configured agent commands:

```bash
ai-orchestrator run ./my-app --execute
```

Run one stage:

```bash
ai-orchestrator run ./my-app --stage 10_frontend_gemini
```

## Interactive Chat Mode

Chat with the orchestrator - it automatically routes your query to the appropriate agent:

```bash
# Start chat (orchestrator decides which agent to use)
python -m ai_orchestrator.cli chat

# Chat with project context
python -m ai_orchestrator.cli chat --project-dir ./my-app
```

The orchestrator analyzes your query and routes to:
- **Gemini** - For UI/UX, frontend, components, styling questions
- **Codex** - For backend, API, database, testing, deployment, orchestrator questions  
- **Ollama** - Automatic fallback when Gemini/Codex fail (credit exhaustion, API errors)

Commands in chat:
- `exit`, `quit`, `q` - Exit chat session
- `clear` - Clear conversation history

## Architecture Flow

### Agent Responsibilities
- **Codex** - Orchestrator, backend, testing, deployment
- **Gemini** - Frontend only
- **Ollama (Qwen)** - Fallback for both when primary fails

### Automatic Fallback Chain
1. Primary agent (Gemini/Codex) attempts task
2. If failure (credit, timeout, API error) → Falls back to Ollama
3. Ollama continues entire orchestration to deployment
4. When primary API comes online, system switches back

### Context Management
All agents share context via `.orchestrator/context.json`:
- Completed stages and model used
- Failures and fallback history
- User preferences
- Agent completion notes

Each agent records their work so any model can continue seamlessly.

## Professional Development Standards

All agents follow senior software developer best practices:

### Code Quality
- Clean code principles (DRY, SOLID)
- Self-documenting code
- Comprehensive error handling
- Security-first approach
- Performance optimization

### Testing
- 80%+ code coverage
- Unit, integration, and E2E tests
- Edge case coverage
- Security testing

### Security
- Input validation on all inputs
- No hardcoded secrets
- SQL injection prevention
- XSS/CSRF protection
- Dependency vulnerability scanning

### Deployment
- Production-ready Docker configs
- Health checks and monitoring
- Rollback procedures
- Documentation

See [SENIOR_DEV_GUIDELINES.md](SENIOR_DEV_GUIDELINES.md) for complete standards.

## Environment Configuration

Create a `.env` file in your project root:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
GEMINI_API_KEY=your_key_here
CODEX_API_KEY=your_key_here
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder
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

The `ai_orchestrator` folder is self-contained. Copy the folder to another machine, install it, and you're ready to go:

```bash
# Copy to new location
cp -r ai_orchestrator /path/to/new/location/

# Use it
cd /path/to/new/location/
python -m ai_orchestrator.cli init ./my-project --name my-project
```

## Installation

If you want to install it as a package:

```bash
cd /path/to/ai_orchestrator/parent/directory
pip install -e ai_orchestrator/
```

Then use:

```bash
ai-orchestrator init ./my-app --name my-app
ai-orchestrator chat
```

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - Quick start guide with examples
- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture documentation
- [SENIOR_DEV_GUIDELINES.md](SENIOR_DEV_GUIDELINES.md) - Professional development standards
- [PROFESSIONAL_TOOLS_SUMMARY.md](PROFESSIONAL_TOOLS_SUMMARY.md) - Implementation details

## Verify

Run tests:

```bash
python3 -m pytest tests/
# or
python3 -m unittest discover
```
