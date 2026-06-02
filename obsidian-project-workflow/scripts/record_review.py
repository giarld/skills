#!/usr/bin/env python3
"""Append a Review record to an Obsidian workflow task note and optionally sync the board state."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import tempfile
from pathlib import Path

import move_task
from vault_utils import resolve_vault_path


INVALID_PROJECT_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
DEFAULT_REVIEWER = "AI"
PASSING_DECISION = "pass"
FAILING_DECISION = "fail"
REVIEW_STATUS = "Review"


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


def table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


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


def review_record(time: str, reviewer: str, model: str, conclusion: str, disposition: str) -> str:
    return (
        f"| {table_cell(time)} | {table_cell(reviewer)} | {table_cell(model)} | "
        f"{table_cell(conclusion)} | {table_cell(disposition)} |"
    )


def ensure_review_section(content: str) -> str:
    if "## Review" in content:
        return content

    section = (
        "\n## Review\n\n"
        "| 时间 | Reviewer | 模型 | 结论 | 处理 |\n"
        "| --- | --- | --- | --- | --- |\n"
    )
    evidence_marker = "\n## 验收证据"
    if evidence_marker in content:
        return content.replace(evidence_marker, section + evidence_marker, 1)
    return content.rstrip() + section + "\n"


def append_review_in_content(content: str, time: str, reviewer: str, model: str, conclusion: str, disposition: str) -> str:
    content = ensure_review_section(content)
    row = review_record(time, reviewer, model, conclusion, disposition)
    lines = content.splitlines()
    try:
        heading = lines.index("## Review")
    except ValueError as exc:
        raise RuntimeError("review section could not be created") from exc

    insert_at = len(lines)
    for index in range(heading + 1, len(lines)):
        if lines[index].startswith("## "):
            insert_at = index
            break
    while insert_at > heading and insert_at <= len(lines) and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, row)
    return "\n".join(lines).rstrip() + "\n"


def append_review(note_path: Path, time: str, reviewer: str, model: str, conclusion: str, disposition: str) -> None:
    updated = append_review_in_content(note_path.read_text(encoding="utf-8"), time, reviewer, model, conclusion, disposition)
    write_utf8(note_path, updated)


def current_status(note_path: Path) -> str | None:
    return move_task.frontmatter_value(note_path, "status")


def require_review_status_for_decision(note_path: Path, decision: str) -> None:
    status = current_status(note_path)
    if status == REVIEW_STATUS:
        return
    raise ValueError(
        "review decisions can only be recorded while the task is in Review; "
        f"current status is {status or 'unknown'}. After a fixer completes changes in 执行中, "
        "move the task back to Review first with scripts/move_task.py --to-column Review. "
        "Only the reviewer should append pass/fail Review records."
    )


def review_request_metadata(note_path: Path) -> tuple[str, str]:
    requester = (move_task.frontmatter_value(note_path, "review_requested_by") or "").strip()
    requester_model = (move_task.frontmatter_value(note_path, "review_requested_model") or "").strip()
    return requester, requester_model


def require_review_request_metadata(note_path: Path) -> tuple[str, str]:
    requester, requester_model = review_request_metadata(note_path)
    if requester and requester_model:
        return requester, requester_model
    raise ValueError(
        "review request metadata is missing; resubmit the task to Review with "
        "scripts/request_review.py or scripts/move_task.py --review-requester/--review-requester-model "
        "before recording a pass/fail Review decision."
    )


def require_reviewer_differs_from_requester(note_path: Path, reviewer: str) -> None:
    requester, _ = require_review_request_metadata(note_path)
    if requester.casefold() != reviewer.strip().casefold():
        return
    raise ValueError(
        "the reviewer must be different from the person who resubmitted the task to Review; "
        "a fixer may only send the task back to Review, and the reviewer must record the next pass/fail decision."
    )


def resolve_note_path(
    vault_path: Path,
    project_name: str,
    title: str,
    note_path: str | None,
    board_name: str | None,
) -> Path:
    if note_path:
        path = Path(note_path).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (vault_path / path).resolve()

    note_name = safe_note_name(title)
    project_root = vault_path / project_name
    inferred = project_root / "任务" / "Tasks" / f"{note_name}.md"
    if inferred.exists():
        return inferred

    try:
        board_path = move_task.resolve_board_path(project_root, board_name)
    except (FileNotFoundError, ValueError):
        return inferred

    expected_target = f"{project_name}/任务/Tasks/{note_name}"
    board = board_path.read_text(encoding="utf-8")
    for line in board.splitlines():
        if not move_task.card_matches_task(line, expected_target, note_name, title):
            continue
        target = move_task.matching_wikilink_target(line, expected_target, note_name, title)
        return move_task.resolve_note_path_from_card(vault_path, project_root, project_name, target, note_name)
    return inferred


def record_review(
    vault_path: Path,
    project_name: str,
    title: str,
    reviewer: str,
    model: str,
    conclusion: str,
    disposition: str,
    note_path: str | None = None,
    time: str | None = None,
    decision: str | None = None,
    board_name: str | None = None,
) -> Path:
    project_name = safe_project_name(project_name)
    note = resolve_note_path(vault_path, project_name, title, note_path, board_name)
    if not note.exists():
        raise FileNotFoundError(f"task note not found: {note}")
    if decision in {PASSING_DECISION, FAILING_DECISION}:
        require_review_status_for_decision(note, decision)
        require_reviewer_differs_from_requester(note, reviewer)

    recorded_at = time or dt.datetime.now().astimezone().isoformat(timespec="seconds")
    original_note = note.read_text(encoding="utf-8")
    updated_note = append_review_in_content(original_note, recorded_at, reviewer, model, conclusion, disposition)

    if decision is None:
        write_utf8(note, updated_note)
        return note

    note_name = safe_note_name(title)
    project_root = vault_path / project_name
    board_path = move_task.resolve_board_path(project_root, board_name)
    expected_target = f"{project_name}/任务/Tasks/{note_name}"
    board = board_path.read_text(encoding="utf-8")
    board, card, _, source_column = move_task.remove_card(board, expected_target, note_name, title)
    board = move_task.remove_empty_archive_column(board)
    target_column = REVIEW_STATUS if decision == PASSING_DECISION else "执行中"
    move_task.require_source_column(source_column, REVIEW_STATUS, target_column, title)
    final_note = move_task.build_note_content_for_move_from_content(updated_note, source_column, target_column)
    if final_note is None:
        # The appended Review row must still persist even when frontmatter sync produces no additional change.
        final_note = updated_note
    board = move_task.insert_card(board, target_column, card)
    move_task.write_board_and_note(board_path, board, note, final_note)

    return note


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", help="Path to the Obsidian vault root. Defaults to the active Obsidian vault.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--note-path", help="Task note path, absolute or vault-relative. Overrides --title filename inference.")
    parser.add_argument("--board-name", help="Board file name. Auto-detects '*任务看板.md' when omitted.")
    parser.add_argument("--reviewer", default=DEFAULT_REVIEWER, help="Reviewer name recorded in the Review table.")
    parser.add_argument("--model", required=True, help="Reviewer model name recorded in the Review table.")
    parser.add_argument("--conclusion", required=True, help="Review conclusion, such as '通过' or '不通过：缺少测试'.")
    parser.add_argument("--disposition", default="", help="Follow-up action, such as '无' or '补测试后重提'.")
    parser.add_argument("--time", help="Review timestamp. Defaults to the current local time in ISO 8601 format.")
    parser.add_argument(
        "--decision",
        choices=[PASSING_DECISION, FAILING_DECISION],
        help="Optional workflow action after recording Review: pass keeps the task in Review and syncs the gate; fail moves it back to 执行中.",
    )
    args = parser.parse_args()

    note_path = record_review(
        resolve_vault_path(args.vault_path),
        args.project_name,
        args.title,
        args.reviewer,
        args.model,
        args.conclusion,
        args.disposition,
        args.note_path,
        args.time,
        args.decision,
        args.board_name,
    )
    print(note_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
