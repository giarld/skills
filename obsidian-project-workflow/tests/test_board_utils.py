from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("board_utils", SCRIPTS / "board_utils.py")
board_utils = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(board_utils)


BOARD_WITH_DONE_CARD_AND_EMPTY_ARCHIVE = """---
kanban-plugin: board
---

## 需求池

## 待执行

## 执行中

## Review

## 完成

- [ ] card

***

## Archive

%% kanban:settings
```
{"kanban-plugin":"board","list-collapse":[false,false,false,false,false,false],"show-checkboxes":false,"new-note-folder":"Gix/任务/Tasks","tag-colors":[]}
```
%%
"""


class BoardUtilsArchiveColumnTest(unittest.TestCase):
    def test_remove_empty_archive_keeps_blank_line_before_settings(self):
        board = board_utils.remove_empty_archive_column(BOARD_WITH_DONE_CARD_AND_EMPTY_ARCHIVE)

        self.assertNotIn("## Archive", board)
        self.assertIn("- [ ] card\n\n%% kanban:settings", board)
        self.assertIn('"list-collapse":[false,false,false,false,false]', board)

    def test_blank_line_before_settings_is_idempotent(self):
        board = BOARD_WITH_DONE_CARD_AND_EMPTY_ARCHIVE.replace(
            "- [ ] card\n\n***",
            "- [ ] card\n\n\n\n***",
        )

        once = board_utils.remove_empty_archive_column(board)
        twice = board_utils.remove_empty_archive_column(once)

        self.assertEqual(once, twice)
        self.assertIn("- [ ] card\n\n%% kanban:settings", once)
        self.assertNotIn("- [ ] card\n\n\n%% kanban:settings", once)


if __name__ == "__main__":
    unittest.main()
