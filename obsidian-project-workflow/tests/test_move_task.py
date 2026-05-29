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


BOARD = """---
kanban-plugin: board
---

## 需求池

## 待执行

## 执行中

{doing}

## Review

{review}

## 完成

{done}

## Archive

"""

NOTE = """---
title: 任务标题
status: {status}
review_rounds: {rounds}
review_issues_closed: {closed}
updated: 2026-01-01
---
"""

CARD = "- [ ] [[task_file|任务标题]]"


class MoveTaskReviewGateTest(unittest.TestCase):
    def make_workspace(self, *, doing: str = "", review: str = "", done: str = "", status: str = "执行中", rounds: int = 0, closed: str = "false"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        vault = Path(tmp.name)
        project = vault / "Gix"
        board_path = project / "任务" / "任务看板.md"
        note_path = project / "任务" / "Tasks" / "task_file.md"
        note_path.parent.mkdir(parents=True)
        board_path.write_text(BOARD.format(doing=doing, review=review, done=done), encoding="utf-8")
        note_path.write_text(NOTE.format(status=status, rounds=rounds, closed=closed), encoding="utf-8")
        return vault, board_path, note_path

    def test_enter_review_increments_round_and_reopens_issues(self):
        vault, _, note_path = self.make_workspace(doing=CARD, status="执行中", rounds=0, closed="true")

        move_task.move_task(vault, "Gix", "任务标题", "Review", "任务看板.md")

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("review_rounds: 1", note)
        self.assertIn("review_issues_closed: false", note)

    def test_review_to_review_is_idempotent_for_review_fields(self):
        vault, _, note_path = self.make_workspace(review=CARD, status="Review", rounds=3, closed="true")

        move_task.move_task(vault, "Gix", "任务标题", "Review", "任务看板.md")

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("review_rounds: 3", note)
        self.assertIn("review_issues_closed: true", note)

    def test_review_rework_reopens_issues(self):
        vault, _, note_path = self.make_workspace(review=CARD, status="Review", rounds=3, closed="true")

        move_task.move_task(vault, "Gix", "任务标题", "执行中", "任务看板.md")

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("status: '执行中'", note)
        self.assertIn("review_issues_closed: false", note)

    def test_done_requires_review_source(self):
        vault, _, _ = self.make_workspace(doing=CARD, status="执行中", rounds=3, closed="true")

        with self.assertRaisesRegex(ValueError, "must be in Review before moving to 完成"):
            move_task.move_task(vault, "Gix", "任务标题", "完成", "任务看板.md")

    def test_done_requires_three_closed_review_rounds(self):
        vault, _, _ = self.make_workspace(review=CARD, status="Review", rounds=2, closed="true")

        with self.assertRaisesRegex(ValueError, "review gate incomplete"):
            move_task.move_task(vault, "Gix", "任务标题", "完成", "任务看板.md")

    def test_done_succeeds_after_three_closed_review_rounds(self):
        vault, board_path, note_path = self.make_workspace(review=CARD, status="Review", rounds=3, closed="true")

        move_task.move_task(vault, "Gix", "任务标题", "完成", "任务看板.md")

        self.assertIn("status: '完成'", note_path.read_text(encoding="utf-8"))
        self.assertIn("## 完成\n\n- [ ] [[task_file|任务标题]]", board_path.read_text(encoding="utf-8"))

    def test_note_write_failure_rolls_back_board(self):
        vault, board_path, note_path = self.make_workspace(doing=CARD, status="执行中", rounds=0, closed="true")
        original_board = board_path.read_text(encoding="utf-8")
        original_note = note_path.read_text(encoding="utf-8")
        real_write = move_task.write_utf8

        def fail_note_write(path: Path, content: str) -> None:
            if path.resolve() == note_path.resolve():
                raise OSError("simulated note write failure")
            real_write(path, content)

        with mock.patch.object(move_task, "write_utf8", side_effect=fail_note_write):
            with self.assertRaisesRegex(OSError, "simulated note write failure"):
                move_task.move_task(vault, "Gix", "任务标题", "Review", "任务看板.md")

        self.assertEqual(original_board, board_path.read_text(encoding="utf-8"))
        self.assertEqual(original_note, note_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
