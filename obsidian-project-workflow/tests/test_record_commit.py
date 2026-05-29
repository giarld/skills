from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("record_commit", SCRIPTS / "record_commit.py")
record_commit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(record_commit)


class RecordCommitTest(unittest.TestCase):
    def test_read_git_commit_uses_given_commit_ref(self):
        repo = Path("/tmp/repo")

        with mock.patch.object(record_commit, "run_command", return_value="abc123\tGxin\t2026-01-02T00:00:00+08:00\tmessage") as run:
            commit = record_commit.read_git_commit(repo, "abc123")

        run.assert_called_once_with(
            ["git", "show", "-s", "--pretty=format:%H%x09%an%x09%cI%x09%s", "abc123"],
            repo,
        )
        self.assertEqual(commit["commit"], "abc123")
        self.assertEqual(commit["source"], "git/show")

    def test_read_git_commit_defaults_to_head(self):
        repo = Path("/tmp/repo")

        with mock.patch.object(record_commit, "run_command", return_value="def456\tGxin\t2026-01-02T00:00:00+08:00\tmessage") as run:
            commit = record_commit.read_git_commit(repo)

        run.assert_called_once_with(
            ["git", "show", "-s", "--pretty=format:%H%x09%an%x09%cI%x09%s", "HEAD"],
            repo,
        )
        self.assertEqual(commit["commit"], "def456")


if __name__ == "__main__":
    unittest.main()
