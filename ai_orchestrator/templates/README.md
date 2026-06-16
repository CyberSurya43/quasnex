# Project Templates

This folder contains reusable project templates for initializing new orchestration projects.

## Available Templates

### web_app
A complete web application template with:
- Frontend configuration (Gemini agent)
- Backend configuration (Codex agent)
- Deployment setup
- Professional development guidelines
- Security best practices

**Usage:**
```bash
python -m ai_orchestrator init ./my-app --name my-app
```

This will copy the `web_app` template to your project directory and configure it with your project name.

## Creating Custom Templates

To create a new template:

1. Create a new directory under `templates/` (e.g., `templates/my-template/`)
2. Add your configuration files:
   - `orchestrator.toml` - Project configuration and stage definitions
   - `brief.md` - Product brief and requirements
   - `workspace/` - Initial workspace structure
3. Copy `.env.example` to `workspace/` for API key configuration

Templates are copied during project initialization using the `init_project` function.
