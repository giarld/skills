from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("move_task", SCRIPTS / "move_task.py")
move_task = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(move_task)
import task_context


BOARD = """---
kanban-plugin: board
---

## Backlog

## Todo

## In Progress

{doing}

## Review

{review}

## Done

{done}

%% kanban:settings
```
{{"kanban-plugin":"board","list-collapse":[false,false,false,false,false],"show-checkboxes":false,"new-note-folder":"Gix/Planning/Tasks","tag-colors":[]}}
```
%%
"""

NOTE = """---
title: Task Title
status: {status}
review_issues_closed: {closed}
requires_commit: {requires_commit}
review_requested_by: ''
review_requested_model: ''
review_requested_at: ''
updated: 2026-01-01
---

{review_section}
"""

CARD = "- [ ] [[task_file|Task Title]]"
REVIEW_EMPTY = """## Review

| Time | Reviewer | Model | Conclusion | Disposition |
| --- | --- | --- | --- | --- |
"""
REVIEW_ONE_PASS = REVIEW_EMPTY + "| 2026-01-02 | Reviewer A | gpt-5 | Pass | None |\n"
REVIEW_TWO_PASS = REVIEW_ONE_PASS + "| 2026-01-03 | Reviewer B | gpt-5-codex | Pass | None |\n"
REVIEW_NON_CONSECUTIVE_PASS = REVIEW_EMPTY + (
    "| 2026-01-02 | Reviewer A | gpt-5 | Pass | None |\n"
    "| 2026-01-03 | Reviewer B | gpt-5-codex | Fail | Changes required |\n"
    "| 2026-01-04 | Reviewer C | gpt-5 | Pass | None |\n"
)
REVIEW_LEGACY_TWO_PASS = """## Review

| Time | Reviewer | Conclusion | Disposition |
| --- | --- | --- | --- |
| 2026-01-02 | Reviewer A | Pass | None |
| 2026-01-03 | Reviewer B | Pass | None |
"""
REVIEW_REORDERED_TWO_PASS = """## Review

| Time | Reviewer | Conclusion | Model | Disposition |
| --- | --- | --- | --- | --- |
| 2026-01-02 | Reviewer A | Pass | gpt-5 | None |
| 2026-01-03 | Reviewer B | Pass | gpt-5-codex | None |
"""
REVIEW_PREFIXED_TWO_PASS = REVIEW_EMPTY + (
    "| 2026-01-02 | Reviewer A | gpt-5 | Round 1 passed: no blockers found | None |\n"
    "| 2026-01-03 | Reviewer B | gpt-5-codex | Round 2 passed: verification passed | None |\n"
)
REVIEW_RETURNED_WITH_PASSING_TEXT = REVIEW_EMPTY + (
    "| 2026-01-02 | Reviewer A | gpt-5 | Pass | None |\n"
    "| 2026-01-03 | Reviewer B | gpt-5-codex | Returned: implementation review passed, but tests were not added | Changes required |\n"
)


class MoveTaskReviewGateTest(unittest.TestCase):
    def make_workspace(self, *, doing: str = "", review: str = "", done: str = "", status: str = "In Progress", closed: str = "false", requires_commit: str = "false", review_section: str = REVIEW_EMPTY, commit_section: str = ""):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        vault = Path(tmp.name)
        project = vault / "Gix"
        board_path = project / "Planning" / "Task Board.md"
        note_path = project / "Planning" / "Tasks" / "task_file.md"
        note_path.parent.mkdir(parents=True)
        board_path.write_text(BOARD.format(doing=doing, review=review, done=done), encoding="utf-8")
        note_path.write_text(
            NOTE.format(
                status=status,
                closed=closed,
                requires_commit=requires_commit,
                review_section=review_section,
            ) + commit_section,
            encoding="utf-8",
        )
        return vault, board_path, note_path

    def test_enter_review_reopens_issues(self):
        vault, _, note_path = self.make_workspace(doing=CARD, status="In Progress", closed="true", review_section=REVIEW_TWO_PASS)

        move_task.move_task(vault, "Gix", "Task Title", "Review", "Task Board.md")

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("review_issues_closed: false", note)

    def test_review_to_review_closes_issues_after_two_consecutive_passing_records(self):
        vault, _, note_path = self.make_workspace(review=CARD, status="Review", closed="false", review_section=REVIEW_TWO_PASS)

        move_task.move_task(vault, "Gix", "Task Title", "Review", "Task Board.md")

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("review_issues_closed: true", note)

    def test_review_rework_reopens_issues(self):
        vault, _, note_path = self.make_workspace(review=CARD, status="Review", closed="true", review_section=REVIEW_TWO_PASS)

        move_task.move_task(vault, "Gix", "Task Title", "In Progress", "Task Board.md")

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("status: 'In Progress'", note)
        self.assertIn("review_issues_closed: false", note)

    def test_review_to_review_reopens_issues_without_two_consecutive_passing_records(self):
        vault, _, note_path = self.make_workspace(
            review=CARD,
            status="Review",
            closed="true",
            review_section=REVIEW_NON_CONSECUTIVE_PASS,
        )

        move_task.move_task(vault, "Gix", "Task Title", "Review", "Task Board.md")

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("status: 'Review'", note)
        self.assertIn("review_issues_closed: false", note)

    def test_review_to_review_can_fill_missing_review_request_metadata(self):
        vault, _, note_path = self.make_workspace(review=CARD, status="Review", closed="false", review_section=REVIEW_ONE_PASS)

        move_task.move_task(
            vault,
            "Gix",
            "Task Title",
            "Review",
            "Task Board.md",
            review_requester="Codex Fixer",
            review_requester_model="gpt-5-codex",
        )

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("review_requested_by: 'Codex Fixer'", note)
        self.assertIn("review_requested_model: 'gpt-5-codex'", note)

    def test_done_requires_review_source(self):
        vault, _, _ = self.make_workspace(doing=CARD, status="In Progress", closed="true", review_section=REVIEW_TWO_PASS)

        with self.assertRaisesRegex(ValueError, "must be in Review before moving to Done"):
            move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md")

    def test_done_requires_two_consecutive_passing_review_records(self):
        vault, _, _ = self.make_workspace(review=CARD, status="Review", closed="true", review_section=REVIEW_ONE_PASS)

        with self.assertRaisesRegex(ValueError, "review gate incomplete"):
            move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md")

    def test_done_requires_consecutive_passing_review_records(self):
        vault, _, _ = self.make_workspace(
            review=CARD,
            status="Review",
            closed="true",
            review_section=REVIEW_NON_CONSECUTIVE_PASS,
        )

        with self.assertRaisesRegex(ValueError, "review gate incomplete"):
            move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md")

    def test_done_succeeds_after_two_consecutive_passing_review_records(self):
        vault, board_path, note_path = self.make_workspace(review=CARD, status="Review", closed="false", review_section=REVIEW_TWO_PASS)

        move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md")

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("status: 'Done'", note)
        self.assertIn("review_issues_closed: true", note)
        self.assertIn("## Done\n\n- [ ] [[task_file|Task Title]]", board_path.read_text(encoding="utf-8"))
        self.assertNotIn("## Archive", board_path.read_text(encoding="utf-8"))

    def test_done_clears_matching_active_task_pointer(self):
        vault, _, note_path = self.make_workspace(
            review=CARD,
            status="Review",
            closed="false",
            review_section=REVIEW_TWO_PASS,
        )
        repo = vault / "repo"
        repo.mkdir()
        note = note_path.read_text(encoding="utf-8").replace(
            "requires_commit: false",
            f"requires_commit: false\nexecution_repo: '{repo.resolve()}'",
        )
        note_path.write_text(note, encoding="utf-8")
        task_context.activate_task(repo, note_path, "Gix", "Task Title", 1, "Review", "succeeded")

        move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md")

        self.assertFalse((repo / task_context.CONTEXT_PATH).exists())

    def test_archive_column_is_created_on_first_archive_move(self):
        vault, board_path, note_path = self.make_workspace(done=CARD, status="Done", closed="true", review_section=REVIEW_TWO_PASS)

        move_task.move_task(vault, "Gix", "Task Title", "Archive", "Task Board.md")

        board = board_path.read_text(encoding="utf-8")
        note = note_path.read_text(encoding="utf-8")
        self.assertIn("***\n\n## Archive\n\n- [ ] [[task_file|Task Title]]", board)
        self.assertLess(board.index("## Archive"), board.index("%% kanban:settings"))
        self.assertIn('"list-collapse":[false,false,false,false,false,false]', board)
        self.assertIn("status: 'Archive'", note)

    def test_archive_move_reuses_existing_archive_column(self):
        board_with_archive = BOARD.replace("%% kanban:settings", "***\n\n## Archive\n\n- [ ] existing card\n\n%% kanban:settings")
        vault, board_path, note_path = self.make_workspace(done=CARD, status="Done", closed="true", review_section=REVIEW_TWO_PASS)
        board_path.write_text(board_with_archive.format(doing="", review="", done=CARD), encoding="utf-8")

        move_task.move_task(vault, "Gix", "Task Title", "Archive", "Task Board.md")

        board = board_path.read_text(encoding="utf-8")
        self.assertEqual(board.count("## Archive"), 1)
        self.assertIn("## Archive\n\n- [ ] existing card\n- [ ] [[task_file|Task Title]]", board)
        self.assertNotIn("- [ ] existing card\n\n- [ ] [[task_file|Task Title]]", board)
        self.assertIn("status: 'Archive'", note_path.read_text(encoding="utf-8"))

    def test_empty_archive_column_is_removed_after_moving_last_archived_task_out(self):
        board_with_archived_card = BOARD.replace("%% kanban:settings", f"***\n\n## Archive\n\n{CARD}\n\n%% kanban:settings")
        vault, board_path, note_path = self.make_workspace(status="Archive", closed="true", review_section=REVIEW_TWO_PASS)
        board_path.write_text(board_with_archived_card.format(doing="", review="", done=""), encoding="utf-8")

        move_task.move_task(vault, "Gix", "Task Title", "In Progress", "Task Board.md")

        board = board_path.read_text(encoding="utf-8")
        note = note_path.read_text(encoding="utf-8")
        self.assertNotIn("## Archive", board)
        self.assertIn('"list-collapse":[false,false,false,false,false]', board)
        self.assertIn("## In Progress\n\n- [ ] [[task_file|Task Title]]", board)
        self.assertIn("status: 'In Progress'", note)

    def test_done_supports_legacy_review_table_without_model_column(self):
        vault, board_path, note_path = self.make_workspace(review=CARD, status="Review", closed="false", review_section=REVIEW_LEGACY_TWO_PASS)

        move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md")

        self.assertIn("review_issues_closed: true", note_path.read_text(encoding="utf-8"))
        self.assertIn("## Done\n\n- [ ] [[task_file|Task Title]]", board_path.read_text(encoding="utf-8"))

    def test_done_uses_conclusion_header_when_review_table_columns_move(self):
        vault, board_path, note_path = self.make_workspace(review=CARD, status="Review", closed="false", review_section=REVIEW_REORDERED_TWO_PASS)

        move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md")

        self.assertIn("review_issues_closed: true", note_path.read_text(encoding="utf-8"))
        self.assertIn("## Done\n\n- [ ] [[task_file|Task Title]]", board_path.read_text(encoding="utf-8"))

    def test_done_accepts_prefixed_passing_review_conclusions(self):
        vault, board_path, note_path = self.make_workspace(review=CARD, status="Review", closed="false", review_section=REVIEW_PREFIXED_TWO_PASS)

        move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md")

        self.assertIn("review_issues_closed: true", note_path.read_text(encoding="utf-8"))
        self.assertIn("## Done\n\n- [ ] [[task_file|Task Title]]", board_path.read_text(encoding="utf-8"))

    def test_done_rejects_returned_review_even_when_text_mentions_pass(self):
        vault, _, _ = self.make_workspace(review=CARD, status="Review", closed="true", review_section=REVIEW_RETURNED_WITH_PASSING_TEXT)

        with self.assertRaisesRegex(ValueError, "review gate incomplete"):
            move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md")

    def test_done_requires_commit_record_when_required(self):
        vault, _, _ = self.make_workspace(review=CARD, status="Review", closed="false", requires_commit="true", review_section=REVIEW_TWO_PASS)

        with self.assertRaisesRegex(ValueError, "commit chain incomplete"):
            move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md")

    def test_done_succeeds_with_recorded_commit_when_required(self):
        commit_section = (
            "\n## Commit Log\n\n"
            "| Time | VCS | Commit | Author | Message | Source |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| 2026-01-02 | git | abc123 | Gxin | message | user/manual |\n"
        )
        vault, board_path, note_path = self.make_workspace(
            review=CARD,
            status="Review",
            closed="false",
            requires_commit="true",
            review_section=REVIEW_TWO_PASS,
            commit_section=commit_section,
        )

        move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md")

        self.assertIn("status: 'Done'", note_path.read_text(encoding="utf-8"))
        self.assertIn("## Done\n\n- [ ] [[task_file|Task Title]]", board_path.read_text(encoding="utf-8"))

    def test_done_can_skip_commit_record_when_human_says_no_record_needed(self):
        vault, board_path, note_path = self.make_workspace(review=CARD, status="Review", closed="false", requires_commit="true", review_section=REVIEW_TWO_PASS)

        move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md", skip_commit_record=True)

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("status: 'Done'", note)
        self.assertIn("commit_record_skipped: true", note)
        self.assertIn("## Done\n\n- [ ] [[task_file|Task Title]]", board_path.read_text(encoding="utf-8"))

    def test_require_commit_and_skip_commit_record_conflict(self):
        vault, _, _ = self.make_workspace(review=CARD, status="Review", closed="true", review_section=REVIEW_TWO_PASS)

        with self.assertRaisesRegex(ValueError, "cannot be used together"):
            move_task.move_task(vault, "Gix", "Task Title", "Done", "Task Board.md", require_commit=True, skip_commit_record=True)

    def test_note_write_failure_rolls_back_board(self):
        vault, board_path, note_path = self.make_workspace(doing=CARD, status="In Progress", closed="true")
        original_board = board_path.read_text(encoding="utf-8")
        original_note = note_path.read_text(encoding="utf-8")
        real_write = move_task.write_utf8

        def fail_note_write(path: Path, content: str) -> None:
            if path.resolve() == note_path.resolve():
                raise OSError("simulated note write failure")
            real_write(path, content)

        with mock.patch.object(move_task, "write_utf8", side_effect=fail_note_write):
            with self.assertRaisesRegex(OSError, "simulated note write failure"):
                move_task.move_task(vault, "Gix", "Task Title", "Review", "Task Board.md")

        self.assertEqual(original_board, board_path.read_text(encoding="utf-8"))
        self.assertEqual(original_note, note_path.read_text(encoding="utf-8"))

    def test_repeated_moves_do_not_accumulate_blank_lines(self):
        vault, board_path, _ = self.make_workspace(
            doing="\n\n\n\n",
            review=f"{CARD}\n\n\n\n\n\n",
            status="Review",
            closed="false",
            review_section=REVIEW_ONE_PASS,
        )

        for _ in range(3):
            move_task.move_task(vault, "Gix", "Task Title", "In Progress", "Task Board.md")
            move_task.move_task(vault, "Gix", "Task Title", "Review", "Task Board.md")

        board = board_path.read_text(encoding="utf-8")
        self.assertIn("## In Progress\n\n## Review", board)
        self.assertIn("## Review\n\n- [ ] [[task_file|Task Title]]\n\n## Done", board)
        self.assertNotIn("\n\n\n## Review", board)
        self.assertNotIn("\n\n\n## Done", board)


if __name__ == "__main__":
    unittest.main()
