from __future__ import annotations

from pathlib import Path
from typing import Any

from ..agents import create_agent, AIAgent
from ..config import load_env, load_config
from . import context as ctx_store
from ..tools.senior_dev import get_agent_instructions


class ChatOrchestrator:
    """Orchestrator that routes user queries to appropriate AI agents with fallback."""
    
    def __init__(self, project_dir: Path | None = None):
        self.project_dir = project_dir or Path.cwd()
        self.env_config = load_env(self.project_dir)
        
        # Load project config if available
        self.config = None
        if (self.project_dir / "orchestrator.toml").exists():
            self.config = load_config(self.project_dir)
        
        # Initialize agents
        self._agents: dict[str, AIAgent] = {}
        self._init_agents()
    
    def _init_agents(self) -> None:
        """Initialize all available agents."""
        # Ollama is always available as fallback
        self._agents["ollama"] = create_agent(
            "ollama", 
            model=self.env_config.ollama_model
        )
        
        # Gemini if API key available
        if self.env_config.gemini_api_key:
            self._agents["gemini"] = create_agent(
                "gemini", 
                api_key=self.env_config.gemini_api_key
            )
        
        # Codex if API key available
        if self.env_config.codex_api_key:
            self._agents["codex"] = create_agent(
                "codex", 
                api_key=self.env_config.codex_api_key
            )
    
    def route_query(self, query: str, context: list[dict[str, str]] | None = None) -> tuple[str, str]:
        """
        Route user query to the appropriate agent with automatic fallback.
        Flow:
        - orchestrator, backend, testing, deploy -> Codex (fallback: Ollama)
        - frontend -> Gemini (fallback: Ollama)
        
        Returns: (agent_name, response)
        """
        # Determine primary agent based on query
        primary_agent = self._determine_agent(query)
        
        # Build fallback chain: primary -> ollama
        agent_chain = [primary_agent]
        if primary_agent != "ollama":
            agent_chain.append("ollama")
        
        # Try agents in order with fallback
        for agent_name in agent_chain:
            if agent_name not in self._agents:
                continue
            
            try:
                # Add project context to the query
                enhanced_query = self._add_project_context(query)
                response = self._agents[agent_name].send_message(enhanced_query, context)
                
                # Check if response indicates failure
                if self._is_failure_response(response):
                    reason = "API error or credit exhaustion"
                    self._record_failure(agent_name, query, reason)
                    print(f"  [fallback] {agent_name} failed: {reason}. Trying next agent...")
                    continue
                
                # Success - record context
                self._record_success(agent_name, query, response)
                return agent_name, response
                
            except Exception as e:
                reason = str(e)
                self._record_failure(agent_name, query, reason)
                print(f"  [fallback] {agent_name} failed: {reason}. Trying next agent...")
                continue
        
        # All agents failed
        return "none", "Error: All agents failed to respond. Please check your configuration."
    
    def _determine_agent(self, query: str) -> str:
        """Determine which agent should handle the query based on content."""
        query_lower = query.lower()
        
        # Frontend-related keywords -> Gemini
        frontend_keywords = [
            "ui", "ux", "frontend", "react", "vue", "angular", "css", "html",
            "component", "layout", "design", "responsive", "accessibility",
            "button", "form", "input", "navigation", "menu", "style", "page"
        ]
        
        # Backend/orchestrator/testing/deploy keywords -> Codex
        codex_keywords = [
            "orchestrator", "backend", "api", "database", "server", "deploy", "docker",
            "test", "testing", "architecture", "endpoint", "auth", "security",
            "migration", "schema", "persistence", "integration", "deployment",
            "release", "build", "ci", "cd", "pipeline"
        ]
        
        # Check for frontend keywords -> Gemini
        if any(keyword in query_lower for keyword in frontend_keywords):
            return "gemini" if "gemini" in self._agents else "ollama"
        
        # Check for backend/orchestrator/testing/deploy keywords -> Codex
        if any(keyword in query_lower for keyword in codex_keywords):
            return "codex" if "codex" in self._agents else "ollama"
        
        # Default: orchestrator/general queries go to Codex (or ollama fallback)
        return "codex" if "codex" in self._agents else "ollama"
    
    def _add_project_context(self, query: str) -> str:
        """Add project context and professional guidelines to the query."""
        if not self.project_dir:
            return query
        
        # Determine agent type for instructions
        agent_type = self._determine_agent(query)
        
        # Build enhanced query with guidelines
        enhanced_parts = [query]
        
        # Add professional guidelines
        instructions = get_agent_instructions(agent_type)
        enhanced_parts.append("\n## Professional Guidelines")
        enhanced_parts.append(instructions)
        
        # Add project context
        context_block = ctx_store.inject_context_block(self.project_dir)
        if context_block:
            enhanced_parts.append(context_block)
        
        return "\n".join(enhanced_parts)
    
    def _is_failure_response(self, response: str) -> bool:
        """Check if response indicates a failure."""
        failure_indicators = [
            "error:", "failed", "not configured", "not found",
            "credit", "quota", "rate limit"
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in failure_indicators)
    
    def _record_success(self, agent_name: str, query: str, response: str) -> None:
        """Record successful agent interaction in project context."""
        if not self.project_dir:
            return
        
        ctx = ctx_store.load(self.project_dir)
        ctx.setdefault("chat_history", []).append({
            "agent": agent_name,
            "query": query[:100],  # Truncate long queries
            "status": "success",
            "response_preview": response[:200]  # Store preview
        })
        ctx_store.save(self.project_dir, ctx)
    
    def _record_failure(self, agent_name: str, query: str, reason: str) -> None:
        """Record failed agent interaction in project context."""
        if not self.project_dir:
            return
        
        ctx = ctx_store.load(self.project_dir)
        ctx.setdefault("chat_failures", []).append({
            "agent": agent_name,
            "query": query[:100],
            "reason": reason
        })
        ctx_store.save(self.project_dir, ctx)
    
    def get_available_agents(self) -> list[str]:
        """Get list of available agents."""
        return list(self._agents.keys())
