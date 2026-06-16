# Example Projects

This folder contains example orchestration projects demonstrating how to use the AI Orchestrator framework.

## Available Examples

### task-manager
A simple task management application example showing:
- How to structure a project brief
- Typical agent responsibilities
- Expected outputs and deliverables

**Using this example:**
1. Review `brief.md` to understand the product requirements
2. Study how stages are defined in the project configuration
3. Use this as a reference when creating your own projects

## Running Examples

To use an example as a starting point for your project:

```bash
# Copy the example
cp -r examples/task-manager ./my-task-app

# Initialize as an orchestration project
python -m ai_orchestrator init ./my-task-app --name "My Task App" --force

# Plan the orchestration
python -m ai_orchestrator plan ./my-task-app

# View the generated tasks
ls ./my-task-app/.orchestrator/runs/*/tasks/
```

## Creating New Examples

To add a new example:

1. Create a new directory under `examples/` (e.g., `examples/my-project/`)
2. Include a `brief.md` with product requirements and project overview
3. Document the project's architecture and key decisions
4. Optionally include sample files showing expected outputs

Examples help users understand project structure and demonstrate best practices.
