"""Helpers for matching and editing Obsidian Kanban task boards."""

from __future__ import annotations

import json
import re


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]*))?\]\]")
HORIZONTAL_RULE_RE = re.compile(r"^\s{0,3}(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})\s*$")
KANBAN_SETTINGS_RE = re.compile(r"^%%\s*kanban:settings\b")


def normalize_wikilink_target(target: str) -> str:
    normalized = target.strip().replace("\\", "/")
    if normalized.endswith(".md"):
        normalized = normalized[:-3]
    return re.sub(r"/+", "/", normalized)


def wikilink_target_matches(target: str, expected_target: str, note_name: str) -> bool:
    normalized = normalize_wikilink_target(target)
    expected = normalize_wikilink_target(expected_target)
    return normalized == expected or normalized.rsplit("/", 1)[-1] == note_name


def card_links_to_task(line: str, expected_target: str, note_name: str, title: str) -> bool:
    return matching_wikilink_target(line, expected_target, note_name, title) is not None


def matching_wikilink_target(line: str, expected_target: str, note_name: str, title: str) -> str | None:
    for match in WIKILINK_RE.finditer(line):
        alias = (match.group(2) or "").strip()
        if wikilink_target_matches(match.group(1), expected_target, note_name) or alias == title.strip():
            return normalize_wikilink_target(match.group(1))
    return None


def normalize_card_text(line: str) -> str:
    stripped = line.strip()
    stripped = re.sub(r"^[-*+]\s+", "", stripped)
    stripped = re.sub(r"^\[[ xX]\]\s+", "", stripped)
    return stripped.strip()


def card_text_matches_title(line: str, title: str) -> bool:
    if "[[" in line:
        return False
    return normalize_card_text(line) == title.strip()


def is_card_line(line: str) -> bool:
    return line.strip().startswith(("-", "*", "+"))


def is_horizontal_rule(line: str) -> bool:
    return HORIZONTAL_RULE_RE.fullmatch(line) is not None


def is_kanban_settings_start(line: str) -> bool:
    return KANBAN_SETTINGS_RE.match(line.strip()) is not None


def find_column_bounds(lines: list[str], column: str) -> tuple[int, int]:
    heading = f"## {column}"
    try:
        start = lines.index(heading) + 1
    except ValueError as exc:
        raise ValueError(f"board column not found: {column}") from exc

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## ") or is_kanban_settings_start(lines[index]):
            end = index
            break
    return start, end


def trim_blank_lines(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def normalize_column_section(lines: list[str]) -> list[str]:
    body = trim_blank_lines(lines)
    tail: list[str] = []
    if body and is_horizontal_rule(body[-1]):
        tail = [body[-1]]
        body = trim_blank_lines(body[:-1])

    normalized = [""]
    if body:
        normalized.extend(body)
        normalized.append("")
    if tail:
        normalized.extend(tail)
        normalized.append("")
    return normalized


def normalize_board_column_spacing(board: str) -> str:
    lines = board.splitlines()
    normalized: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        normalized.append(line)
        index += 1
        if not line.startswith("## "):
            continue

        section_start = index
        while index < len(lines):
            if lines[index].startswith("## ") or is_kanban_settings_start(lines[index]):
                break
            index += 1
        normalized.extend(normalize_column_section(lines[section_start:index]))

    return ensure_blank_line_before_kanban_settings("\n".join(normalized).rstrip() + "\n")


def sync_list_collapse_count(board: str) -> str:
    lines = board.splitlines()
    column_count = sum(1 for line in lines if line.startswith("## "))
    for start, line in enumerate(lines):
        if not is_kanban_settings_start(line):
            continue
        if start + 1 >= len(lines) or lines[start + 1].strip() != "```":
            return board
        end = start + 2
        while end < len(lines) and lines[end].strip() != "```":
            end += 1
        if end >= len(lines):
            return board
        try:
            settings = json.loads("\n".join(lines[start + 2:end]))
        except json.JSONDecodeError:
            return board
        collapse = settings.get("list-collapse")
        if not isinstance(collapse, list) or len(collapse) == column_count:
            return board
        settings["list-collapse"] = [bool(value) for value in collapse[:column_count]]
        settings["list-collapse"].extend([False] * (column_count - len(settings["list-collapse"])))
        lines[start + 2:end] = [json.dumps(settings, ensure_ascii=False, separators=(",", ":"))]
        return "\n".join(lines).rstrip() + "\n"
    return board


def ensure_archive_column(board: str) -> str:
    lines = board.splitlines()
    if "## Archive" in lines:
        return sync_list_collapse_count(board)

    insert_at = len(lines)
    for index, line in enumerate(lines):
        if is_kanban_settings_start(line):
            insert_at = index
            break

    before = "\n".join(lines[:insert_at]).rstrip()
    after = "\n".join(lines[insert_at:]).lstrip()
    archive = "***\n\n## Archive"
    if before and after:
        board = f"{before}\n\n{archive}\n\n{after}"
    elif before:
        board = f"{before}\n\n{archive}\n"
    elif after:
        board = f"{archive}\n\n{after}"
    else:
        board = f"{archive}\n"
    return sync_list_collapse_count(board.rstrip() + "\n")


def ensure_blank_line_before_kanban_settings(board: str) -> str:
    lines = board.splitlines()
    index = 0
    while index < len(lines):
        if is_kanban_settings_start(lines[index]) and index > 0:
            blank_start = index
            while blank_start > 0 and not lines[blank_start - 1].strip():
                blank_start -= 1
            lines[blank_start:index] = [""]
            index = blank_start + 1
        index += 1
    return "\n".join(lines).rstrip() + "\n"


def remove_empty_archive_column(board: str) -> str:
    lines = board.splitlines()
    if "## Archive" not in lines:
        return sync_list_collapse_count(board)

    archive_heading = lines.index("## Archive")
    start, end = find_column_bounds(lines, "Archive")
    if any(line.strip() for line in lines[start:end]):
        return sync_list_collapse_count(board)

    remove_start = archive_heading
    previous = archive_heading - 1
    while previous >= 0 and not lines[previous].strip():
        previous -= 1
    if previous >= 0 and is_horizontal_rule(lines[previous]):
        remove_start = previous
        while remove_start > 0 and not lines[remove_start - 1].strip():
            remove_start -= 1

    board = "\n".join([*lines[:remove_start], *lines[end:]]).rstrip() + "\n"
    board = ensure_blank_line_before_kanban_settings(board)
    return sync_list_collapse_count(board)


def insert_card(board: str, column: str, card_line: str) -> str:
    if card_line in board:
        return board

    board = normalize_board_column_spacing(board)
    lines = board.splitlines()
    start, end = find_column_bounds(lines, column)

    section = trim_blank_lines(lines[start:end])
    tail: list[str] = []
    if section and is_horizontal_rule(section[-1]):
        tail = [section[-1], ""]
        section = trim_blank_lines(section[:-1])

    if section and is_card_line(section[-1]):
        section.append(card_line)
    else:
        if section:
            section.append("")
        section.append(card_line)
    lines[start:end] = ["", *section, "", *tail]
    return normalize_board_column_spacing("\n".join(lines).rstrip() + "\n")


def card_matches_task(line: str, expected_target: str, note_name: str, title: str) -> bool:
    return is_card_line(line) and (
        card_links_to_task(line, expected_target, note_name, title)
        or card_text_matches_title(line, title)
    )


def board_has_task_card(board: str, expected_target: str, note_name: str, title: str) -> bool:
    return any(
        card_matches_task(line, expected_target, note_name, title)
        for line in board.splitlines()
    )
