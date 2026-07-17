---
name: obsidian-project-workflow
description: Operate an Obsidian-backed project workflow with obsidian-cli and the Obsidian Kanban plugin. Use for project task boards, status/progress queries, requirement pool to execution/review/completion/archive flows, task note creation/movement, and human/agent handoffs in an Obsidian vault. Prefer the running Obsidian vault via obsidian-cli; never assume the current working/session directory is the vault.
---

# Obsidian Project Workflow

Obsidian is the source of truth. Use `obsidian` CLI first; use helper scripts only for deterministic scaffold/task edits. Never search or write workflow docs in the current session directory unless it is explicitly resolved as the vault.

## Fast Path

**Read-only status/query**: use `obsidian read/search/backlinks`; answer briefly. Do not initialize, create, move, or explain the workflow.

```bash
obsidian search query="Task Board" limit=20
obsidian read path="Project Name/Planning/Task Board.md"
obsidian backlinks path="Project Name/Planning/Tasks/Task Title.md"
```

For "Current project task status", report only:

```text
Current board：Backlog N / Todo N / In Progress N / Review N / Done N / Archive N
Highlights：
- In Progress：...
- Review：...
- Blocked / Missing Evidence：...
```

If evidence is absent, say `No acceptance or test evidence found`; do not infer it.
If a task note has `run_status: failed`, report its `last_failure_reason` and the latest recorded next action under `Blocked / Missing Evidence`; do not treat the task itself as completed or archived.

**Write/scaffold operations**: use scripts from this skill directory:

```bash
python3 scripts/init_project.py --project-name "Project Name" --board-name "Task Board.md"
python3 scripts/create_task.py --project-name "Project Name" --title "Improve Login Flow" --column "Backlog" --board-name "Task Board.md"
python3 scripts/record_execution.py --project-name "Project Name" --title "Improve Login Flow" --event start --executor "Codex Fixer" --model "gpt-5-codex" --repo-path "/path/to/worktree" --board-name "Task Board.md"
python3 scripts/record_execution.py --project-name "Project Name" --title "Improve Login Flow" --event succeed --executor "Codex Fixer" --model "gpt-5-codex" --result "Implementation complete; tests passed" --board-name "Task Board.md"
python3 scripts/record_execution.py --project-name "Project Name" --title "Improve Login Flow" --event fail --executor "Codex Fixer" --model "gpt-5-codex" --reason "Test environment unavailable" --next-action "Fix the environment and retry" --board-name "Task Board.md"
python3 scripts/request_review.py --project-name "Project Name" --title "Improve Login Flow" --requester "Codex Fixer" --requester-model "gpt-5-codex" --board-name "Task Board.md"
python3 scripts/record_review.py --project-name "Project Name" --title "Improve Login Flow" --reviewer "Codex Reviewer" --model "gpt-5-codex" --conclusion "Pass" --disposition "None" --decision pass --board-name "Task Board.md"
python3 scripts/record_review.py --project-name "Project Name" --title "Improve Login Flow" --reviewer "Codex Reviewer" --model "gpt-5-codex" --conclusion "Fail: regression tests are missing" --disposition "Add tests and resubmit" --decision fail --board-name "Task Board.md"
python3 scripts/record_commit.py --project-name "Project Name" --title "Improve Login Flow" --vcs git --repo-path "/path/to/repo"
python3 scripts/record_commit.py --project-name "Project Name" --title "Improve Login Flow" --vcs git --repo-path "/path/to/repo" --commit "<hash>"
python3 scripts/move_task.py --project-name "Project Name" --title "Improve Login Flow" --to-column "Done" --require-commit
python3 scripts/move_task.py --project-name "Project Name" --title "Improve Login Flow" --to-column "Done" --skip-commit-record
```

On Windows use `python`; set `PYTHONUTF8=1` for non-ASCII names.

For existing boards, keep their current card link style when moving cards. The helper scripts understand full-path wikilinks, short wikilinks, aliased wikilinks, and exact plain-text task cards; if a board uses another Kanban-compatible card shape, read the board first and preserve the surrounding Markdown instead of forcing a format migration.

When moving an existing card, `scripts/move_task.py` resolves the task note from the matched card's wikilink target before falling back to title-based filename inference.

If an existing task note filename differs from the task title, pass `--note-path` to `scripts/record_commit.py` instead of relying on title-to-filename inference.

Use `scripts/request_review.py` when a fixer resubmits work into `Review`; it records who requested the new review inside the task note. Use `scripts/record_review.py` for Review outcomes so the Review row and the follow-up column move happen together. `--decision pass` records a passing row and keeps the task in `Review` while syncing the gate; `--decision fail` records the finding and immediately moves the card back to `In Progress`.
Use `scripts/record_execution.py` for execution attempts. `start` increments `run_attempt` and moves `Todo` to `In Progress`; `succeed` records the deliverable and moves to `Review`; `fail` keeps the task in `In Progress` and requires both a failure reason and next action. The script updates the note and board together.
For repository work, pass `--repo-path` on `start`. The script adds one bounded, idempotent bootstrap block to `AGENTS.md` and `CLAUDE.md`, then writes the dynamic pointer at `.obsidian-project/current-task.md`. After `start`, immediately read the emitted current-task content and its linked task note in the same turn; writing `AGENTS.md` does not reload instructions in an already-running session. Later turns and new sessions use the pointer to recover the same task. A worktree can have only one active pointer; do not use `--replace-current-task` unless the human explicitly switches tasks.
Do not use `scripts/record_review.py --decision pass` or `--decision fail` from `In Progress`. A fixer in `In Progress` may only move the task back to `Review`; only an active reviewer in `Review` may write pass/fail Review outcomes. `scripts/record_review.py` rejects a pass/fail decision if the reviewer matches the current review requester.

## Vault And Paths

- `obsidian` CLI targets the most recently focused vault by default; use `vault=<name>` only when the user specifies a vault.
- Use `path=<vault-relative path>` for notes. `file=<name>` is acceptable only when unique.
- Resolve filesystem vault root only for helper scripts or direct filesystem fallback:
  1. active Obsidian via `obsidian eval`;
  2. explicit `--vault-path`;
  3. `OBSIDIAN_VAULT_PATH`;
  4. ask user.
- For ad hoc path resolution: `python3 scripts/resolve_vault.py`.
- Do not use `rg`, `ls`, `Get-ChildItem`, or `find` in the session directory to discover workflow notes.

## Structure

Project structure inside the vault:

```text
Project Name/
├── Docs/
└── Planning/
    ├── *Task Board.md
    └── Tasks/
```

Board columns:

```text
Backlog -> Todo -> In Progress -> Review -> Done
```

`Archive` is an optional terminal column. The default Kanban template must not include it while empty; when a user asks to archive a task, use `scripts/move_task.py --to-column Archive`, which creates:

```markdown
***

## Archive
```

and then moves the task card under that column. If the last archived task is later moved out of `Archive`, remove the empty `Archive` column.

`Task Board.md` is only the default board name. Any single-file name matching `*Task Board.md` is valid. If multiple boards exist, pass `--board-name`.

## Resources

- `assets/kanban-template.md`: board template.
- `assets/task-note-template.md`: task note template.
- `scripts/board_utils.py`: shared Kanban card matching helpers.
- `scripts/init_project.py`: scaffold project folders and board.
- `scripts/create_task.py`: create task note and board card.
- `scripts/record_execution.py`: append execution-attempt events and atomically sync task status.
- `scripts/task_context.py`: maintain the static agent bootstrap and dynamic current-task pointer.
- `scripts/move_task.py`: move card and update note status.
- `scripts/request_review.py`: resubmit a task into Review and record the current review requester.
- `scripts/record_review.py`: append a Review row and optionally sync the next workflow move.
- `scripts/record_commit.py`: append git/svn/manual commit metadata to a task note.
- `scripts/resolve_vault.py`: print resolved vault root.
- Read `references/obsidian-cli-quickref.md` only for CLI syntax.
- Read `references/workflow-model.md` only for detailed workflow gates, multi-agent handoffs, or review/acceptance rules.

## Write Rules

- Preserve Kanban frontmatter and `%% kanban:settings ... %%`.
- Do not keep an empty `Archive` column; create `Archive` only when moving/creating an archived task, and remove it when it becomes empty.
- Keep `new-note-folder` pointed at `Project Name/Planning/Tasks`.
- Use wikilinks for vault-local links.
- Create/link task notes for non-trivial cards.
- Keep task state and execution attempts separate: the board/frontmatter `status` is the task lifecycle, while `run_attempt`, `run_status`, and `## Execution Attempts` describe individual executions.
- Treat `.obsidian-project/current-task.md` as a locator, not a second source of truth. Always read the linked Obsidian task note before acting. Keep the pointer through execution, failure, retry, and Review; moving the task to `Done` or `Archive` clears it only when it still points to that task.
- Record code submission metadata in the task note's `Commit Log`: git hash, svn revision, commit author/message, or user-provided manual commit info.
- After Review is complete and the task is otherwise ready for `Done`, ask the human whether to submit/commit. If the human confirms, create the commit, record that exact commit with `scripts/record_commit.py`, then move the task to `Done`. If the human refuses, stop and do not move the task further.
- If the human already submitted the code and says the task can move to `Done`, use the commit id/revision they provide with `scripts/record_commit.py --commit <id>`, then move the task to `Done`. Do not infer the task's commit from the repository's latest commit in this case.
- If the human explicitly says no commit record is needed, move the task to `Done` with `scripts/move_task.py --skip-commit-record`; this records `commit_record_skipped: true` in frontmatter. Use this only for explicit human confirmation.
- If the user says they manually committed code, capture the commit message/revision/hash they provide and record it; do not invent missing values.
- For code tasks, set `requires_commit: true` in the task note or pass `--require-commit` when moving to `Done`, unless the human explicitly says no commit record is needed.
- Before moving a code task to `Done`, check `Commit Log`. If the commit chain lacks a commit id/hash or svn revision and the human did not explicitly waive the record, stop and ask the user for it, then record it with `scripts/record_commit.py`.
- Each move into `Review` from another column reopens `review_issues_closed: false`.
- Review closure is derived from the task note's `## Review` table. Record each row as `Time / Reviewer / Model / Conclusion / Disposition`; put the reviewer model name in `Model`. `scripts/move_task.py` sets `review_issues_closed: true` only when the latest two valid Review records have passing conclusions, such as `Pass`, `pass`, `approved`, `ok`, or `lgtm`; otherwise it keeps or sets `review_issues_closed: false`.
- Every Review attempt must append a new `## Review` row before the agent ends the turn. Do not summarize Review findings only in chat.
- If Review finds any issue, missing evidence, or required follow-up, the agent must do both of the following in the same workflow step: record the failed Review row and move the card from `Review` back to `In Progress`. Prefer `scripts/record_review.py --decision fail`; do not leave a failed task parked in `Review`.
- If Review passes, still append a Review row and sync the Review gate before asking to move on. Prefer `scripts/record_review.py --decision pass` so `review_issues_closed` reflects the latest two valid records.
- The fixer/executor must not append a passing Review row after finishing rework in `In Progress`. The correct action is only to resubmit with `scripts/request_review.py`; the next pass/fail row must be written by the reviewer while the task is actually in `Review`, and the reviewer must differ from the recorded review requester.
- Do not move a task to `Done` unless `review_issues_closed: true`. `scripts/move_task.py` checks the Review records and the frontmatter gate before allowing the move.
- Do not require commit metadata for non-code tasks.
- Before completing a write operation, verify the board changed in the resolved vault, not the session directory.
