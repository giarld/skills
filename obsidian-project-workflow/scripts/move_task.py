#!/usr/bin/env python3
"""Move a task card to another project Kanban column and update note status."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import tempfile
from pathlib import Path

from board_utils import (
    card_matches_task,
    ensure_archive_column,
    insert_card,
    matching_wikilink_target,
    remove_empty_archive_column,
)
from vault_utils import resolve_vault_path


VALID_COLUMNS = {"需求池", "待执行", "执行中", "Review", "完成", "Archive"}
INVALID_PROJECT_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
DEFAULT_BOARD_NAME = "任务看板.md"
REQUIRED_PASSING_REVIEW_RECORDS = 2


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


def remove_card(board: str, expected_target: str, note_name: str, title: str) -> tuple[str, str, str | None, str | None]:
    lines = board.splitlines()
    removed = ""
    removed_target = None
    source_column = None
    removed_column = None
    kept: list[str] = []
    for line in lines:
        if line.startswith("## "):
            source_column = line[3:].strip()
        if not removed and card_matches_task(line, expected_target, note_name, title):
            removed = line
            removed_target = matching_wikilink_target(line, expected_target, note_name, title)
            removed_column = source_column
            continue
        kept.append(line)
    if not removed:
        raise ValueError(f"task card not found: {expected_target} or {note_name}")
    return "\n".join(kept).rstrip() + "\n", removed, removed_target, removed_column


def with_markdown_suffix(path: Path) -> Path:
    if path.suffix == ".md":
        return path
    return Path(f"{path}.md")


def unique_paths(paths: list[Path]) -> list[Path]:
    unique = []
    seen = set()
    for path in paths:
        resolved = path.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def resolve_note_path_from_card(
    vault_path: Path,
    project_root: Path,
    project_name: str,
    link_target: str | None,
    fallback_note_name: str,
) -> Path:
    fallback = project_root / "任务" / "Tasks" / f"{fallback_note_name}.md"
    if not link_target:
        return fallback

    target_path = with_markdown_suffix(Path(link_target))
    if target_path.is_absolute():
        return target_path.expanduser().resolve()

    parts = target_path.parts
    candidates = []
    if parts and parts[0] == project_name:
        candidates.append(vault_path / target_path)
    if parts and parts[0] == "任务":
        candidates.append(project_root / target_path)
    if parts and parts[0] == "Tasks":
        candidates.append(project_root / "任务" / target_path)
    if len(parts) == 1:
        candidates.append(project_root / "任务" / "Tasks" / target_path)
    candidates.extend([
        vault_path / target_path,
        project_root / target_path,
        fallback,
    ])

    candidates = unique_paths(candidates)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def yaml_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_utf8(path: Path, content: str) -> None:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            dir=path.parent,
            delete=False,
            encoding="utf-8",
            newline="\n",
        ) as file:
            tmp_path = Path(file.name)
            file.write(content)
        os.replace(tmp_path, path)
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


def read_frontmatter_content(content: str) -> tuple[list[str], int | None]:
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return lines, None

    for index in range(1, len(lines)):
        if lines[index] == "---":
            return lines, index
    return lines, None


def frontmatter_value(note_path: Path, key: str) -> str | None:
    if not note_path.exists():
        return None

    return frontmatter_value_from_content(note_path.read_text(encoding="utf-8"), key)


def frontmatter_value_from_content(content: str, key: str) -> str | None:
    lines, end = read_frontmatter_content(content)
    if end is None:
        return None

    for index in range(1, end):
        if lines[index].startswith(f"{key}:"):
            return lines[index].split(":", 1)[1].strip().strip("'\"")
    return None


def set_frontmatter_values_in_content(content: str, values: dict[str, str]) -> str | None:
    lines, end = read_frontmatter_content(content)
    if end is None:
        return None
    missing = dict(values)
    for index in range(1, end):
        key = lines[index].split(":", 1)[0]
        if key in values:
            lines[index] = f"{key}: {values[key]}"
            missing.pop(key, None)
    for key, value in missing.items():
        lines.insert(end, f"{key}: {value}")
        end += 1

    return "\n".join(lines).rstrip() + "\n"


def update_status_in_content(content: str, status: str) -> str | None:
    today = dt.date.today().isoformat()
    return set_frontmatter_values_in_content(content, {
        "status": yaml_string(status),
        "updated": yaml_string(today),
    })


def frontmatter_bool(note_path: Path, key: str) -> bool:
    value = frontmatter_value(note_path, key)
    if value is None:
        return False
    return value.lower() in {"true", "yes", "1", "on"}


def frontmatter_bool_from_content(content: str, key: str) -> bool:
    value = frontmatter_value_from_content(content, key)
    if value is None:
        return False
    return value.lower() in {"true", "yes", "1", "on"}


def review_section_lines(content: str) -> list[str]:
    lines = content.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == "## Review") + 1
    except StopIteration:
        return []

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return lines[start:end]


def markdown_table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def is_markdown_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def review_record_conclusions(content: str) -> list[str]:
    conclusions = []
    conclusion_index = 2
    for line in review_section_lines(content):
        cells = markdown_table_cells(line)
        if cells is None:
            continue
        if is_markdown_separator_row(cells):
            continue
        if "结论" in cells:
            conclusion_index = cells.index("结论")
            continue
        if len(cells) <= conclusion_index:
            continue
        conclusion = cells[conclusion_index].strip()
        if not conclusion:
            continue
        conclusions.append(conclusion)
    return conclusions


def is_passing_review_conclusion(conclusion: str) -> bool:
    normalized = re.sub(r"\s+", "", conclusion).lower().strip("`*_[]（）()。.!！")
    negative_tokens = (
        "不通过",
        "未通过",
        "失败",
        "退回",
        "需修改",
        "需要修改",
        "返工",
        "fail",
        "failed",
        "reject",
        "rejected",
        "blocked",
    )
    if any(token in normalized for token in negative_tokens):
        return False
    passing_tokens = {"通过", "pass", "passed", "approve", "approved", "ok", "lgtm", "无问题", "验收通过"}
    return (
        normalized in passing_tokens
        or "通过" in normalized
        or normalized.startswith("pass")
        or normalized.startswith("approve")
        or normalized.startswith("approved")
    )


def has_required_passing_review_records(content: str) -> bool:
    conclusions = review_record_conclusions(content)
    if len(conclusions) < REQUIRED_PASSING_REVIEW_RECORDS:
        return False
    return all(is_passing_review_conclusion(conclusion) for conclusion in conclusions[-REQUIRED_PASSING_REVIEW_RECORDS:])


def set_review_issues_closed_in_content(content: str, closed: bool) -> str | None:
    today = dt.date.today().isoformat()
    return set_frontmatter_values_in_content(content, {
        "review_issues_closed": str(closed).lower(),
        "updated": yaml_string(today),
    })


def sync_review_issues_closed_from_records_in_content(content: str) -> str | None:
    return set_review_issues_closed_in_content(content, has_required_passing_review_records(content))


def require_review_gate_for_done(content: str, title: str) -> None:
    issues_closed = frontmatter_bool_from_content(content, "review_issues_closed")
    passing_records = has_required_passing_review_records(content)
    if issues_closed and passing_records:
        return
    raise ValueError(
        f"review gate incomplete for task '{title}'; moving to 完成 requires "
        f"{REQUIRED_PASSING_REVIEW_RECORDS} consecutive passing Review records and "
        f"review_issues_closed: true "
        f"(current consecutive_passing_reviews={str(passing_records).lower()}, "
        f"review_issues_closed={str(issues_closed).lower()})."
    )


def require_source_column(source_column: str | None, required_column: str, to_column: str, title: str) -> None:
    if source_column == required_column:
        return
    raise ValueError(
        f"task '{title}' must be in {required_column} before moving to {to_column} "
        f"(current column={source_column or 'unknown'})."
    )


def reopen_review_issues_in_content(content: str) -> str | None:
    return set_review_issues_closed_in_content(content, False)


def build_note_content_for_move(
    note_path: Path,
    source_column: str | None,
    to_column: str,
    skip_commit_record: bool = False,
) -> str | None:
    if not note_path.exists():
        return None

    original = note_path.read_text(encoding="utf-8")
    updated = original
    if to_column == "Review" and source_column != "Review":
        next_content = reopen_review_issues_in_content(updated)
        if next_content is not None:
            updated = next_content
    if source_column == "Review" and to_column == "Review":
        next_content = sync_review_issues_closed_from_records_in_content(updated)
        if next_content is not None:
            updated = next_content
    if source_column == "Review" and to_column == "完成":
        next_content = sync_review_issues_closed_from_records_in_content(updated)
        if next_content is not None:
            updated = next_content
    if source_column == "Review" and to_column not in {"Review", "完成"}:
        next_content = reopen_review_issues_in_content(updated)
        if next_content is not None:
            updated = next_content
    next_content = update_status_in_content(updated, to_column)
    if next_content is not None:
        updated = next_content
    if to_column == "完成" and skip_commit_record:
        next_content = set_frontmatter_values_in_content(updated, {"commit_record_skipped": "true"})
        if next_content is not None:
            updated = next_content
    if updated == original:
        return None
    return updated


def write_board_and_note(board_path: Path, board_content: str, note_path: Path, note_content: str | None) -> None:
    original_board = board_path.read_text(encoding="utf-8")
    original_note = note_path.read_text(encoding="utf-8") if note_path.exists() else None
    board_written = False
    note_written = False
    try:
        write_utf8(board_path, board_content)
        board_written = True
        if note_content is not None:
            write_utf8(note_path, note_content)
            note_written = True
    except Exception as exc:
        rollback_errors = []
        if board_written:
            try:
                write_utf8(board_path, original_board)
            except Exception as rollback_exc:
                rollback_errors.append(f"board rollback failed: {rollback_exc}")
        if note_written and original_note is not None:
            try:
                write_utf8(note_path, original_note)
            except Exception as rollback_exc:
                rollback_errors.append(f"note rollback failed: {rollback_exc}")
        if rollback_errors:
            raise RuntimeError("; ".join(rollback_errors)) from exc
        raise


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
    skip_commit_record: bool = False,
) -> tuple[Path, Path]:
    if to_column not in VALID_COLUMNS:
        raise ValueError(f"invalid column: {to_column}")
    if require_commit and skip_commit_record:
        raise ValueError("--require-commit and --skip-commit-record cannot be used together")

    project_name = safe_project_name(project_name)
    note_name = safe_note_name(title)
    vault_path = vault_path.expanduser().resolve()
    project_root = vault_path / project_name
    board_path = resolve_board_path(project_root, board_name)
    expected_target = f"{project_name}/任务/Tasks/{note_name}"

    board = board_path.read_text(encoding="utf-8")
    board, card, card_target, source_column = remove_card(board, expected_target, note_name, title)
    if to_column != "Archive":
        board = remove_empty_archive_column(board)
    note_path = resolve_note_path_from_card(vault_path, project_root, project_name, card_target, note_name)

    should_require_commit = (require_commit or frontmatter_bool(note_path, "requires_commit")) and not skip_commit_record
    if to_column == "完成" and should_require_commit:
        require_commit_chain_for_done(note_path, title)

    note_content = build_note_content_for_move(note_path, source_column, to_column, skip_commit_record)
    if to_column == "完成":
        require_source_column(source_column, "Review", to_column, title)
        effective_note_content = note_content
        if effective_note_content is None and note_path.exists():
            effective_note_content = note_path.read_text(encoding="utf-8")
        require_review_gate_for_done(effective_note_content or "", title)

    if to_column == "Archive":
        board = ensure_archive_column(board)
    board = insert_card(board, to_column, card)
    write_board_and_note(board_path, board, note_path, note_content)
    return note_path, board_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", help="Path to the Obsidian vault root. Defaults to the active Obsidian vault.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--board-name", help="Board file name. Auto-detects '*任务看板.md' when omitted.")
    parser.add_argument("--to-column", required=True, choices=sorted(VALID_COLUMNS))
    parser.add_argument("--require-commit", action="store_true", help="Require a recorded commit id/hash or svn revision before moving to 完成.")
    parser.add_argument("--skip-commit-record", action="store_true", help="Skip commit-record gate only when the human explicitly says no commit record is needed.")
    args = parser.parse_args()

    note_path, board_path = move_task(
        resolve_vault_path(args.vault_path),
        args.project_name,
        args.title,
        args.to_column,
        args.board_name,
        args.require_commit,
        args.skip_commit_record,
    )
    print(note_path)
    print(board_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
