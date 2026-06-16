#!/usr/bin/env python3
"""Test script to verify orchestrator fallback architecture."""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_orchestrator.orchestrator_chat import ChatOrchestrator


def test_agent_routing():
    """Test that queries route to correct agents."""
    print("Testing Agent Routing...")
    print("=" * 60)
    
    orchestrator = ChatOrchestrator()
    
    test_cases = [
        # Frontend queries -> Gemini
        ("How do I style a button?", "gemini"),
        ("Create a React component", "gemini"),
        ("Design a responsive layout", "gemini"),
        
        # Backend/orchestrator/testing/deploy queries -> Codex
        ("Build a REST API", "codex"),
        ("Set up database schema", "codex"),
        ("Write unit tests", "codex"),
        ("Deploy with Docker", "codex"),
        ("Create orchestrator flow", "codex"),
        
        # General queries -> Codex (default)
        ("What is the project status?", "codex"),
    ]
    
    for query, expected_agent in test_cases:
        determined_agent = orchestrator._determine_agent(query)
        # If expected agent not available, should fallback to ollama
        if expected_agent not in orchestrator.get_available_agents():
            expected_agent = "ollama"
        
        status = "✓" if determined_agent == expected_agent else "✗"
        print(f"{status} Query: '{query}'")
        print(f"  Expected: {expected_agent}, Got: {determined_agent}")
        print()


def test_fallback_chain():
    """Test that fallback chain is correct."""
    print("\nTesting Fallback Chain...")
    print("=" * 60)
    
    orchestrator = ChatOrchestrator()
    available = orchestrator.get_available_agents()
    
    print(f"Available agents: {', '.join(available)}")
    print()
    
    # Verify ollama is always available
    if "ollama" in available:
        print("✓ Ollama (fallback) is available")
    else:
        print("✗ WARNING: Ollama fallback not available!")
    
    if "gemini" in available:
        print("✓ Gemini is configured")
    else:
        print("⚠ Gemini not configured (will fallback to Ollama)")
    
    if "codex" in available:
        print("✓ Codex is configured")
    else:
        print("⚠ Codex not configured (will fallback to Ollama)")
    
    print("\nFallback Flow:")
    print("  Frontend query: Gemini → Ollama (if Gemini fails)")
    print("  Backend/orchestrator/test/deploy query: Codex → Ollama (if Codex fails)")


def test_context_integration():
    """Test that context management is integrated."""
    print("\n\nTesting Context Integration...")
    print("=" * 60)
    
    orchestrator = ChatOrchestrator()
    
    # Check if context methods exist
    methods = ["_record_success", "_record_failure", "_add_project_context"]
    
    for method in methods:
        if hasattr(orchestrator, method):
            print(f"✓ {method} is implemented")
        else:
            print(f"✗ {method} is missing")


if __name__ == "__main__":
    print("AI Orchestrator Architecture Test")
    print("=" * 60)
    print()
    
    test_agent_routing()
    test_fallback_chain()
    test_context_integration()
    
    print("\n" + "=" * 60)
    print("Test complete!")
