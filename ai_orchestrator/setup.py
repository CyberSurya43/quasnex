#!/usr/bin/env python3
"""
Setup script for AI Orchestrator.

This makes the ai_orchestrator folder fully portable and installable.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="ai-orchestrator",
    version="0.1.0",
    description="Portable AI agent orchestration framework for building web applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AI Orchestrator Team",
    python_requires=">=3.11",
    packages=find_packages(),
        install_requires=[
        "requests>=2.31.0",
    ],
    include_package_data=True,
    package_data={
        "ai_orchestrator": [
            "templates/**/*",
            "templates/**/**/*",
            "examples/**/*",
            "examples/**/**/*",
            "*.md",
            ".env.example",
            ".gitignore",
        ],
    },
    entry_points={
        "console_scripts": [
            "ai-orchestrator=ai_orchestrator.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
