#!/usr/bin/env python3
"""Initialize an Obsidian project workflow scaffold."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from vault_utils import resolve_vault_path


SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSETS = SKILL_ROOT / "assets"
INVALID_PROJECT_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
DEFAULT_BOARD_NAME = "任务看板.md"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(content)


def safe_project_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("project name cannot be empty")
    if cleaned in {".", ".."}:
        raise ValueError("project name cannot be . or ..")
    if INVALID_PROJECT_CHARS.search(cleaned):
        raise ValueError("project name must be a single folder name and cannot contain path separators")
    return cleaned


def safe_board_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("board name cannot be empty")
    if not cleaned.endswith(".md"):
        cleaned += ".md"
    if cleaned in {".md", "..md"}:
        raise ValueError("board name cannot be . or ..")
    if INVALID_FILENAME_CHARS.search(cleaned):
        raise ValueError("board name must be a single markdown file name and cannot contain path separators")
    if not cleaned.endswith("任务看板.md"):
        raise ValueError("board name must match '*任务看板.md'")
    return cleaned


def init_project(vault_path: Path, project_name: str, board_name: str, overwrite: bool) -> list[Path]:
    project_name = safe_project_name(project_name)
    board_name = safe_board_name(board_name)
    vault_path = vault_path.expanduser().resolve()
    project_root = vault_path / project_name

    created_or_touched = [
        project_root / "文档",
        project_root / "任务",
        project_root / "任务" / "Tasks",
    ]
    for folder in created_or_touched:
        folder.mkdir(parents=True, exist_ok=True)

    board_template = read_text(ASSETS / "kanban-template.md")
    board = board_template.replace("{{PROJECT_NAME}}", project_name)
    board_path = project_root / "任务" / board_name
    write_text(board_path, board, overwrite=overwrite)

    return [*created_or_touched, board_path]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", help="Path to the Obsidian vault root. Defaults to the active Obsidian vault.")
    parser.add_argument("--project-name", required=True, help="Project folder name to create in the vault.")
    parser.add_argument("--board-name", default=DEFAULT_BOARD_NAME, help="Board file name, matching '*任务看板.md'.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing board file.")
    args = parser.parse_args()

    paths = init_project(resolve_vault_path(args.vault_path), args.project_name, args.board_name, args.overwrite)
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
