from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("create_task", SCRIPTS / "create_task.py")
create_task = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(create_task)


BOARD_WITH_EMPTY_ARCHIVE = """---
kanban-plugin: board
---

## Backlog

## Todo

## In Progress

## Review

## Done

***

## Archive

%% kanban:settings
```
{"kanban-plugin":"board","list-collapse":[false,false,false,false,false,false],"show-checkboxes":false,"new-note-folder":"Gix/Planning/Tasks","tag-colors":[]}
```
%%
"""


class CreateTaskArchiveColumnTest(unittest.TestCase):
    def make_workspace(self) -> tuple[Path, Path]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        vault = Path(tmp.name)
        board_path = vault / "Gix" / "Planning" / "Task Board.md"
        board_path.parent.mkdir(parents=True)
        board_path.write_text(BOARD_WITH_EMPTY_ARCHIVE, encoding="utf-8")
        return vault, board_path

    def test_create_regular_task_removes_empty_archive_column(self):
        vault, board_path = self.make_workspace()

        create_task.create_task(vault, "Gix", "Task Title", "Backlog", "", "", "", False, "Task Board.md")

        board = board_path.read_text(encoding="utf-8")
        self.assertNotIn("## Archive", board)
        self.assertIn('"list-collapse":[false,false,false,false,false]', board)
        self.assertIn("## Backlog\n\n- [ ] [[Gix/Planning/Tasks/Task Title|Task Title]]", board)


if __name__ == "__main__":
    unittest.main()
