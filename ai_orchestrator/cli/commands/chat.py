"""Chat command - interactive chat session with the LangGraph coding agent."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import re

from rich import box
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from ai_orchestrator import knowledge_graph as kg
from ai_orchestrator.agent_tools import set_confirmation_sink
from ai_orchestrator.agent_tools.confirm import set_os_permission_sink
from ai_orchestrator.core import CodingAgent, HardStopError, MIN_RECURSION_LIMIT
from ai_orchestrator.llm import ModelRegistry, UnknownModelError, UnknownProviderError
from ai_orchestrator.skills import list_skills, load_skill
from ai_orchestrator.cli.ui import APP_NAME, TAGLINE, console

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
_DEFAULT_RECURSION_LIMIT = MIN_RECURSION_LIMIT
_WORKFLOW_RECURSION_LIMIT = MIN_RECURSION_LIMIT
_WORKFLOW_REQUEST_RE = re.compile(
    r"\b("
    r"add|build|change|create|debug|fix|implement|make|modify|refactor|remove|"
    r"update|write"
    r")\b",
    re.IGNORECASE,
)
_NON_RETRYABLE_ERRORS = (
    "HARD STOP:",
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

_HELP_COMMANDS = (
    ("Models", "/model", "Choose from models configured in .env"),
    ("Models", "/model list", "List all configured models"),
    ("Models", "/model <provider> [model]", "Switch directly"),
    ("Workspace", "/kg [rebuild]", "Inspect or rebuild the knowledge graph"),
    ("Workspace", "/tools", "List agent tools"),
    ("Workspace", "/skills", "List available workflows"),
    ("Workflows", "/plan <task>", "Analyze, implement, and verify"),
    ("Workflows", "/build <task>", "Build with the coding workflow"),
    ("Workflows", "/debug <task>", "Investigate and fix a bug"),
    ("Workflows", "/test [task]", "Run or write tests"),
    ("Workflows", "/deploy [task]", "Prepare a deployment"),
    ("Session", "/clear", "Start a fresh conversation"),
    ("Session", "/exit", "Close ForgeFlow"),
)


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

        with console.status("[dim]indexing project...[/dim]", spinner="dots"):
            graph = kg.build_or_update(self.workspace_root, self.kg_store_dir)

        overview = Table.grid(padding=(0, 2))
        overview.add_column(style="forge.muted", justify="right")
        overview.add_column()
        overview.add_row("MODEL", Text(f"{planner.provider} / {planner.model}", style="green"))
        overview.add_row("WORKSPACE", Text(str(self.workspace_root), style="forge.path"))
        if graph["files"]:
            overview.add_row(
                "INDEX",
                Text(f"{len(graph['files'])} files  •  {len(graph['edges'])} import edges", style="cyan"),
            )
        else:
            overview.add_row("INDEX", Text("No source files indexed", style="forge.warning"))
        overview.add_row("COMMANDS", Text("/help  •  /model  •  /exit", style="bright_magenta"))

        console.print()
        console.print(
            Panel(
                overview,
                title=f"[forge.brand]◆ {APP_NAME.upper()}[/forge.brand]",
                subtitle=f"[forge.muted]{TAGLINE}[/forge.muted]",
                border_style="bright_cyan",
                padding=(1, 3),
            )
        )

        while True:
            try:
                user_input = console.input(
                    "\n[forge.brand]you[/forge.brand] [forge.accent]›[/forge.accent] "
                ).strip()
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
                # A model selected with /model remains active for ordinary chat.
                # Capability workflows still select their configured role model.
                self._send(user_input, preserve_active=True)

    # ------------------------------------------------------------------

    def _send(
        self,
        message: str,
        model_role: str = "planner",
        recursion_limit: int = _DEFAULT_RECURSION_LIMIT,
        *,
        preserve_active: bool = False,
    ) -> str | None:
        def on_tool_call(name: str, args: dict) -> None:
            console.print(f"  [dim]tool:[/dim] [magenta]{name}[/magenta]({args})")

        try:
            if not preserve_active:
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

        self._print_verification()
        console.print(
            Panel(
                Markdown(response),
                title=f"[forge.brand]{APP_NAME}[/forge.brand]",
                title_align="left",
                border_style="bright_cyan",
                padding=(1, 2),
            )
        )
        return response

    def _print_verification(self) -> None:
        verification = self.agent.last_verification
        if verification is None:
            return
        if not verification.attempted:
            console.print(
                "[dim]No test command detected for this project — changes were not auto-verified.[/dim]"
            )
        elif not verification.ran:
            console.print(f"[dim]Verification skipped: user declined to run `{verification.command}`.[/dim]")
        elif verification.passed:
            console.print(f"[green]✓ Verified:[/green] `{verification.command}` passed.")
        else:
            console.print(
                f"[red]✗ Verification failed:[/red] `{verification.command}` still failing "
                "after auto-fix attempts."
            )

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
            console.print(
                Rule(
                    f"[forge.brand]{index}. {label}[/forge.brand] [forge.muted]{role}[/forge.muted]",
                    style="bright_cyan",
                    align="left",
                )
            )
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
            self._print_help()
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
                self._select_model_interactively()
                return False
            if parts[1].lower() == "list":
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
        current = self.registry.current()
        route = self.registry.planner_model()
        table = Table(
            title="Models configured in .env",
            title_style="forge.brand",
            box=box.ROUNDED,
            border_style="bright_cyan",
            header_style="bold bright_magenta",
            show_lines=False,
        )
        table.add_column("#", justify="right", style="cyan", width=4)
        table.add_column("Provider", style="bold")
        table.add_column("Model", overflow="fold")
        table.add_column("Status", justify="center")
        index = 1
        for provider_name, models in self.registry.list_available().items():
            for model_name in models:
                status = (
                    "[forge.success]● active[/forge.success]"
                    if (provider_name, model_name) == current
                    else "[forge.muted]available[/forge.muted]"
                )
                table.add_row(str(index), Text(provider_name), Text(model_name), status)
                index += 1
        console.print(table)
        console.print(
            f"[forge.muted]Planner route:[/forge.muted] {route.provider} / {route.model}  "
            "[forge.muted]•[/forge.muted]  Choose with [bold]/model[/bold]"
        )

    def _print_help(self) -> None:
        table = Table(
            title=f"{APP_NAME} command palette",
            title_style="forge.brand",
            box=box.ROUNDED,
            border_style="bright_cyan",
            header_style="bold bright_magenta",
            expand=False,
        )
        table.add_column("Group", style="forge.muted", no_wrap=True)
        table.add_column("Command", style="bold cyan", no_wrap=True)
        table.add_column("What it does")
        previous_group = None
        for group, command, description in _HELP_COMMANDS:
            table.add_row(group if group != previous_group else "", command, description)
            previous_group = group
        console.print(table)

    def _select_model_interactively(self) -> None:
        choices = [
            (provider_name, model_name)
            for provider_name, models in self.registry.list_available().items()
            for model_name in models
        ]
        self._print_model_status()
        if not choices:
            console.print("[red]No models are configured.[/red]")
            return

        try:
            raw_choice = console.input(
                f"Select model [bold](1-{len(choices)})[/bold] "
                "([dim]Enter to cancel[/dim]): "
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Model selection cancelled.[/dim]")
            return
        if not raw_choice:
            console.print("[dim]Model selection cancelled.[/dim]")
            return
        try:
            choice_index = int(raw_choice) - 1
        except ValueError:
            choice_index = -1
        if choice_index not in range(len(choices)):
            console.print(
                f"[red]Invalid selection.[/red] Enter a number from 1 to {len(choices)}."
            )
            return

        provider, model = choices[choice_index]
        self.registry.switch(provider, model)
        self.agent.rebuild()
        console.print(f"Switched to [green]{provider}[/green] / [green]{model}[/green]")


def handle_chat(project_dir: Path | None = None) -> None:
    """Handle the chat command - start interactive chat session."""
    try:
        session = ChatSession(project_dir)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        return
    session.run()
