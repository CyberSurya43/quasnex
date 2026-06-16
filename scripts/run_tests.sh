#!/bin/bash
# Run test suite for AI Orchestrator

set -e

echo "Running AI Orchestrator Test Suite"
echo "=================================="
echo ""

# Run unit tests
echo "Running unit tests..."
python3 -m pytest tests/unit/ -v

echo ""
echo "=================================="
echo "All tests passed! ✓"
