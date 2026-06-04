from __future__ import annotations

from pathlib import Path
import shutil


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "web_app"


def init_project(target_dir: Path, name: str | None = None, force: bool = False) -> None:
    target_dir = target_dir.resolve()
    if target_dir.exists() and any(target_dir.iterdir()) and not force:
        raise FileExistsError(f"{target_dir} is not empty. Use --force to merge template files.")

    target_dir.mkdir(parents=True, exist_ok=True)
    for source in TEMPLATE_DIR.rglob("*"):
        relative = source.relative_to(TEMPLATE_DIR)
        destination = target_dir / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        if destination.exists() and not force:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    if name:
        config_path = target_dir / "orchestrator.toml"
        config = config_path.read_text(encoding="utf-8")
        config = config.replace('name = "new-web-application"', f'name = "{name}"')
        config_path.write_text(config, encoding="utf-8")
