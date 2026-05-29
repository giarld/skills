"""Helpers for matching Obsidian Kanban task cards."""

from __future__ import annotations

import re


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]*))?\]\]")


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
    for match in WIKILINK_RE.finditer(line):
        alias = (match.group(2) or "").strip()
        if wikilink_target_matches(match.group(1), expected_target, note_name) or alias == title.strip():
            return True
    return False


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
