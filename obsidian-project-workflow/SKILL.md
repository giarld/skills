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
python3 scripts/move_task.py --project-name "项目名称" --title "登录流程优化" --to-column "Review" --board-name "任务看板.md"
python3 scripts/record_commit.py --project-name "项目名称" --title "登录流程优化" --vcs git --repo-path "/path/to/repo"
python3 scripts/move_task.py --project-name "项目名称" --title "登录流程优化" --to-column "完成" --require-commit
```

On Windows use `python`; set `PYTHONUTF8=1` for non-ASCII names.

For existing boards, keep their current card link style when moving cards. The helper scripts understand full-path wikilinks, short wikilinks, aliased wikilinks, and exact plain-text task cards; if a board uses another Kanban-compatible card shape, read the board first and preserve the surrounding Markdown instead of forcing a format migration.

When moving an existing card, `scripts/move_task.py` resolves the task note from the matched card's wikilink target before falling back to title-based filename inference.

If an existing task note filename differs from the task title, pass `--note-path` to `scripts/record_commit.py` instead of relying on title-to-filename inference.

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
需求池 -> 待执行 -> 执行中 -> Review -> 完成 -> Archive
```

`任务看板.md` is only the default board name. Any single-file name matching `*任务看板.md` is valid. If multiple boards exist, pass `--board-name`.

## Resources

- `assets/kanban-template.md`: board template.
- `assets/task-note-template.md`: task note template.
- `scripts/board_utils.py`: shared Kanban card matching helpers.
- `scripts/init_project.py`: scaffold project folders and board.
- `scripts/create_task.py`: create task note and board card.
- `scripts/move_task.py`: move card and update note status.
- `scripts/record_commit.py`: append git/svn/manual commit metadata to a task note.
- `scripts/resolve_vault.py`: print resolved vault root.
- Read `references/obsidian-cli-quickref.md` only for CLI syntax.
- Read `references/workflow-model.md` only for detailed workflow gates, multi-agent handoffs, or review/acceptance rules.

## Write Rules

- Preserve Kanban frontmatter and `%% kanban:settings ... %%`.
- Keep `new-note-folder` pointed at `项目名称/任务/Tasks`.
- Use wikilinks for vault-local links.
- Create/link task notes for non-trivial cards.
- Record code submission metadata in the task note's `提交记录`: git hash, svn revision, commit author/message, or user-provided manual commit info.
- If the user says they manually committed code, capture the commit message/revision/hash they provide and record it; do not invent missing values.
- For code tasks, set `requires_commit: true` in the task note or pass `--require-commit` when moving to `完成`.
- Before moving a code task to `完成`, check `提交记录`. If the commit chain lacks a commit id/hash or svn revision, stop and ask the user for it, then record it with `scripts/record_commit.py`.
- Each move into `Review` starts a new review round. `scripts/move_task.py` increments `review_rounds` and resets `review_issues_closed: false` when the card enters `Review` from another column.
- Do not move a task to `完成` until it has completed at least 3 review rounds and all review issues are closed. `scripts/move_task.py` enforces `review_rounds >= 3` and `review_issues_closed: true`; set `review_issues_closed: true` only after recorded review findings are resolved or intentionally closed.
- Do not require commit metadata for non-code tasks.
- Before completing a write operation, verify the board changed in the resolved vault, not the session directory.
