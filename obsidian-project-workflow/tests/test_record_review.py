from __future__ import annotations

import datetime as dt
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
RECORD_REVIEW_SPEC = importlib.util.spec_from_file_location("record_review", SCRIPTS / "record_review.py")
record_review = importlib.util.module_from_spec(RECORD_REVIEW_SPEC)
assert RECORD_REVIEW_SPEC.loader is not None
RECORD_REVIEW_SPEC.loader.exec_module(record_review)
REQUEST_REVIEW_SPEC = importlib.util.spec_from_file_location("request_review", SCRIPTS / "request_review.py")
request_review = importlib.util.module_from_spec(REQUEST_REVIEW_SPEC)
assert REQUEST_REVIEW_SPEC.loader is not None
REQUEST_REVIEW_SPEC.loader.exec_module(request_review)


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

%% kanban:settings
```
{{"kanban-plugin":"board","list-collapse":[false,false,false,false,false],"show-checkboxes":false,"new-note-folder":"Gix/任务/Tasks","tag-colors":[]}}
```
%%
"""

NOTE = """---
title: 任务标题
status: {status}
review_issues_closed: {closed}
review_requested_by: {requester}
review_requested_model: {requester_model}
review_requested_at: '2026-01-01T00:00:00+08:00'
updated: {updated}
---

{review_section}

## 验收证据
"""

CARD = "- [ ] [[task_file|任务标题]]"
REVIEW_EMPTY = """## Review

| 时间 | Reviewer | 模型 | 结论 | 处理 |
| --- | --- | --- | --- | --- |
"""
REVIEW_ONE_PASS = REVIEW_EMPTY + "| 2026-01-02 | Reviewer A | gpt-5 | 通过 | 无 |\n"


class RecordReviewWorkflowTest(unittest.TestCase):
    def make_workspace(
        self,
        *,
        doing: str = "",
        review: str = "",
        done: str = "",
        status: str = "Review",
        closed: str = "false",
        requester: str = "'Codex Fixer'",
        requester_model: str = "'gpt-5-codex'",
        updated: str = "2026-01-01",
        review_section: str = REVIEW_EMPTY,
    ) -> tuple[Path, Path, Path]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        vault = Path(tmp.name)
        project = vault / "Gix"
        board_path = project / "任务" / "任务看板.md"
        note_path = project / "任务" / "Tasks" / "task_file.md"
        note_path.parent.mkdir(parents=True)
        board_path.write_text(BOARD.format(doing=doing, review=review, done=done), encoding="utf-8")
        note_path.write_text(
            NOTE.format(
                status=status,
                closed=closed,
                requester=requester,
                requester_model=requester_model,
                updated=updated,
                review_section=review_section.rstrip(),
            ),
            encoding="utf-8",
        )
        return vault, board_path, note_path

    def test_record_review_appends_row(self):
        vault, _, note_path = self.make_workspace(review=CARD)

        record_review.record_review(
            vault,
            "Gix",
            "任务标题",
            "Codex Reviewer",
            "gpt-5-codex",
            "通过",
            "无",
            note_path="Gix/任务/Tasks/task_file.md",
        )

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("| Codex Reviewer | gpt-5-codex | 通过 | 无 |", note)
        self.assertIn("status: Review", note)

    def test_failing_review_records_row_and_moves_back_to_doing(self):
        vault, board_path, note_path = self.make_workspace(review=CARD, closed="true", review_section=REVIEW_ONE_PASS)

        record_review.record_review(
            vault,
            "Gix",
            "任务标题",
            "Codex Reviewer",
            "gpt-5-codex",
            "不通过：缺少回归测试",
            "补测试后重提",
            decision="fail",
            board_name="任务看板.md",
        )

        note = note_path.read_text(encoding="utf-8")
        board = board_path.read_text(encoding="utf-8")
        self.assertIn("| Codex Reviewer | gpt-5-codex | 不通过：缺少回归测试 | 补测试后重提 |", note)
        self.assertIn("status: '执行中'", note)
        self.assertIn("review_issues_closed: false", note)
        self.assertIn("## 执行中\n\n- [ ] [[task_file|任务标题]]", board)

    def test_passing_review_records_row_and_syncs_review_gate(self):
        vault, board_path, note_path = self.make_workspace(review=CARD, review_section=REVIEW_ONE_PASS)

        record_review.record_review(
            vault,
            "Gix",
            "任务标题",
            "Codex Reviewer",
            "gpt-5-codex",
            "通过",
            "无",
            decision="pass",
            board_name="任务看板.md",
        )

        note = note_path.read_text(encoding="utf-8")
        board = board_path.read_text(encoding="utf-8")
        self.assertIn("| Codex Reviewer | gpt-5-codex | 通过 | 无 |", note)
        self.assertIn("status: 'Review'", note)
        self.assertIn("review_issues_closed: true", note)
        self.assertIn("## Review\n\n- [ ] [[task_file|任务标题]]", board)

    def test_first_passing_review_row_persists_when_frontmatter_sync_is_noop(self):
        today = dt.date.today().isoformat()
        vault, board_path, note_path = self.make_workspace(
            review=CARD,
            status="Review",
            closed="false",
            updated=today,
            review_section=REVIEW_EMPTY,
        )

        record_review.record_review(
            vault,
            "Gix",
            "任务标题",
            "Codex Reviewer",
            "gpt-5-codex",
            "通过",
            "无",
            decision="pass",
            board_name="任务看板.md",
        )

        note = note_path.read_text(encoding="utf-8")
        board = board_path.read_text(encoding="utf-8")
        self.assertIn("| Codex Reviewer | gpt-5-codex | 通过 | 无 |", note)
        self.assertIn("review_issues_closed: false", note)
        self.assertIn(f"updated: '{today}'", note)
        self.assertIn("## Review\n\n- [ ] [[task_file|任务标题]]", board)

    def test_executor_cannot_record_passing_review_from_doing(self):
        vault, _, note_path = self.make_workspace(doing=CARD, review="", status="执行中", review_section=REVIEW_ONE_PASS)
        original_note = note_path.read_text(encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "can only be recorded while the task is in Review"):
            record_review.record_review(
                vault,
                "Gix",
                "任务标题",
                "Codex Reviewer",
                "gpt-5-codex",
                "通过",
                "无",
                decision="pass",
                board_name="任务看板.md",
            )

        self.assertEqual(original_note, note_path.read_text(encoding="utf-8"))

    def test_requester_cannot_self_approve_after_resubmitting_review(self):
        vault, _, note_path = self.make_workspace(
            doing=CARD,
            review="",
            status="执行中",
            requester="''",
            requester_model="''",
            review_section=REVIEW_ONE_PASS,
        )

        record_review.move_task.move_task(
            vault,
            "Gix",
            "任务标题",
            "Review",
            "任务看板.md",
            review_requester="Codex Fixer",
            review_requester_model="gpt-5-codex",
        )

        with self.assertRaisesRegex(ValueError, "reviewer must be different"):
            record_review.record_review(
                vault,
                "Gix",
                "任务标题",
                "Codex Fixer",
                "gpt-5-codex",
                "通过",
                "无",
                decision="pass",
                board_name="任务看板.md",
            )

        self.assertIn("status: 'Review'", note_path.read_text(encoding="utf-8"))

    def test_request_review_can_backfill_metadata_while_task_already_in_review(self):
        vault, _, note_path = self.make_workspace(
            review=CARD,
            status="Review",
            requester="''",
            requester_model="''",
            review_section=REVIEW_ONE_PASS,
        )

        request_review.request_review(
            vault,
            "Gix",
            "任务标题",
            "任务看板.md",
            "Codex Fixer",
            "gpt-5-codex",
        )

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("review_requested_by: 'Codex Fixer'", note)
        self.assertIn("review_requested_model: 'gpt-5-codex'", note)

        record_review.record_review(
            vault,
            "Gix",
            "任务标题",
            "Codex Reviewer",
            "gpt-5-codex",
            "通过",
            "无",
            decision="pass",
            board_name="任务看板.md",
        )

        self.assertIn("| Codex Reviewer | gpt-5-codex | 通过 | 无 |", note_path.read_text(encoding="utf-8"))

    def test_review_decision_is_atomic_when_board_write_fails(self):
        from unittest import mock

        vault, board_path, note_path = self.make_workspace(review=CARD, review_section=REVIEW_ONE_PASS)
        original_note = note_path.read_text(encoding="utf-8")
        original_board = board_path.read_text(encoding="utf-8")

        with mock.patch.object(record_review.move_task, "write_board_and_note", side_effect=OSError("simulated write failure")):
            with self.assertRaisesRegex(OSError, "simulated write failure"):
                record_review.record_review(
                    vault,
                    "Gix",
                    "任务标题",
                    "Codex Reviewer",
                    "gpt-5-codex",
                    "通过",
                    "无",
                    decision="pass",
                    board_name="任务看板.md",
                )

        self.assertEqual(original_note, note_path.read_text(encoding="utf-8"))
        self.assertEqual(original_board, board_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
