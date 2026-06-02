---
name: obsidian-project-workflow
description: Operate an Obsidian-backed project workflow with obsidian-cli and the Obsidian Kanban plugin. Use for project task boards, status/progress queries, requirement pool to execution/review/completion/archive flows, task note creation/movement, and human/agent handoffs in an Obsidian vault. Prefer the running Obsidian vault via obsidian-cli; never assume the current working/session directory is the vault.
---

# Obsidian Project Workflow

Obsidian is the source of truth. Use `obsidian` CLI first; use helper scripts only for deterministic scaffold/task edits. Never search or write workflow docs in the current session directory unless it is explicitly resolved as the vault.

## Fast Path

**Read-only status/query**: use `obsidian read/search/backlinks`; answer briefly. Do not initialize, create, move, or explain the workflow.

```bash
obsidian search query="任务看板" limit=20
obsidian read path="项目名称/任务/任务看板.md"
obsidian backlinks path="项目名称/任务/Tasks/任务标题.md"
```

For "当前项目任务实施情况", report only:

```text
当前看板：需求池 N / 待执行 N / 执行中 N / Review N / 完成 N / Archive N
重点：
- 执行中：...
- Review：...
- 阻塞/缺证据：...
```

If evidence is absent, say `未看到验收/测试证据`; do not infer it.

**Write/scaffold operations**: use scripts from this skill directory:

```bash
python3 scripts/init_project.py --project-name "项目名称" --board-name "任务看板.md"
python3 scripts/create_task.py --project-name "项目名称" --title "登录流程优化" --column "需求池" --board-name "任务看板.md"
python3 scripts/request_review.py --project-name "项目名称" --title "登录流程优化" --requester "Codex Fixer" --requester-model "gpt-5-codex" --board-name "任务看板.md"
python3 scripts/record_review.py --project-name "项目名称" --title "登录流程优化" --reviewer "Codex Reviewer" --model "gpt-5-codex" --conclusion "通过" --disposition "无" --decision pass --board-name "任务看板.md"
python3 scripts/record_review.py --project-name "项目名称" --title "登录流程优化" --reviewer "Codex Reviewer" --model "gpt-5-codex" --conclusion "不通过：缺少回归测试" --disposition "补测试后重提" --decision fail --board-name "任务看板.md"
python3 scripts/record_commit.py --project-name "项目名称" --title "登录流程优化" --vcs git --repo-path "/path/to/repo"
python3 scripts/record_commit.py --project-name "项目名称" --title "登录流程优化" --vcs git --repo-path "/path/to/repo" --commit "<hash>"
python3 scripts/move_task.py --project-name "项目名称" --title "登录流程优化" --to-column "完成" --require-commit
python3 scripts/move_task.py --project-name "项目名称" --title "登录流程优化" --to-column "完成" --skip-commit-record
```

On Windows use `python`; set `PYTHONUTF8=1` for non-ASCII names.

For existing boards, keep their current card link style when moving cards. The helper scripts understand full-path wikilinks, short wikilinks, aliased wikilinks, and exact plain-text task cards; if a board uses another Kanban-compatible card shape, read the board first and preserve the surrounding Markdown instead of forcing a format migration.

When moving an existing card, `scripts/move_task.py` resolves the task note from the matched card's wikilink target before falling back to title-based filename inference.

If an existing task note filename differs from the task title, pass `--note-path` to `scripts/record_commit.py` instead of relying on title-to-filename inference.

Use `scripts/request_review.py` when a fixer resubmits work into `Review`; it records who requested the new review inside the task note. Use `scripts/record_review.py` for Review outcomes so the Review row and the follow-up column move happen together. `--decision pass` records a passing row and keeps the task in `Review` while syncing the gate; `--decision fail` records the finding and immediately moves the card back to `执行中`.
Do not use `scripts/record_review.py --decision pass` or `--decision fail` from `执行中`. A fixer in `执行中` may only move the task back to `Review`; only an active reviewer in `Review` may write pass/fail Review outcomes. `scripts/record_review.py` rejects a pass/fail decision if the reviewer matches the current review requester.

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
项目名称/
├── 文档/
└── 任务/
    ├── *任务看板.md
    └── Tasks/
```

Board columns:

```text
需求池 -> 待执行 -> 执行中 -> Review -> 完成
```

`Archive` is an optional terminal column. The default Kanban template must not include it while empty; when a user asks to archive a task, use `scripts/move_task.py --to-column Archive`, which creates:

```markdown
***

## Archive
```

and then moves the task card under that column. If the last archived task is later moved out of `Archive`, remove the empty `Archive` column.

`任务看板.md` is only the default board name. Any single-file name matching `*任务看板.md` is valid. If multiple boards exist, pass `--board-name`.

## Resources

- `assets/kanban-template.md`: board template.
- `assets/task-note-template.md`: task note template.
- `scripts/board_utils.py`: shared Kanban card matching helpers.
- `scripts/init_project.py`: scaffold project folders and board.
- `scripts/create_task.py`: create task note and board card.
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
- Keep `new-note-folder` pointed at `项目名称/任务/Tasks`.
- Use wikilinks for vault-local links.
- Create/link task notes for non-trivial cards.
- Record code submission metadata in the task note's `提交记录`: git hash, svn revision, commit author/message, or user-provided manual commit info.
- After Review is complete and the task is otherwise ready for `完成`, ask the human whether to submit/commit. If the human confirms, create the commit, record that exact commit with `scripts/record_commit.py`, then move the task to `完成`. If the human refuses, stop and do not move the task further.
- If the human already submitted the code and says the task can move to `完成`, use the commit id/revision they provide with `scripts/record_commit.py --commit <id>`, then move the task to `完成`. Do not infer the task's commit from the repository's latest commit in this case.
- If the human explicitly says no commit record is needed, move the task to `完成` with `scripts/move_task.py --skip-commit-record`; this records `commit_record_skipped: true` in frontmatter. Use this only for explicit human confirmation.
- If the user says they manually committed code, capture the commit message/revision/hash they provide and record it; do not invent missing values.
- For code tasks, set `requires_commit: true` in the task note or pass `--require-commit` when moving to `完成`, unless the human explicitly says no commit record is needed.
- Before moving a code task to `完成`, check `提交记录`. If the commit chain lacks a commit id/hash or svn revision and the human did not explicitly waive the record, stop and ask the user for it, then record it with `scripts/record_commit.py`.
- Each move into `Review` from another column reopens `review_issues_closed: false`.
- Review closure is derived from the task note's `## Review` table. Record each row as `时间 / Reviewer / 模型 / 结论 / 处理`; put the reviewer model name in `模型`. `scripts/move_task.py` sets `review_issues_closed: true` only when the latest two valid Review records have passing conclusions, such as `通过`, `pass`, `approved`, `ok`, or `lgtm`; otherwise it keeps or sets `review_issues_closed: false`.
- Every Review attempt must append a new `## Review` row before the agent ends the turn. Do not summarize Review findings only in chat.
- If Review finds any issue, missing evidence, or required follow-up, the agent must do both of the following in the same workflow step: record the failed Review row and move the card from `Review` back to `执行中`. Prefer `scripts/record_review.py --decision fail`; do not leave a failed task parked in `Review`.
- If Review passes, still append a Review row and sync the Review gate before asking to move on. Prefer `scripts/record_review.py --decision pass` so `review_issues_closed` reflects the latest two valid records.
- The fixer/executor must not append a passing Review row after finishing rework in `执行中`. The correct action is only to resubmit with `scripts/request_review.py`; the next pass/fail row must be written by the reviewer while the task is actually in `Review`, and the reviewer must differ from the recorded review requester.
- Do not move a task to `完成` unless `review_issues_closed: true`. `scripts/move_task.py` checks the Review records and the frontmatter gate before allowing the move.
- Do not require commit metadata for non-code tasks.
- Before completing a write operation, verify the board changed in the resolved vault, not the session directory.
