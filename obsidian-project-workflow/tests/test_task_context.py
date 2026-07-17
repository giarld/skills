from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SPEC = importlib.util.spec_from_file_location("task_context", SCRIPTS / "task_context.py")
task_context = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(task_context)


class TaskContextTest(unittest.TestCase):
    def make_repo(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        repo = root / "repo"
        repo.mkdir()
        note = root / "vault" / "Gix" / "Planning" / "Tasks" / "task.md"
        note.parent.mkdir(parents=True)
        note.write_text("# Task\n", encoding="utf-8")
        return repo, note

    def test_bootstrap_is_idempotent_and_preserves_existing_content(self):
        repo, _ = self.make_repo()
        agents = repo / "AGENTS.md"
        agents.write_text("# Existing\n", encoding="utf-8")

        task_context.ensure_bootstrap(repo)
        task_context.ensure_bootstrap(repo)

        content = agents.read_text(encoding="utf-8")
        self.assertIn("# Existing", content)
        self.assertEqual(content.count(task_context.START_MARKER), 1)
        self.assertEqual((repo / "CLAUDE.md").read_text(encoding="utf-8").count(task_context.START_MARKER), 1)

    def test_clear_only_removes_matching_task(self):
        repo, note = self.make_repo()
        task_context.activate_task(repo, note, "Gix", "Task", 1, "In Progress", "running")

        self.assertFalse(task_context.clear_task(repo, note.parent / "other.md"))
        self.assertTrue((repo / task_context.CONTEXT_PATH).exists())
        self.assertTrue(task_context.clear_task(repo, note))
        self.assertFalse((repo / task_context.CONTEXT_PATH).exists())


if __name__ == "__main__":
    unittest.main()
