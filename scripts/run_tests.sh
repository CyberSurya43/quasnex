#!/bin/bash
# Run test suite for Quasnex

set -e

echo "Running Quasnex Test Suite"
echo "=================================="
echo ""

# Run unit tests
echo "Running unit tests..."
python3 -m pytest tests/unit/ -v

echo ""
echo "=================================="
echo "All tests passed! ✓"
