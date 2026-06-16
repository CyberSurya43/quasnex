#!/usr/bin/env python3
"""Test professional guidelines integration."""

from pathlib import Path
import sys

from ai_orchestrator.tools.senior_dev import (
    DevelopmentRules,
    DevelopmentTools,
    get_agent_instructions,
    get_rules_for_stage,
)


def test_development_rules():
    """Test that all development rules are defined."""
    print("Testing Development Rules...")
    print("=" * 60)
    
    rules = [
        ("Code Quality", DevelopmentRules.CODE_QUALITY),
        ("Security", DevelopmentRules.SECURITY),
        ("Testing", DevelopmentRules.TESTING),
        ("Frontend", DevelopmentRules.FRONTEND),
        ("Backend", DevelopmentRules.BACKEND),
        ("Deployment", DevelopmentRules.DEPLOYMENT),
    ]
    
    for name, rule in rules:
        if rule and len(rule) > 100:
            print(f"✓ {name} rules defined ({len(rule)} chars)")
        else:
            print(f"✗ {name} rules missing or too short")


def test_checklists():
    """Test that all checklists are complete."""
    print("\nTesting Checklists...")
    print("=" * 60)
    
    checklists = [
        ("Code Review", DevelopmentTools.get_code_review_checklist(), 10),
        ("Testing", DevelopmentTools.get_testing_checklist(), 10),
        ("Deployment", DevelopmentTools.get_deployment_checklist(), 10),
        ("Security", DevelopmentTools.get_security_checklist(), 12),
    ]
    
    for name, checklist, expected_min in checklists:
        count = len(checklist)
        if count >= expected_min:
            print(f"✓ {name} checklist: {count} items")
        else:
            print(f"✗ {name} checklist: {count} items (expected >= {expected_min})")


def test_agent_instructions():
    """Test agent-specific instructions."""
    print("\nTesting Agent Instructions...")
    print("=" * 60)
    
    agents = ["codex", "gemini", "backend", "frontend"]
    
    for agent in agents:
        instructions = get_agent_instructions(agent)
        if instructions and len(instructions) > 500:
            print(f"✓ {agent.capitalize()} instructions: {len(instructions)} chars")
        else:
            print(f"✗ {agent.capitalize()} instructions missing or too short")


def test_stage_rules():
    """Test stage-specific rules."""
    print("\nTesting Stage-Specific Rules...")
    print("=" * 60)
    
    stages = [
        "10_frontend_gemini",
        "20_backend_codex",
        "40_testing_codex",
        "50_deployment_codex",
    ]
    
    for stage in stages:
        rules = get_rules_for_stage(stage)
        if rules and len(rules) > 100:
            print(f"✓ {stage} rules: {len(rules)} chars")
        else:
            print(f"✗ {stage} rules missing or too short")


def test_project_structures():
    """Test project structure templates."""
    print("\nTesting Project Structures...")
    print("=" * 60)
    
    project_types = ["backend", "frontend"]
    
    for ptype in project_types:
        structure = DevelopmentTools.get_project_structure_template(ptype)
        dirs = structure.get("directories", [])
        if len(dirs) >= 10:
            print(f"✓ {ptype.capitalize()} structure: {len(dirs)} directories")
        else:
            print(f"✗ {ptype.capitalize()} structure incomplete")


if __name__ == "__main__":
    print("Professional Guidelines Test")
    print("=" * 60)
    print()
    
    test_development_rules()
    test_checklists()
    test_agent_instructions()
    test_stage_rules()
    test_project_structures()
    
    print("\n" + "=" * 60)
    print("Test complete!")
