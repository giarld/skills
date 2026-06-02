#!/usr/bin/env python3
"""Move a task back to Review and record who requested the new review."""

from __future__ import annotations

import argparse

import move_task
from vault_utils import resolve_vault_path


def request_review(
    vault_path,
    project_name: str,
    title: str,
    board_name: str | None,
    requester: str,
    requester_model: str,
) -> tuple[object, object]:
    return move_task.move_task(
        vault_path,
        project_name,
        title,
        "Review",
        board_name,
        review_requester=requester,
        review_requester_model=requester_model,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", help="Path to the Obsidian vault root. Defaults to the active Obsidian vault.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--board-name", help="Board file name. Auto-detects '*任务看板.md' when omitted.")
    parser.add_argument("--requester", required=True, help="Who is resubmitting the task for review.")
    parser.add_argument("--requester-model", required=True, help="Requester model name for the current review submission.")
    args = parser.parse_args()

    note_path, board_path = request_review(
        resolve_vault_path(args.vault_path),
        args.project_name,
        args.title,
        args.board_name,
        args.requester,
        args.requester_model,
    )
    print(note_path)
    print(board_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
