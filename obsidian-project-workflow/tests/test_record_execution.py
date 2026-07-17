from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("record_execution", SCRIPTS / "record_execution.py")
record_execution = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(record_execution)

BOARD = """---
kanban-plugin: board
---

## Backlog

## Todo

{ready}

## In Progress

{doing}

## Review

{review}

## Done

%% kanban:settings
```
{{"kanban-plugin":"board","new-note-folder":"Gix/Planning/Tasks"}}
```
%%
"""

NOTE = """---
title: Task Title
status: '{status}'
execution_repo: ''
run_attempt: {attempt}
run_status: '{run_status}'
run_started_at: ''
last_failure_reason: ''
review_issues_closed: false
review_requested_by: ''
review_requested_model: ''
review_requested_at: ''
updated: '2026-01-01'
---

## Execution Attempts

| Time | Attempt | Executor | Model | Status | Result / Reason | Next Action |
| --- | --- | --- | --- | --- | --- | --- |

## Review

| Time | Reviewer | Model | Conclusion | Disposition |
| --- | --- | --- | --- | --- |
"""

CARD = "- [ ] [[task_file|Task Title]]"


class RecordExecutionTest(unittest.TestCase):
    def make_workspace(self, *, ready="", doing="", review="", status="Todo", attempt=0, run_status="idle"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        vault = Path(tmp.name)
        task_dir = vault / "Gix" / "Planning"
        note_path = task_dir / "Tasks" / "task_file.md"
        note_path.parent.mkdir(parents=True)
        board_path = task_dir / "Task Board.md"
        board_path.write_text(BOARD.format(ready=ready, doing=doing, review=review), encoding="utf-8")
        note_path.write_text(
            NOTE.format(status=status, attempt=attempt, run_status=run_status),
            encoding="utf-8",
        )
        return vault, board_path, note_path

    def test_start_increments_attempt_and_moves_to_doing(self):
        vault, board_path, note_path = self.make_workspace(ready=CARD)

        record_execution.record_execution(
            vault, "Gix", "Task Title", "start", "Codex", "gpt-5", "Task Board.md"
        )

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("run_attempt: 1", note)
        self.assertIn("run_status: 'running'", note)
        self.assertIn("| 1 | Codex | gpt-5 | running | Execution started |", note)
        self.assertIn("## In Progress\n\n- [ ] [[task_file|Task Title]]", board_path.read_text(encoding="utf-8"))

    def test_failure_stays_in_doing_and_records_retry_context(self):
        vault, board_path, note_path = self.make_workspace(
            doing=CARD, status="In Progress", attempt=1, run_status="running"
        )

        record_execution.record_execution(
            vault,
            "Gix",
            "Task Title",
            "fail",
            "Codex",
            "gpt-5",
            "Task Board.md",
            reason="Test environment unavailable",
            next_action="Fix the environment and retry",
        )

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("run_status: 'failed'", note)
        self.assertIn("last_failure_reason: 'Test environment unavailable'", note)
        self.assertIn("| failed | Test environment unavailable | Fix the environment and retry |", note)
        self.assertIn("## In Progress\n\n- [ ] [[task_file|Task Title]]", board_path.read_text(encoding="utf-8"))

    def test_success_moves_to_review_and_records_requester(self):
        vault, board_path, note_path = self.make_workspace(
            doing=CARD, status="In Progress", attempt=2, run_status="running"
        )

        record_execution.record_execution(
            vault,
            "Gix",
            "Task Title",
            "succeed",
            "Codex",
            "gpt-5",
            "Task Board.md",
            result="Implementation complete; tests passed",
        )

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("run_status: 'succeeded'", note)
        self.assertIn("review_requested_by: 'Codex'", note)
        self.assertIn("review_requested_model: 'gpt-5'", note)
        self.assertIn("| succeeded | Implementation complete; tests passed |", note)
        self.assertIn("## Review\n\n- [ ] [[task_file|Task Title]]", board_path.read_text(encoding="utf-8"))

    def test_finish_requires_running_attempt(self):
        vault, _, _ = self.make_workspace(doing=CARD, status="In Progress")

        with self.assertRaisesRegex(ValueError, "record start"):
            record_execution.record_execution(
                vault,
                "Gix",
                "Task Title",
                "succeed",
                "Codex",
                "gpt-5",
                "Task Board.md",
                result="Done",
            )

    def test_retry_after_failure_opens_a_new_attempt(self):
        vault, _, note_path = self.make_workspace(
            doing=CARD, status="In Progress", attempt=1, run_status="failed"
        )

        record_execution.record_execution(
            vault, "Gix", "Task Title", "start", "Codex", "gpt-5", "Task Board.md"
        )

        note = note_path.read_text(encoding="utf-8")
        self.assertIn("run_attempt: 2", note)
        self.assertIn("run_status: 'running'", note)
        self.assertIn("| 2 | Codex | gpt-5 | running | Execution started |", note)

    def test_start_binds_worktree_and_injects_bootstrap(self):
        vault, _, note_path = self.make_workspace(ready=CARD)
        repo = vault / "repo"
        repo.mkdir()
        (repo / "AGENTS.md").write_text("# Existing rules\n", encoding="utf-8")

        record_execution.record_execution(
            vault,
            "Gix",
            "Task Title",
            "start",
            "Codex",
            "gpt-5",
            "Task Board.md",
            repo_path=str(repo),
        )

        note = note_path.read_text(encoding="utf-8")
        active = (repo / ".obsidian-project" / "current-task.md").read_text(encoding="utf-8")
        agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
        claude = (repo / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn(f"execution_repo: '{repo.resolve()}'", note)
        self.assertIn(f"task_note: '{note_path.resolve()}'", active)
        self.assertIn("run_status: 'running'", active)
        self.assertIn("# Existing rules", agents)
        self.assertEqual(agents.count("obsidian-project-workflow:start"), 1)
        self.assertEqual(claude.count("obsidian-project-workflow:start"), 1)

    def test_start_refuses_to_replace_another_worktree_task(self):
        vault, _, note_path = self.make_workspace(ready=CARD)
        repo = vault / "repo"
        repo.mkdir()
        other_note = vault / "other.md"
        other_note.write_text("other", encoding="utf-8")
        record_execution.task_context.activate_task(
            repo, other_note, "Other", "Other task", 1, "In Progress", "running"
        )
        original = note_path.read_text(encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "another active task"):
            record_execution.record_execution(
                vault,
                "Gix",
                "Task Title",
                "start",
                "Codex",
                "gpt-5",
                "Task Board.md",
                repo_path=str(repo),
            )

        self.assertEqual(original, note_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
