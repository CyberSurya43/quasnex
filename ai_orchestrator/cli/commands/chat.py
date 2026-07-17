"""Chat command - interactive chat session with the LangGraph coding agent."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm

from ai_orchestrator import knowledge_graph as kg
from ai_orchestrator.agent_tools import set_confirmation_sink
from ai_orchestrator.core import CodingAgent
from ai_orchestrator.llm import ModelRegistry, UnknownModelError, UnknownProviderError
from ai_orchestrator.skills import list_skills, load_skill

console = Console()

HELP_TEXT = """\
[bold]Slash commands[/bold]
  /model                      show the active provider/model
  /model <provider> [model]   switch the active provider (and optionally model)
  /providers                  list all configured providers and their models
  /tools                      list tools available to the agent
  /skills                     list available skills (plan/build/test/deploy/debug)
  /kg                         show knowledge graph stats
  /kg rebuild                 force a full re-index of the project
  /plan <task>                work through <task> following the Plan skill
  /build <task>                work through <task> following the Build skill
  /test [task]                run/write tests following the Test skill
  /deploy [task]               prepare a deployment following the Deploy skill
  /debug <task>                investigate a bug following the Debug skill
  /clear                       start a fresh conversation thread
  /help                        show this help
  /exit, /quit                 end the session
"""


def _confirm_sink(action: str, detail: str) -> bool:
    return Confirm.ask(f"[yellow]Allow[/yellow] {action}: [bold]{detail}[/bold]?", default=False)


class ChatSession:
    """Interactive chat session backed by a tool-using LangGraph agent."""

    def __init__(self, project_dir: Path | None = None):
        self.project_dir = project_dir
        self.workspace_root = (project_dir / "workspace") if project_dir else Path.cwd()

        set_confirmation_sink(_confirm_sink)

        self.registry = ModelRegistry(project_dir)
        self.agent = CodingAgent(
            self.registry,
            workspace_root=self.workspace_root,
            project_dir=project_dir,
        )

    def run(self) -> None:
        provider, model = self.registry.current()

        kg_line = ""
        with console.status("[dim]indexing project...[/dim]", spinner="dots"):
            graph = kg.build_or_update(self.workspace_root, self.project_dir)
        if graph["files"]:
            kg_line = (
                f"Knowledge graph: [green]{len(graph['files'])}[/green] files, "
                f"[green]{len(graph['edges'])}[/green] import edges\n"
            )

        console.print(
            Panel.fit(
                f"[bold cyan]AI Orchestrator[/bold cyan]\n"
                f"Active model: [green]{provider}[/green] / [green]{model}[/green]\n"
                f"Workspace: [dim]{self.workspace_root}[/dim]\n"
                f"{kg_line}"
                f"Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to quit.",
                border_style="cyan",
            )
        )

        while True:
            try:
                user_input = console.input("\n[bold blue]you>[/bold blue] ").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Goodbye![/dim]")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                if self._handle_command(user_input):
                    break
                continue

            self._send(user_input)

    # ------------------------------------------------------------------

    def _send(self, message: str) -> None:
        def on_tool_call(name: str, args: dict) -> None:
            console.print(f"  [dim]tool:[/dim] [magenta]{name}[/magenta]({args})")

        try:
            with console.status("[dim]thinking...[/dim]", spinner="dots"):
                response = self.agent.send(message, on_tool_call=on_tool_call)
        except Exception as exc:
            response = self._retry_with_fallback(message, exc, on_tool_call)
            if response is None:
                return

        console.print(Markdown(response))

    def _retry_with_fallback(self, message: str, exc: Exception, on_tool_call) -> str | None:
        """If the active provider errored out, try the next configured provider once."""
        candidates = self.registry.other_providers()
        if not candidates:
            console.print(f"[red]Error:[/red] {exc}")
            return None

        fallback = candidates[0]
        console.print(
            f"[yellow]{self.registry.current()[0]} failed ({exc}); "
            f"switching to {fallback} and retrying...[/yellow]"
        )
        self.registry.switch(fallback)
        self.agent.rebuild()

        try:
            with console.status("[dim]thinking...[/dim]", spinner="dots"):
                return self.agent.send(message, on_tool_call=on_tool_call)
        except Exception as exc2:
            console.print(f"[red]Error:[/red] {exc2}")
            return None

    def _handle_command(self, raw: str) -> bool:
        """Return True if the session should end."""
        parts = raw.split()
        cmd = parts[0].lower()

        if cmd in ("/exit", "/quit"):
            console.print("[dim]Goodbye![/dim]")
            return True

        if cmd == "/help":
            console.print(HELP_TEXT)
            return False

        if cmd == "/clear":
            self.agent.clear_history()
            console.print("[dim]Started a fresh conversation thread.[/dim]")
            return False

        if cmd == "/tools":
            for name in self.agent.list_tools():
                console.print(f"  - {name}")
            return False

        if cmd == "/providers":
            for name, models in self.registry.list_available().items():
                console.print(f"[bold]{name}[/bold]: {', '.join(models)}")
            return False

        if cmd == "/skills":
            for name in list_skills():
                console.print(f"  - {name}")
            return False

        if cmd == "/kg":
            if len(parts) > 1 and parts[1] == "rebuild":
                with console.status("[dim]re-indexing...[/dim]", spinner="dots"):
                    graph = kg.build_or_update(self.workspace_root, None)  # bypass cache
                    if self.project_dir:
                        kg.save_graph(self.project_dir, graph)
            else:
                graph = kg.load_graph(self.project_dir) if self.project_dir else None
                if graph is None:
                    console.print("No knowledge graph yet — run [bold]/kg rebuild[/bold].")
                    return False
            console.print(
                f"{len(graph['files'])} files, {len(graph['edges'])} import edges "
                f"(root: {graph['root']})"
            )
            return False

        skill_name = cmd.lstrip("/")
        if skill_name in list_skills():
            task = raw.split(maxsplit=1)[1] if len(parts) > 1 else ""
            skill_text = load_skill(skill_name)
            message = f"Follow these instructions:\n\n{skill_text}\n\n---\nTask: {task or '(continue the current work)'}"
            self._send(message)
            return False

        if cmd == "/model":
            if len(parts) == 1:
                provider, model = self.registry.current()
                console.print(f"Active: [green]{provider}[/green] / [green]{model}[/green]")
                return False
            provider_name = parts[1]
            model_name = parts[2] if len(parts) > 2 else None
            try:
                provider, model = self.registry.switch(provider_name, model_name)
            except (UnknownProviderError, UnknownModelError) as exc:
                console.print(f"[red]Error:[/red] {exc}")
                return False
            self.agent.rebuild()
            console.print(f"Switched to [green]{provider}[/green] / [green]{model}[/green]")
            return False

        console.print(f"[red]Unknown command:[/red] {cmd}. Type /help for a list.")
        return False


def handle_chat(project_dir: Path | None = None) -> None:
    """Handle the chat command - start interactive chat session."""
    try:
        session = ChatSession(project_dir)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        return
    session.run()
