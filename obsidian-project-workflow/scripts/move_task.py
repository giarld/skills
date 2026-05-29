#!/usr/bin/env python3
"""Move a task card to another project Kanban column and update note status."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

from board_utils import card_matches_task
from vault_utils import resolve_vault_path


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


def insert_card(board: str, column: str, card_line: str) -> str:
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
    while section and not section[-1].strip():
        section.pop()
    section.extend(["", card_line, ""])
    lines[start:end] = section
    return "\n".join(lines).rstrip() + "\n"


def remove_card(board: str, expected_target: str, note_name: str, title: str) -> tuple[str, str]:
    lines = board.splitlines()
    removed = ""
    kept: list[str] = []
    for line in lines:
        if not removed and card_matches_task(line, expected_target, note_name, title):
            removed = line
            continue
        kept.append(line)
    if not removed:
        raise ValueError(f"task card not found: {expected_target} or {note_name}")
    return "\n".join(kept).rstrip() + "\n", removed


def yaml_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_utf8(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(content)


def update_status(note_path: Path, status: str) -> None:
    if not note_path.exists():
        return

    content = note_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return

    end = None
    for index in range(1, len(lines)):
        if lines[index] == "---":
            end = index
            break
    if end is None:
        return

    replaced = False
    updated_replaced = False
    today = dt.date.today().isoformat()
    for index in range(1, end):
        if lines[index].startswith("status:"):
            lines[index] = f"status: {yaml_string(status)}"
            replaced = True
        if lines[index].startswith("updated:"):
            lines[index] = f"updated: {yaml_string(today)}"
            updated_replaced = True
    if not replaced:
        lines.insert(end, f"status: {yaml_string(status)}")
        end += 1
    if not updated_replaced:
        lines.insert(end, f"updated: {yaml_string(today)}")
    write_utf8(note_path, "\n".join(lines).rstrip() + "\n")


def frontmatter_bool(note_path: Path, key: str) -> bool:
    if not note_path.exists():
        return False

    lines = note_path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return False

    for index in range(1, len(lines)):
        if lines[index] == "---":
            return False
        if not lines[index].startswith(f"{key}:"):
            continue
        value = lines[index].split(":", 1)[1].strip().strip("'\"").lower()
        return value in {"true", "yes", "1", "on"}
    return False


def commit_chain_complete(note_path: Path) -> bool:
    if not note_path.exists():
        return False

    lines = note_path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("## 提交记录") + 1
    except ValueError:
        return False

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break

    for line in lines[start:end]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 3:
            continue
        commit_id = cells[2]
        if commit_id and commit_id not in {"提交", "---"} and not set(commit_id) <= {"-"}:
            return True
    return False


def require_commit_chain_for_done(note_path: Path, title: str) -> None:
    if commit_chain_complete(note_path):
        return
    raise ValueError(
        "commit chain incomplete; ask the user for the commit id/hash or svn revision for "
        f"task '{title}', record it with scripts/record_commit.py, then move the task to 完成."
    )


def move_task(
    vault_path: Path,
    project_name: str,
    title: str,
    to_column: str,
    board_name: str | None,
    require_commit: bool = False,
) -> tuple[Path, Path]:
    if to_column not in VALID_COLUMNS:
        raise ValueError(f"invalid column: {to_column}")

    project_name = safe_project_name(project_name)
    note_name = safe_note_name(title)
    project_root = vault_path.expanduser().resolve() / project_name
    board_path = resolve_board_path(project_root, board_name)
    note_path = project_root / "任务" / "Tasks" / f"{note_name}.md"
    expected_target = f"{project_name}/任务/Tasks/{note_name}"

    should_require_commit = require_commit or frontmatter_bool(note_path, "requires_commit")
    if to_column == "完成" and should_require_commit:
        require_commit_chain_for_done(note_path, title)

    board = board_path.read_text(encoding="utf-8")
    board, card = remove_card(board, expected_target, note_name, title)
    board = insert_card(board, to_column, card)
    write_utf8(board_path, board)
    update_status(note_path, to_column)
    return note_path, board_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", help="Path to the Obsidian vault root. Defaults to the active Obsidian vault.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--board-name", help="Board file name. Auto-detects '*任务看板.md' when omitted.")
    parser.add_argument("--to-column", required=True, choices=sorted(VALID_COLUMNS))
    parser.add_argument("--require-commit", action="store_true", help="Require a recorded commit id/hash or svn revision before moving to 完成.")
    args = parser.parse_args()

    note_path, board_path = move_task(
        resolve_vault_path(args.vault_path),
        args.project_name,
        args.title,
        args.to_column,
        args.board_name,
        args.require_commit,
    )
    print(note_path)
    print(board_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
