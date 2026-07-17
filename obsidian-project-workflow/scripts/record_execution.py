#!/usr/bin/env python3
"""Record one execution lifecycle event and sync the task board atomically."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import move_task
import task_context
from vault_utils import resolve_vault_path


EVENT_STATUS = {
    "start": "running",
    "succeed": "succeeded",
    "fail": "failed",
}
EXECUTION_SECTION = """## Execution Attempts

| Time | Attempt | Executor | Model | Status | Result / Reason | Next Action |
| --- | --- | --- | --- | --- | --- | --- |
"""


def table_text(value: str) -> str:
    return " ".join(value.replace("|", "\\|").splitlines()).strip()


def append_execution_row(content: str, row: str) -> str:
    lines = content.splitlines()
    try:
        start = lines.index("## Execution Attempts")
    except ValueError:
        return content.rstrip() + "\n\n" + EXECUTION_SECTION + row + "\n"

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    lines.insert(end, row)
    return "\n".join(lines).rstrip() + "\n"


def current_attempt(content: str) -> int:
    raw = move_task.frontmatter_value_from_content(content, "run_attempt") or "0"
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"invalid run_attempt: {raw}") from exc


def build_execution_content(
    original: str,
    event: str,
    executor: str,
    model: str,
    result: str,
    reason: str,
    next_action: str,
    source_column: str | None,
) -> tuple[str, str]:
    if event not in EVENT_STATUS:
        raise ValueError(f"invalid event: {event}")

    previous_status = move_task.frontmatter_value_from_content(original, "run_status") or "idle"
    attempt = current_attempt(original)
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")

    if event == "start":
        if source_column not in {"Todo", "In Progress"}:
            raise ValueError(f"execution can only start from Todo or In Progress (current column={source_column or 'unknown'})")
        if previous_status == "running":
            raise ValueError("execution is already running")
        attempt += 1
        target_column = "In Progress"
        detail = result or "Execution started"
        failure_reason = ""
    else:
        if source_column != "In Progress":
            raise ValueError(f"execution can only finish from In Progress (current column={source_column or 'unknown'})")
        if attempt < 1 or previous_status != "running":
            raise ValueError("record start before finishing an execution attempt")
        target_column = "Review" if event == "succeed" else "In Progress"
        detail = result if event == "succeed" else reason
        failure_reason = reason if event == "fail" else ""

    values = {
        "run_attempt": str(attempt),
        "run_status": move_task.yaml_string(EVENT_STATUS[event]),
        "run_started_at": move_task.yaml_string(now if event == "start" else (
            move_task.frontmatter_value_from_content(original, "run_started_at") or ""
        )),
        "last_failure_reason": move_task.yaml_string(failure_reason),
    }
    updated = move_task.set_frontmatter_values_in_content(original, values)
    if updated is None:
        raise ValueError("task note requires YAML frontmatter")

    row = (
        f"| {table_text(now)} | {attempt} | {table_text(executor)} | {table_text(model)} | "
        f"{EVENT_STATUS[event]} | {table_text(detail)} | {table_text(next_action)} |"
    )
    return append_execution_row(updated, row), target_column


def record_execution(
    vault_path: Path,
    project_name: str,
    title: str,
    event: str,
    executor: str,
    model: str,
    board_name: str | None = None,
    result: str = "",
    reason: str = "",
    next_action: str = "",
    repo_path: str | None = None,
    replace_current_task: bool = False,
) -> tuple[Path, Path]:
    if event == "succeed" and not result.strip():
        raise ValueError("--result is required for succeed")
    if event == "fail" and (not reason.strip() or not next_action.strip()):
        raise ValueError("--reason and --next-action are required for fail")

    project_name = move_task.safe_project_name(project_name)
    note_name = move_task.safe_note_name(title)
    vault_path = vault_path.expanduser().resolve()
    project_root = vault_path / project_name
    board_path = move_task.resolve_board_path(project_root, board_name)
    expected_target = f"{project_name}/Planning/Tasks/{note_name}"

    original_board = board_path.read_text(encoding="utf-8")
    board_without_card, card, card_target, source_column = move_task.remove_card(
        original_board, expected_target, note_name, title
    )
    note_path = move_task.resolve_note_path_from_card(
        vault_path, project_root, project_name, card_target, note_name
    )
    if not note_path.exists():
        raise FileNotFoundError(f"task note not found: {note_path}")

    original_note = note_path.read_text(encoding="utf-8")
    stored_repo = move_task.frontmatter_value_from_content(original_note, "execution_repo") or ""
    effective_repo = Path(repo_path or stored_repo).expanduser().resolve() if repo_path or stored_repo else None
    if effective_repo is not None:
        task_context.assert_can_activate(effective_repo, note_path, replace_current_task)

    note_content, target_column = build_execution_content(
        original_note,
        event,
        executor,
        model,
        result,
        reason,
        next_action,
        source_column,
    )
    if effective_repo is not None:
        note_content = move_task.set_frontmatter_values_in_content(
            note_content, {"execution_repo": move_task.yaml_string(str(effective_repo))}
        ) or note_content
    note_content = move_task.build_note_content_for_move_from_content(
        note_content,
        source_column,
        target_column,
        review_requester=executor if target_column == "Review" else None,
        review_requester_model=model if target_column == "Review" else None,
    ) or note_content

    if target_column == source_column:
        board_content = original_board
    else:
        board_content = move_task.insert_card(board_without_card, target_column, card)
    move_task.write_board_and_note(board_path, board_content, note_path, note_content)

    if effective_repo is not None:
        task_context.activate_task(
            effective_repo,
            note_path,
            project_name,
            title,
            current_attempt(note_content),
            target_column,
            EVENT_STATUS[event],
            reason,
            next_action,
            replace_current_task,
        )
    return note_path, board_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", help="Path to the Obsidian vault root. Defaults to the active Obsidian vault.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--board-name", help="Board file name. Auto-detects '*Task Board.md' when omitted.")
    parser.add_argument("--event", required=True, choices=sorted(EVENT_STATUS))
    parser.add_argument("--executor", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--result", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--next-action", default="")
    parser.add_argument("--repo-path", help="Repository or worktree receiving AGENTS.md/CLAUDE.md bootstrap and the current-task pointer.")
    parser.add_argument("--replace-current-task", action="store_true", help="Explicitly replace another active task in this worktree.")
    args = parser.parse_args()

    note_path, board_path = record_execution(
        resolve_vault_path(args.vault_path),
        args.project_name,
        args.title,
        args.event,
        args.executor,
        args.model,
        args.board_name,
        args.result,
        args.reason,
        args.next_action,
        args.repo_path,
        args.replace_current_task,
    )
    print(note_path)
    print(board_path)
    note = note_path.read_text(encoding="utf-8")
    repo = move_task.frontmatter_value_from_content(note, "execution_repo") or ""
    if repo:
        active_context = task_context.context_path(Path(repo))
        if active_context.exists():
            print(active_context)
            print(active_context.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
