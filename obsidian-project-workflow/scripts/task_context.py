#!/usr/bin/env python3
"""Maintain the repository pointer to the active Obsidian task."""

from __future__ import annotations

import datetime as dt
import os
import subprocess
import tempfile
from pathlib import Path


CONTEXT_PATH = Path(".obsidian-project/current-task.md")
BOOTSTRAP_FILES = ("AGENTS.md", "CLAUDE.md")
START_MARKER = "<!-- obsidian-project-workflow:start -->"
END_MARKER = "<!-- obsidian-project-workflow:end -->"
BOOTSTRAP_BLOCK = f"""{START_MARKER}
## Active Obsidian project task

If `.obsidian-project/current-task.md` exists:

1. Read it before doing project work.
2. Use `$obsidian-project-workflow` to read and update the linked task note.
3. Treat the task note as the source of truth for scope, status, evidence, and next action.
4. Do not infer or switch to another task unless the user explicitly asks.
{END_MARKER}"""


def yaml_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def frontmatter_value(content: str, key: str) -> str:
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return ""
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith(f"{key}:"):
            value = line.split(":", 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] == "'":
                return value[1:-1].replace("''", "'")
            return value.strip('"')
    return ""


def write_utf8(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=path.parent, delete=False, encoding="utf-8", newline="\n"
        ) as file:
            tmp_path = Path(file.name)
            file.write(content)
        os.replace(tmp_path, path)
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


def validate_repo_path(repo_path: Path) -> Path:
    repo_path = repo_path.expanduser().resolve()
    if not repo_path.is_dir():
        raise FileNotFoundError(f"repository/worktree not found: {repo_path}")
    return repo_path


def inject_bootstrap(content: str) -> str:
    if START_MARKER in content:
        if END_MARKER not in content:
            raise ValueError(f"missing bootstrap end marker: {END_MARKER}")
        before, rest = content.split(START_MARKER, 1)
        _, after = rest.split(END_MARKER, 1)
        return (before.rstrip() + "\n\n" + BOOTSTRAP_BLOCK + after).strip() + "\n"
    return (content.rstrip() + "\n\n" + BOOTSTRAP_BLOCK).strip() + "\n"


def ensure_bootstrap(repo_path: Path) -> None:
    repo_path = validate_repo_path(repo_path)
    for name in BOOTSTRAP_FILES:
        path = repo_path / name
        original = path.read_text(encoding="utf-8") if path.exists() else ""
        updated = inject_bootstrap(original)
        if updated != original:
            write_utf8(path, updated)


def ensure_local_git_ignore(repo_path: Path) -> None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--git-path", "info/exclude"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return
    if result.returncode != 0:
        return
    exclude = Path(result.stdout.strip())
    if not exclude.is_absolute():
        exclude = repo_path / exclude
    line = CONTEXT_PATH.as_posix()
    original = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    if line not in {item.strip() for item in original.splitlines()}:
        write_utf8(exclude, original.rstrip() + "\n" + line + "\n")


def context_path(repo_path: Path) -> Path:
    return validate_repo_path(repo_path) / CONTEXT_PATH


def assert_can_activate(repo_path: Path, note_path: Path, replace: bool = False) -> None:
    path = context_path(repo_path)
    if not path.exists():
        return
    active_note = frontmatter_value(path.read_text(encoding="utf-8"), "task_note")
    if active_note and Path(active_note).expanduser().resolve() != note_path.expanduser().resolve() and not replace:
        raise ValueError(
            f"worktree already has another active task: {active_note}; "
            "use --replace-current-task only after explicitly deciding to switch"
        )


def render_current_task(
    note_path: Path,
    project: str,
    title: str,
    attempt: int,
    task_status: str,
    run_status: str,
    reason: str = "",
    next_action: str = "",
) -> str:
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    return f"""---
task_note: {yaml_string(str(note_path.expanduser().resolve()))}
project: {yaml_string(project)}
title: {yaml_string(title)}
attempt: {attempt}
task_status: {yaml_string(task_status)}
run_status: {yaml_string(run_status)}
updated: {yaml_string(now)}
---

# Current Obsidian Project Task

- Task Note: `{note_path.expanduser().resolve()}`
- Project: {project}
- Task: {title}
- Attempt: {attempt}
- Task Status: {task_status}
- Run Status: {run_status}
- Latest Failure: {reason or "None"}
- Next Action: {next_action or "Read the scope, acceptance criteria, and latest records in the task note"}

## Session Rules

1. Read the task note immediately; do not rely only on this summary.
2. Write all execution, evidence, Review, and commit information back to that task note.
3. Before continuing, verify the board state and latest execution attempt; do not guess from chat history.
4. This file contains local paths, is for this worktree only, and must not be committed.
"""


def activate_task(
    repo_path: Path,
    note_path: Path,
    project: str,
    title: str,
    attempt: int,
    task_status: str,
    run_status: str,
    reason: str = "",
    next_action: str = "",
    replace: bool = False,
) -> Path:
    repo_path = validate_repo_path(repo_path)
    assert_can_activate(repo_path, note_path, replace)
    ensure_bootstrap(repo_path)
    ensure_local_git_ignore(repo_path)
    path = repo_path / CONTEXT_PATH
    write_utf8(
        path,
        render_current_task(
            note_path, project, title, attempt, task_status, run_status, reason, next_action
        ),
    )
    return path


def clear_task(repo_path: Path, note_path: Path) -> bool:
    repo_path = repo_path.expanduser().resolve()
    if not repo_path.is_dir():
        return False
    path = repo_path / CONTEXT_PATH
    if not path.exists():
        return False
    active_note = frontmatter_value(path.read_text(encoding="utf-8"), "task_note")
    if not active_note or Path(active_note).expanduser().resolve() != note_path.expanduser().resolve():
        return False
    path.unlink()
    return True
