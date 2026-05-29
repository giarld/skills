#!/usr/bin/env python3
"""Append git/svn/manual commit metadata to an Obsidian workflow task note."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
from pathlib import Path

from vault_utils import resolve_vault_path


INVALID_PROJECT_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


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


def decode_output(data: bytes, encoding: str | None) -> str:
    encodings = []
    if encoding:
        encodings.append(encoding)
    if os.name == "nt":
        encodings.append("mbcs")
    encodings.append("utf-8")

    for candidate in encodings:
        try:
            return data.decode(candidate).strip()
        except UnicodeDecodeError:
            continue
    return data.decode(encodings[-1], errors="replace").strip()


def run_command(args: list[str], cwd: Path, encoding: str | None = "utf-8") -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        capture_output=True,
    )
    return decode_output(result.stdout, encoding)


def detect_vcs(repo_path: Path) -> str:
    try:
        run_command(["git", "rev-parse", "--is-inside-work-tree"], repo_path)
        return "git"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    try:
        run_command(["svn", "info"], repo_path, encoding=None)
        return "svn"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    raise RuntimeError("cannot detect git or svn repository; pass --vcs manual with commit metadata")


def read_git_commit(repo_path: Path, commit_ref: str | None = None) -> dict[str, str]:
    ref = commit_ref.strip() if commit_ref else "HEAD"
    output = run_command(["git", "show", "-s", "--pretty=format:%H%x09%an%x09%cI%x09%s", ref], repo_path)
    commit_id, author, committed_at, message = output.split("\t", 3)
    return {
        "vcs": "git",
        "commit": commit_id,
        "author": author,
        "message": message,
        "time": committed_at,
        "source": "git/show",
    }


def read_svn_commit(repo_path: Path, revision_ref: str | None = None) -> dict[str, str]:
    revision = (
        revision_ref.strip().lstrip("r")
        if revision_ref
        else run_command(["svn", "info", "--show-item", "revision"], repo_path, encoding=None)
    )
    log_output = run_command(["svn", "log", "-r", revision], repo_path, encoding=None)
    log_lines = [line for line in log_output.splitlines() if not line.startswith("-----")]
    metadata = [cell.strip() for cell in log_lines[0].split("|")] if log_lines else []
    author = metadata[1] if len(metadata) > 1 else ""
    committed_at = metadata[2] if len(metadata) > 2 else ""
    message_lines = log_lines[2:] if len(log_lines) > 2 else []
    message = " ".join(line.strip() for line in message_lines if line.strip())
    return {
        "vcs": "svn",
        "commit": f"r{revision.lstrip('r')}",
        "author": author,
        "message": message,
        "time": committed_at,
        "source": "svn/log",
    }


def manual_commit(args: argparse.Namespace) -> dict[str, str]:
    return {
        "vcs": args.vcs_label or "manual",
        "commit": args.commit.strip(),
        "author": args.author or "",
        "message": args.message or "",
        "time": args.time or dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "user/manual",
    }


def ensure_commit_section(content: str) -> str:
    if "## 提交记录" in content:
        return content

    section = (
        "\n## 提交记录\n\n"
        "| 时间 | VCS | 提交 | 作者 | 信息 | 来源 |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
    )
    review_marker = "\n## Review"
    if review_marker in content:
        return content.replace(review_marker, section + review_marker, 1)
    return content.rstrip() + section + "\n"


def append_commit(note_path: Path, commit: dict[str, str]) -> None:
    content = ensure_commit_section(note_path.read_text(encoding="utf-8"))
    row = (
        f"| {table_cell(commit['time'])} | {table_cell(commit['vcs'])} | "
        f"{table_cell(commit['commit'])} | {table_cell(commit['author'])} | "
        f"{table_cell(commit['message'])} | {table_cell(commit['source'])} |"
    )
    lines = content.splitlines()
    try:
        heading = lines.index("## 提交记录")
    except ValueError as exc:
        raise RuntimeError("commit section could not be created") from exc

    insert_at = len(lines)
    for index in range(heading + 1, len(lines)):
        if lines[index].startswith("## "):
            insert_at = index
            break
    while insert_at > heading and insert_at <= len(lines) and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, row)
    with note_path.open("w", encoding="utf-8", newline="\n") as file:
        file.write("\n".join(lines).rstrip() + "\n")


def resolve_note_path(vault_path: Path, project_name: str, title: str, note_path: str | None) -> Path:
    if note_path:
        path = Path(note_path).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (vault_path / path).resolve()

    note_name = safe_note_name(title)
    return vault_path / project_name / "任务" / "Tasks" / f"{note_name}.md"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", help="Path to the Obsidian vault root. Defaults to the active Obsidian vault.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--note-path", help="Task note path, absolute or vault-relative. Overrides --title filename inference.")
    parser.add_argument("--vcs", choices=["auto", "git", "svn", "manual"], default="auto")
    parser.add_argument("--repo-path", default=".", help="Code repository path for git/svn auto-read.")
    parser.add_argument("--commit", help="Commit hash/ref or svn revision to record. Required for manual records; optional for git/svn.")
    parser.add_argument("--message", help="Manual commit message.")
    parser.add_argument("--author", help="Manual commit author.")
    parser.add_argument("--time", help="Manual commit time.")
    parser.add_argument("--vcs-label", help="Manual VCS label, e.g. git or svn.")
    args = parser.parse_args()
    if args.vcs == "manual" and not (args.commit and args.commit.strip()):
        parser.error("--commit is required when --vcs manual")

    project_name = safe_project_name(args.project_name)
    vault_path = resolve_vault_path(args.vault_path)
    note_path = resolve_note_path(vault_path, project_name, args.title, args.note_path)
    if not note_path.exists():
        raise FileNotFoundError(f"task note not found: {note_path}")

    repo_path = Path(args.repo_path).expanduser().resolve()
    vcs = detect_vcs(repo_path) if args.vcs == "auto" else args.vcs
    if vcs == "git":
        commit = read_git_commit(repo_path, args.commit)
    elif vcs == "svn":
        commit = read_svn_commit(repo_path, args.commit)
    else:
        commit = manual_commit(args)

    append_commit(note_path, commit)
    print(note_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
