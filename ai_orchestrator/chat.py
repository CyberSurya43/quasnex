from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

from .env_loader import load_env
from .orchestrator_chat import ChatOrchestrator


class ChatSession:
    """Interactive chat session with orchestrator routing."""
    
    def __init__(self, project_dir: Path | None = None):
        self.project_dir = project_dir
        self.orchestrator = ChatOrchestrator(project_dir)
        self.history: list[dict[str, str]] = []
    
    def run(self) -> None:
        """Start interactive chat loop."""
        print("AI Orchestrator Chat")
        print("The orchestrator will route your query to the appropriate agent.")
        print(f"Available agents: {', '.join(self.orchestrator.get_available_agents())}")
        print("\nType 'exit' or 'quit' to end session")
        print("Type 'clear' to clear conversation history\n")
        
        while True:
            try:
                user_input = input("\nyou> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ("exit", "quit", "q"):
                    print("Goodbye!")
                    break
                
                if user_input.lower() == "clear":
                    self.history.clear()
                    print("Conversation history cleared.")
                    continue
                
                self.history.append({"role": "user", "content": user_input})
                
                # Route query through orchestrator
                agent_name, response = self.orchestrator.route_query(user_input, self.history)
                
                print(f"\n[{agent_name}] {response}")
                
                self.history.append({"role": "assistant", "content": response, "agent": agent_name})
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except EOFError:
                break


def start_chat(project_dir: Path | None = None) -> None:
    """Start interactive chat session with orchestrator."""
    session = ChatSession(project_dir)
    session.run()
