#!/bin/bash
# AI Orchestrator Portability Test
# Run this from the scripts/ directory

set -e

echo "======================================"
echo "AI Orchestrator Portability Test"
echo "======================================"
echo

# Get the ai_orchestrator directory (parent's sibling of scripts/)
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/ai_orchestrator"

# Test 1: Copy to temp location
echo "1. Testing portability (copying to /tmp)..."
rm -rf /tmp/ai_orchestrator
cp -r "$SOURCE_DIR" /tmp/ai_orchestrator
cd /tmp
echo "✓ Successfully copied to /tmp/ai_orchestrator"
echo

# Test 2: Test CLI help
echo "2. Testing CLI help..."
python3 -m ai_orchestrator --help > /dev/null
echo "✓ CLI works"
echo

# Test 3: Test chat help
echo "3. Testing chat command..."
python3 -m ai_orchestrator chat --help > /dev/null
echo "✓ Chat command works"
echo

# Test 4: Test init command
echo "4. Testing init command..."
rm -rf /tmp/test_project
python3 -m ai_orchestrator init /tmp/test_project --name test > /dev/null 2>&1
if [ -d "/tmp/test_project" ]; then
    echo "✓ Init creates projects"
else
    echo "✗ Init failed"
    exit 1
fi
echo

# Test 5: Test professional tools
echo "5. Testing professional tools..."
python3 <<EOF
from ai_orchestrator.tools.senior_dev import DevelopmentTools, get_agent_instructions
print(f"✓ Code Review: {len(DevelopmentTools.get_code_review_checklist())} items")
print(f"✓ Security: {len(DevelopmentTools.get_security_checklist())} items")
print(f"✓ Codex Instructions: {len(get_agent_instructions('codex'))} chars")
EOF
echo

# Test 6: Test agents
echo "6. Testing agent system..."
python3 <<EOF
from ai_orchestrator.agents import create_agent
agent = create_agent("ollama", model="qwen2.5-coder")
print(f"✓ Ollama agent created: {agent.__class__.__name__}")
EOF
echo

# Test 7: Verify structure
echo "7. Verifying folder structure..."
cd /tmp/ai_orchestrator
if [ -f "README.md" ] && [ -d "cli" ] && [ -d "templates" ]; then
    echo "✓ All key files and folders present"
else
    echo "✗ Missing files"
    exit 1
fi
echo

echo "======================================"
echo "All portability tests PASSED! ✓"
echo "======================================"
echo
echo "The ai_orchestrator folder is fully portable."
echo "Copy it anywhere and run: python3 -m ai_orchestrator"
