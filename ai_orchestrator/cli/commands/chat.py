"""Chat command - interactive chat session with the LangGraph coding agent."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import re

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm

from ai_orchestrator import knowledge_graph as kg
from ai_orchestrator.agent_tools import set_confirmation_sink
from ai_orchestrator.agent_tools.confirm import set_os_permission_sink
from ai_orchestrator.core import CodingAgent, HardStopError
from ai_orchestrator.llm import ModelRegistry, UnknownModelError, UnknownProviderError
from ai_orchestrator.skills import list_skills, load_skill

console = Console()

# Tracks the active "thinking..." spinner (if any) so a confirmation prompt
# fired mid-turn (edit_file/write_file/delete_file) can pause it first —
# Rich only supports one live-updating region per console, and a Confirm.ask
# nested inside an active Status blocks on stdin without ever showing its
# prompt, which looks like the agent hanging.
_active_status = None


@contextmanager
def _thinking_status():
    global _active_status
    status = console.status("[dim]thinking...[/dim]", spinner="dots")
    status.start()
    _active_status = status
    try:
        yield
    finally:
        status.stop()
        _active_status = None

_SKILL_MODEL_ROLES = {
    "plan": "planner",
    "build": "coding",
    "debug": "debugging",
    "test": "testing",
    "deploy": "deployment",
}
_DEFAULT_RECURSION_LIMIT = 40
_WORKFLOW_RECURSION_LIMIT = 28
_WORKFLOW_REQUEST_RE = re.compile(
    r"\b("
    r"add|build|change|create|debug|fix|implement|make|modify|refactor|remove|"
    r"update|write"
    r")\b",
    re.IGNORECASE,
)
_NON_RETRYABLE_ERRORS = (
    "HARD STOP:",
    "permission required",
    "Stopped tool loop:",
)
_PLAN_WORKFLOW = (
    (
        "Analyze",
        "planner",
        "Analyze the request and use KG context to identify the likely files and constraints. Keep the plan concise. Do not ask whether to proceed.",
    ),
    (
        "Implement",
        "coding",
        "Implement the smallest coherent code change from the plan and repository findings. Do not ask whether to proceed; use the tool confirmation layer for file edits.",
    ),
    (
        "Verify",
        "testing",
        "Run focused verification, add or adjust tests if needed, and summarize pass/fail results and any remaining blockers. Do not ask whether to proceed.",
    ),
)

HELP_TEXT = """\
[bold]Slash commands[/bold]
  /model                      show the planner/orchestrator model
  /model <provider> [model]   switch the active provider (and optionally model)
  /providers                  show the planner/orchestrator model
  /tools                      list tools available to the agent
  /skills                     list available skills (plan/build/test/deploy/debug)
  /kg                         show knowledge graph stats
  /kg rebuild                 force a full re-index of the project
  /plan <task>                run analyze -> implement -> verify
  /build <task>                work through <task> following the Build skill
  /test [task]                run/write tests following the Test skill
  /deploy [task]               prepare a deployment following the Deploy skill
  /debug <task>                investigate a bug following the Debug skill
  /clear                       start a fresh conversation thread
  /help                        show this help
  /exit, /quit                 end the session
"""


def _confirm_sink(action: str, detail: str) -> bool:
    if _active_status is not None:
        _active_status.stop()
    try:
        return Confirm.ask(f"[yellow]Allow[/yellow] {action}: [bold]{detail}[/bold]?", default=False)
    finally:
        if _active_status is not None:
            _active_status.start()


def _os_permission_sink(action: str, path: str, reason: str) -> bool:
    """Shown when the filesystem itself denies a write (OS PermissionError)."""
    console.print(
        f"\n[bold red]\u26a0 Access Denied[/bold red]  "
        f"Cannot {action} [bold]{path}[/bold]\n"
        f"  [dim]OS reason:[/dim] {reason}"
    )
    return Confirm.ask(
        f"Fix permissions ([bold]chmod u+w {path}[/bold]) and retry?",
        default=False,
    )


class ChatSession:
    """Interactive chat session backed by a tool-using LangGraph agent."""

    def __init__(self, project_dir: Path | None = None):
        self.project_dir = project_dir
        self.workspace_root = (project_dir / "workspace") if project_dir else Path.cwd()
        self.kg_store_dir = project_dir or self.workspace_root

        set_confirmation_sink(_confirm_sink)
        set_os_permission_sink(_os_permission_sink)

        self.registry = ModelRegistry(project_dir)
        self.registry.switch_role("planner")
        self.agent = CodingAgent(
            self.registry,
            workspace_root=self.workspace_root,
            project_dir=project_dir,
        )

    def run(self) -> None:
        planner = self.registry.planner_model()

        kg_line = ""
        with console.status("[dim]indexing project...[/dim]", spinner="dots"):
            graph = kg.build_or_update(self.workspace_root, self.kg_store_dir)
        if graph["files"]:
            kg_line = (
                f"Knowledge graph: [green]{len(graph['files'])}[/green] files, "
                f"[green]{len(graph['edges'])}[/green] import edges\n"
            )

        console.print(
            Panel.fit(
                f"[bold cyan]AI Orchestrator[/bold cyan]\n"
                f"Planner model: [green]{planner.provider}[/green] / [green]{planner.model}[/green]\n"
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

            if self._should_run_workflow(user_input):
                self._run_plan_workflow(user_input)
            else:
                self._send(user_input)

    # ------------------------------------------------------------------

    def _send(
        self,
        message: str,
        model_role: str = "planner",
        recursion_limit: int = _DEFAULT_RECURSION_LIMIT,
    ) -> str | None:
        def on_tool_call(name: str, args: dict) -> None:
            console.print(f"  [dim]tool:[/dim] [magenta]{name}[/magenta]({args})")

        try:
            self.registry.switch_role(model_role)
            self.agent.rebuild()
            with _thinking_status():
                response = self.agent.send(
                    message,
                    on_tool_call=on_tool_call,
                    recursion_limit=recursion_limit,
                )
        except Exception as exc:
            if self._is_non_retryable_error(exc):
                console.print(f"[red]{exc}[/red]")
                return None
            response = self._retry_with_fallback(
                message,
                exc,
                on_tool_call,
                model_role,
                recursion_limit,
            )
            if response is None:
                return None

        console.print(Markdown(response))
        return response

    def _retry_with_fallback(
        self,
        message: str,
        exc: Exception,
        on_tool_call,
        model_role: str,
        recursion_limit: int,
    ) -> str | None:
        """If the active model errored out, try the next role candidate once."""
        current = self.registry.current()
        candidates = [
            route for route in self.registry.role_candidates(model_role)
            if (route.provider, route.model) != current
        ]
        if not candidates:
            console.print(f"[red]Error:[/red] {exc}")
            return None

        fallback = candidates[0]
        console.print(
            f"[yellow]{current[0]}:{current[1]} failed ({exc}); "
            f"switching to {fallback.label} and retrying...[/yellow]"
        )
        self.registry.switch(fallback.provider, fallback.model)
        self.agent.clear_history()
        self.agent.rebuild()

        try:
            with _thinking_status():
                return self.agent.send(
                    message,
                    on_tool_call=on_tool_call,
                    recursion_limit=recursion_limit,
                )
        except Exception as exc2:
            console.print(f"[red]Error:[/red] {exc2}")
            return None

    def _is_non_retryable_error(self, exc: Exception) -> bool:
        if isinstance(exc, HardStopError):
            return True
        text = str(exc)
        return any(marker in text for marker in _NON_RETRYABLE_ERRORS)

    def _run_plan_workflow(self, task: str) -> None:
        original_task = task or "(continue the current work)"
        context = f"Original user task:\n{original_task}"
        for index, (label, role, instruction) in enumerate(_PLAN_WORKFLOW, start=1):
            console.print(f"\n[bold cyan]{index}. {label}[/bold cyan] [dim]({role})[/dim]")
            message = (
                f"{instruction}\n\n"
                f"Original user task for KG resolution:\n{original_task}\n\n"
                "Workflow context from previous steps:\n"
                f"{context}\n\n"
                "Before reading files, folders, or code, use the injected KG resolver results "
                "or call resolve_issue with the original user task. Read KG-ranked files first.\n\n"
                "Keep this step bounded. If you hit uncertainty, record the assumption and continue. "
                "Never end by asking the user whether to continue."
            )
            response = self._send(message, role, recursion_limit=_WORKFLOW_RECURSION_LIMIT)
            if response is None:
                console.print(f"[red]Workflow stopped during {label}.[/red]")
                return
            context = f"{context}\n\n---\n{label} result:\n{response}"

    def _should_run_workflow(self, message: str) -> bool:
        """Use the full capability workflow for ordinary implementation requests."""
        lowered = message.lower().strip()
        if lowered.startswith(("how ", "why ", "what ", "explain ", "show me ")):
            return False
        return bool(_WORKFLOW_REQUEST_RE.search(message))

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
            self._print_model_status()
            return False

        if cmd == "/skills":
            for name in list_skills():
                console.print(f"  - {name}")
            return False

        if cmd == "/kg":
            if len(parts) > 1 and parts[1] == "rebuild":
                with console.status("[dim]re-indexing...[/dim]", spinner="dots"):
                    graph = kg.build_or_update(self.workspace_root, None)  # bypass cache
                    kg.save_graph(self.kg_store_dir, graph)
            else:
                graph = kg.load_graph(self.kg_store_dir)
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
            if skill_name == "plan":
                self._run_plan_workflow(task)
                return False
            skill_text = load_skill(skill_name)
            message = f"Follow these instructions:\n\n{skill_text}\n\n---\nTask: {task or '(continue the current work)'}"
            self._send(message, _SKILL_MODEL_ROLES.get(skill_name, "planner"))
            return False

        if cmd == "/model":
            if len(parts) == 1:
                self._print_model_status()
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

    def _print_model_status(self) -> None:
        route = self.registry.planner_model()
        console.print(
            f"Planner/orchestrator: [green]{route.provider}[/green] / [green]{route.model}[/green]"
        )
        console.print("Visible model:")
        for provider_name, models in self.registry.list_visible_models().items():
            console.print(f"  [bold]{provider_name}[/bold]")
            for model_name in models:
                active = (
                    " [green](orchestrator)[/green]"
                    if (provider_name, model_name) == (route.provider, route.model)
                    else ""
                )
                console.print(f"    - {model_name}{active}")
        console.print("Switch with: [bold]/model <provider> [model][/bold]")


def handle_chat(project_dir: Path | None = None) -> None:
    """Handle the chat command - start interactive chat session."""
    try:
        session = ChatSession(project_dir)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        return
    session.run()
