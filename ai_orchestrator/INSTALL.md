# AI Orchestrator - Portable Installation Guide

## Method 1: Copy and Use (No Installation)

The `ai_orchestrator` folder is fully self-contained. Just copy it anywhere:

```bash
# Copy to any location
cp -r ai_orchestrator /path/to/anywhere/

# Use from that location
cd /path/to/anywhere
python3 -m ai_orchestrator init ./my-app --name my-app
python3 -m ai_orchestrator chat
```

## Method 2: Install as Package (Optional)

If you want to use it system-wide:

```bash
# From inside the ai_orchestrator folder
pip install -e .

# Or from outside
pip install -e /path/to/ai_orchestrator/

# Then use anywhere
ai-orchestrator init ./my-app --name my-app
ai-orchestrator chat
```

## Method 3: Distribute as Wheel

Build a distributable package:

```bash
cd ai_orchestrator
python3 setup.py sdist bdist_wheel

# Install the wheel on any machine
pip install dist/ai_orchestrator-0.1.0-py3-none-any.whl
```

## What's Included

The `ai_orchestrator` folder contains everything needed:

```
ai_orchestrator/
├── __init__.py                      # Package initialization
├── __main__.py                      # Entry point for module execution
├── agents.py                        # AI agent implementations
├── chat.py                          # Interactive chat session
├── cli.py                           # Command-line interface
├── config.py                        # Configuration management
├── context.py                       # Shared context storage
├── env_loader.py                    # Environment variable loader
├── orchestrator_chat.py             # Chat orchestrator with routing
├── runner.py                        # Stage execution engine
├── scaffold.py                      # Project scaffolding
├── senior_dev_tools.py              # Professional dev tools & rules
├── templates/                       # Project templates
│   └── web_app/                     # Web app template
│       ├── brief.md
│       ├── orchestrator.toml
│       ├── .env.example
│       └── workspace/
├── examples/                        # Example projects
│   └── task-manager/
├── tests/                           # Test suite
│   ├── test_architecture.py
│   ├── test_orchestrator.py
│   └── test_professional_guidelines.py
├── .env.example                     # Environment template
├── .gitignore                       # Git ignore rules
├── README.md                        # Main documentation
├── QUICKSTART.md                    # Quick start guide
├── ARCHITECTURE.md                  # Architecture details
├── SENIOR_DEV_GUIDELINES.md         # Professional standards
├── PROFESSIONAL_TOOLS_SUMMARY.md    # Tools implementation
├── setup.py                         # Installation script
├── pyproject.toml                   # Modern Python packaging
└── MANIFEST.in                      # Package manifest
```

## Quick Test

After copying to a new location:

```bash
# Test help
python3 -m ai_orchestrator --help

# Test chat
python3 -m ai_orchestrator chat

# Test init
python3 -m ai_orchestrator init ./test-project --name test

# Test professional tools
python3 -c "from ai_orchestrator.senior_dev_tools import DevelopmentTools; print('✓ Tools loaded')"
```

## Requirements

- Python 3.11+
- Ollama (optional, for local fallback)
- API keys for Gemini/Codex (optional, Ollama works without)

## No External Dependencies

The orchestrator has zero external Python dependencies. It uses only standard library modules:
- `pathlib` - File system operations
- `subprocess` - Command execution
- `json` - Data serialization
- `argparse` - CLI parsing
- `dataclasses` - Data structures
- `tomllib` - TOML parsing (Python 3.11+)

## Verify Portability

Test that everything works after copying:

```bash
# Copy to /tmp
cp -r ai_orchestrator /tmp/

# Test from /tmp
cd /tmp
python3 -m ai_orchestrator init ./my-test --name my-test

# Should create project successfully ✓
```

## Share with Team

Compress and share:

```bash
tar -czf ai_orchestrator.tar.gz ai_orchestrator/
# Share ai_orchestrator.tar.gz

# Team member extracts and uses:
tar -xzf ai_orchestrator.tar.gz
cd ai_orchestrator
python3 -m ai_orchestrator chat
```

## Docker Usage

Run in Docker:

```bash
# Create Dockerfile
cat > Dockerfile <<EOF
FROM python:3.11-slim
COPY ai_orchestrator /app/ai_orchestrator
WORKDIR /app
CMD ["python3", "-m", "ai_orchestrator", "chat"]
EOF

# Build and run
docker build -t ai-orchestrator .
docker run -it ai-orchestrator
```

The `ai_orchestrator` folder is completely portable and self-contained! 🚀
