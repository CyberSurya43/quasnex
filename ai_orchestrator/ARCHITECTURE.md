# AI Orchestrator Architecture

## Query Routing Flow

```
User Query
    ↓
Orchestrator (analyzes query)
    ↓
    ├─→ Frontend keywords? → Gemini ──(fails)──→ Ollama
    │                          ↓                     ↓
    │                      (success)            (continues)
    │
    └─→ Backend/Orchestrator/Testing/Deploy? → Codex ──(fails)──→ Ollama
                                                  ↓                   ↓
                                              (success)          (continues)
```

## Agent Responsibilities

### Codex
- Orchestrator architecture
- Backend services
- API endpoints
- Testing (unit, integration, e2e)
- Deployment (Docker, CI/CD)
- Database schema and migrations

### Gemini
- Frontend UI/UX
- Component design
- Responsive layouts
- Styling (CSS, Tailwind, etc.)
- Client-side behavior
- Accessibility

### Ollama (Qwen)
- Automatic fallback for both Gemini and Codex
- Handles any query when primary agents fail
- No API key required

## Fallback Mechanism

### Trigger Conditions
- Credit exhaustion
- API rate limits
- Network timeouts
- API errors (4xx, 5xx)

### Fallback Process
1. Primary agent (Gemini/Codex) attempts task
2. On failure, orchestrator logs to context.json
3. Automatically switches to Ollama
4. Ollama continues from where primary left off
5. When primary API recovers, system can switch back

## Context Management

All agents share state via `.orchestrator/context.json`:

```json
{
  "completed_stages": [
    {
      "stage": "10_frontend_gemini",
      "agent": "gemini_frontend",
      "model_used": "gemini",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "failures": [
    {
      "stage": "20_backend_codex",
      "agent": "codex_engineering",
      "model_attempted": "codex",
      "reason": "credit exhaustion",
      "timestamp": "2024-01-15T10:35:00Z"
    }
  ],
  "chat_history": [
    {
      "agent": "codex",
      "query": "Build REST API",
      "status": "success",
      "response_preview": "Created API with endpoints..."
    }
  ],
  "user_preferences": {
    "framework": "FastAPI",
    "database": "PostgreSQL"
  }
}
```

## Keyword Detection

### Frontend Keywords → Gemini
- ui, ux, frontend, react, vue, angular
- css, html, component, layout, design
- responsive, accessibility, button, form
- input, navigation, menu, style, page

### Backend/Orchestrator/Testing/Deploy Keywords → Codex
- orchestrator, backend, api, database
- server, deploy, docker, test, testing
- architecture, endpoint, auth, security
- migration, schema, persistence, integration
- deployment, release, build, ci, cd, pipeline

### Default
All other queries → Codex (or Ollama if unavailable)

## Stage Execution Flow

```
1. Orchestrator.plan()
   ├─→ Load orchestrator.toml
   ├─→ Generate task files with context
   └─→ Create run directory

2. Orchestrator.run()
   ├─→ For each stage:
   │   ├─→ Determine agent (from config)
   │   ├─→ Try primary model
   │   ├─→ If fails → Try fallback (Ollama)
   │   └─→ Record result in context.json
   │
   └─→ Continue until all stages complete

3. Completion
   └─→ All work documented in:
       ├─→ .orchestrator/context.json
       ├─→ .orchestrator/notes/*.md
       └─→ .orchestrator/runs/<timestamp>/
```

## Benefits

1. **Resilience** - Never stalls on API failures
2. **Continuity** - Seamless fallback with shared context
3. **Flexibility** - Works with or without API keys
4. **Transparency** - All decisions logged in context.json
5. **Cost-effective** - Free fallback option (Ollama)
