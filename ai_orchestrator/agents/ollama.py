"""Ollama local model agent integration."""

from __future__ import annotations

import subprocess

from .base import AIAgent


class OllamaAgent(AIAgent):
    """Ollama local model agent with professional context."""
    
    def __init__(self, model: str = "qwen2.5-coder", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    def send_message(self, prompt: str, context: list[dict[str, str]] | None = None) -> str:
        """Send message to Ollama with context."""
        try:
            # Build context-aware prompt
            full_prompt = self._build_prompt(prompt, context)
            
            result = subprocess.run(
                ["ollama", "run", self.model],
                input=full_prompt,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,  # 2 minute timeout
            )
            
            if result.returncode == 0:
                response = result.stdout.strip()
                is_valid, reason = self.validate_response(response)
                if is_valid:
                    return response
                else:
                    return f"Error: Invalid response - {reason}"
            else:
                return f"Error: Ollama returned exit code {result.returncode}: {result.stderr.strip()}"
        
        except subprocess.TimeoutExpired:
            return "Error: Request timed out after 2 minutes"
        except FileNotFoundError:
            return "Error: Ollama CLI not found. Install from https://ollama.ai"
        except Exception as e:
            return f"Error: Unexpected error - {str(e)}"
    
    def _build_prompt(self, prompt: str, context: list[dict[str, str]] | None) -> str:
        """Build prompt with conversation context."""
        if not context:
            return prompt
        
        # Add recent context (last 5 messages)
        recent_context = context[-5:] if len(context) > 5 else context
        
        prompt_parts = ["Previous conversation:"]
        for msg in recent_context:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            prompt_parts.append(f"{role}: {content[:200]}...")  # Truncate long messages
        
        prompt_parts.append("\nCurrent query:")
        prompt_parts.append(prompt)
        
        return "\n".join(prompt_parts)
