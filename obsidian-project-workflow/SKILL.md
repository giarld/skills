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
obsidian read path="项目名称/任务/项目任务看板.md"
obsidian read path="项目名称/任务/研发任务看板.md"
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
python3 scripts/init_project.py --project-name "项目名称" --board-name "研发任务看板.md"
python3 scripts/create_task.py --project-name "项目名称" --title "登录流程优化" --column "需求池" --board-name "研发任务看板.md"
python3 scripts/move_task.py --project-name "项目名称" --title "登录流程优化" --to-column "Review" --board-name "研发任务看板.md"
```

On Windows use `python`; set `PYTHONUTF8=1` for non-ASCII names.

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

`项目任务看板.md` is only the default board name. Any single-file name matching `*任务看板.md` is valid, such as `研发任务看板.md`. If multiple boards exist, pass `--board-name`.

## Resources

- `assets/kanban-template.md`: board template.
- `assets/task-note-template.md`: task note template.
- `scripts/init_project.py`: scaffold project folders and board.
- `scripts/create_task.py`: create task note and board card.
- `scripts/move_task.py`: move card and update note status.
- `scripts/resolve_vault.py`: print resolved vault root.
- Read `references/obsidian-cli-quickref.md` only for CLI syntax.
- Read `references/workflow-model.md` only for detailed workflow gates, multi-agent handoffs, or review/acceptance rules.

## Write Rules

- Preserve Kanban frontmatter and `%% kanban:settings ... %%`.
- Keep `new-note-folder` pointed at `项目名称/任务/Tasks`.
- Use wikilinks for vault-local links.
- Create/link task notes for non-trivial cards.
- Before completing a write operation, verify the board changed in the resolved vault, not the session directory.
