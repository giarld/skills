#!/usr/bin/env python3
"""Create a task note and insert a linked card into the project Kanban board."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

from board_utils import board_has_task_card, is_horizontal_rule
from vault_utils import resolve_vault_path


SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSETS = SKILL_ROOT / "assets"
VALID_COLUMNS = {"需求池", "待执行", "执行中", "Review", "完成", "Archive"}
INVALID_PROJECT_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
DEFAULT_BOARD_NAME = "任务看板.md"


def safe_project_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("project name cannot be empty")
    if cleaned in {".", ".."}:
        raise ValueError("project name cannot be . or ..")
    if INVALID_PROJECT_CHARS.search(cleaned):
        raise ValueError("project name must be a single folder name and cannot contain path separators")
    return cleaned


def safe_note_name(title: str) -> str:
    cleaned = INVALID_FILENAME_CHARS.sub("-", title.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        raise ValueError("task title cannot be empty")
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


def resolve_board_path(project_root: Path, board_name: str | None) -> Path:
    planning_dir = project_root / "任务"
    if board_name:
        return planning_dir / safe_board_name(board_name)

    default_path = planning_dir / DEFAULT_BOARD_NAME
    if default_path.exists():
        return default_path

    matches = sorted(planning_dir.glob("*任务看板.md"))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(f"board not found: {planning_dir / '*任务看板.md'}")
    names = ", ".join(path.name for path in matches)
    raise ValueError(f"multiple board files found, pass --board-name: {names}")


def yaml_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_utf8(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(content)


def insert_card(board: str, column: str, card_line: str) -> str:
    if card_line in board:
        return board

    lines = board.splitlines()
    heading = f"## {column}"
    try:
        start = lines.index(heading) + 1
    except ValueError as exc:
        raise ValueError(f"board column not found: {column}") from exc

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break

    section = lines[start:end]
    tail_start = len(section)
    while tail_start and not section[tail_start - 1].strip():
        tail_start -= 1

    divider_start = tail_start
    if divider_start and is_horizontal_rule(section[divider_start - 1]):
        divider_start -= 1

    content = section[:divider_start]
    tail = section[divider_start:]
    while content and not content[-1].strip():
        content.pop()

    content.extend(["", card_line, ""])
    lines[start:end] = [*content, *tail]
    return "\n".join(lines).rstrip() + "\n"


def create_task(
    vault_path: Path,
    project_name: str,
    title: str,
    column: str,
    owner: str,
    agent_role: str,
    priority: str,
    overwrite: bool,
    board_name: str | None,
) -> tuple[Path, Path]:
    if column not in VALID_COLUMNS:
        raise ValueError(f"invalid column: {column}")

    project_name = safe_project_name(project_name)
    note_name = safe_note_name(title)
    vault_path = vault_path.expanduser().resolve()
    project_root = vault_path / project_name
    tasks_dir = project_root / "任务" / "Tasks"
    board_path = resolve_board_path(project_root, board_name)
    note_path = tasks_dir / f"{note_name}.md"

    if not board_path.exists():
        raise FileNotFoundError(f"board not found: {board_path}")

    today = dt.date.today().isoformat()
    template = (ASSETS / "task-note-template.md").read_text(encoding="utf-8")
    content = template
    content = content.replace('title: "{{TASK_TITLE}}"', f"title: {yaml_string(title)}")
    content = content.replace('project: "{{PROJECT_NAME}}"', f"project: {yaml_string(project_name)}")
    content = content.replace('status: "需求池"', f"status: {yaml_string(column)}")
    content = content.replace('owner: ""', f"owner: {yaml_string(owner)}")
    content = content.replace('agent_role: ""', f"agent_role: {yaml_string(agent_role)}")
    content = content.replace('priority: ""', f"priority: {yaml_string(priority)}")
    content = content.replace('created: "{{DATE}}"', f"created: {yaml_string(today)}")
    content = content.replace('updated: "{{DATE}}"', f"updated: {yaml_string(today)}")
    content = content.replace("{{TASK_TITLE}}", title)

    tasks_dir.mkdir(parents=True, exist_ok=True)
    if overwrite or not note_path.exists():
        write_utf8(note_path, content)

    card = f"- [ ] [[{project_name}/任务/Tasks/{note_name}|{title}]]"
    expected_target = f"{project_name}/任务/Tasks/{note_name}"
    board = board_path.read_text(encoding="utf-8")
    if not board_has_task_card(board, expected_target, note_name, title):
        write_utf8(board_path, insert_card(board, column, card))
    return note_path, board_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", help="Path to the Obsidian vault root. Defaults to the active Obsidian vault.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--board-name", help="Board file name. Auto-detects '*任务看板.md' when omitted.")
    parser.add_argument("--column", default="需求池", choices=sorted(VALID_COLUMNS))
    parser.add_argument("--owner", default="")
    parser.add_argument("--agent-role", default="")
    parser.add_argument("--priority", default="")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    note_path, board_path = create_task(
        resolve_vault_path(args.vault_path),
        args.project_name,
        args.title,
        args.column,
        args.owner,
        args.agent_role,
        args.priority,
        args.overwrite,
        args.board_name,
    )
    print(note_path)
    print(board_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
