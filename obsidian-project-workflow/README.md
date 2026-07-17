# obsidian-project-workflow

A general-purpose agent skill for Obsidian project management. It keeps task status, analysis, execution attempts, Review results, commit metadata, and acceptance evidence in one Obsidian vault instead of scattering them across chats, terminal output, and temporary files.

## Features

- Read Obsidian Kanban boards and report concise project status.
- Initialize project folders, a task board, and task notes.
- Move tasks through `Backlog -> Todo -> In Progress -> Review -> Done`.
- Create `Archive` only when needed and remove it again when empty.
- Track task lifecycle separately from execution attempts, failures, and retries.
- Record Review history, acceptance evidence, and git, svn, or manual commit metadata.
- Keep an active repository worktree linked to the correct Obsidian task.

## Installation

```bash
npx skills add https://github.com/giarld/skills --skill obsidian-project-workflow
```

## Requirements

1. Install and start Obsidian.
2. Enable the Obsidian command-line interface and verify it with `obsidian help`.
3. Install and enable the Obsidian Kanban plugin.
4. Focus the target vault, or explicitly provide the vault when several are open.

On Windows, use `python` when appropriate and set `PYTHONUTF8=1` for non-ASCII project or task names.

## Quick Start

Read the current board:

```bash
obsidian search query="Task Board" limit=20
obsidian read path="Project Name/Planning/Task Board.md"
```

Initialize a project and create a task:

```bash
python3 scripts/init_project.py --project-name "Project Name" --board-name "Task Board.md"
python3 scripts/create_task.py --project-name "Project Name" --title "Improve Login Flow" --column "Backlog" --board-name "Task Board.md"
```

Record execution:

```bash
python3 scripts/record_execution.py --project-name "Project Name" --title "Improve Login Flow" --event start --executor "Codex Fixer" --model "gpt-5-codex" --repo-path "/path/to/worktree" --board-name "Task Board.md"
python3 scripts/record_execution.py --project-name "Project Name" --title "Improve Login Flow" --event succeed --executor "Codex Fixer" --model "gpt-5-codex" --result "Implementation complete; tests passed" --board-name "Task Board.md"
python3 scripts/record_execution.py --project-name "Project Name" --title "Improve Login Flow" --event fail --executor "Codex Fixer" --model "gpt-5-codex" --reason "Test environment unavailable" --next-action "Fix the environment and retry" --board-name "Task Board.md"
```

When `start` receives `--repo-path`, the script:

- Maintains a bounded bootstrap rule in `AGENTS.md` and `CLAUDE.md` without replacing existing content.
- Writes `.obsidian-project/current-task.md` as a dynamic pointer to the unique Obsidian task note.
- Adds that pointer to the worktree's local `.git/info/exclude`.
- Prints the current task context so the active conversation can read it immediately.
- Keeps the pointer through failure, retry, and Review, then removes it when the task enters `Done` or `Archive`.

A worktree may have only one active task by default. Use `--replace-current-task` only after a human explicitly switches tasks; use separate worktrees for parallel tasks.

Request and record Review:

```bash
python3 scripts/request_review.py --project-name "Project Name" --title "Improve Login Flow" --requester "Codex Fixer" --requester-model "gpt-5-codex" --board-name "Task Board.md"
python3 scripts/record_review.py --project-name "Project Name" --title "Improve Login Flow" --reviewer "Codex Reviewer" --model "gpt-5-codex" --conclusion "Pass" --disposition "None" --decision pass --board-name "Task Board.md"
python3 scripts/record_review.py --project-name "Project Name" --title "Improve Login Flow" --reviewer "Codex Reviewer" --model "gpt-5-codex" --conclusion "Fail: regression tests are missing" --disposition "Add tests and resubmit" --decision fail --board-name "Task Board.md"
```

Record a code commit:

```bash
python3 scripts/record_commit.py --project-name "Project Name" --title "Improve Login Flow" --vcs git --repo-path "/path/to/repo"
python3 scripts/record_commit.py --project-name "Project Name" --title "Improve Login Flow" --vcs git --repo-path "/path/to/repo" --commit "<hash>"
```

## Workflow

```text
Backlog -> Todo -> In Progress -> Review -> Done -> Archive
```

- `Backlog`: ideas, requests, bugs, and opportunities.
- `Todo`: scoped work with an owner, next action, and acceptance criteria.
- `In Progress`: active implementation and evidence collection.
- `Review`: independent review of changes and evidence.
- `Done`: accepted work that satisfies all completion gates.
- `Archive`: historical, rejected, expired, or closed work.

Every entry into `Review` reopens `review_issues_closed: false`. A failing Review must append a Review row and return the task to `In Progress` in the same workflow step. A fixer may resubmit with `request_review.py`, but only a different reviewer may record the next pass or fail result.

Moving to `Done` requires two consecutive passing Review records and `review_issues_closed: true`. Code tasks with `requires_commit: true` or `--require-commit` also require a recorded commit id, hash, or svn revision. Use `--skip-commit-record` only after explicit human confirmation.

## Vault Structure

```text
Project Name/
├── Docs/
└── Planning/
    ├── *Task Board.md
    └── Tasks/
```

`Task Board.md` is the default. A single board matching `*Task Board.md` is also accepted; pass `--board-name` when several boards exist.

## Resources

- `SKILL.md`: core agent instructions.
- `assets/kanban-template.md`: Kanban board template.
- `assets/task-note-template.md`: task note template.
- `scripts/init_project.py`: initialize project folders and a board.
- `scripts/create_task.py`: create a task note and board card.
- `scripts/record_execution.py`: record an execution attempt and synchronize state.
- `scripts/task_context.py`: maintain repository bootstrap rules and the active-task pointer.
- `scripts/move_task.py`: move a task card and synchronize note status.
- `scripts/request_review.py`: resubmit a task to Review.
- `scripts/record_review.py`: append a Review record and synchronize the next state.
- `scripts/record_commit.py`: append git, svn, or manual commit metadata.
- `scripts/resolve_vault.py`: resolve the active Obsidian vault.
- `references/obsidian-cli-quickref.md`: Obsidian CLI syntax.
- `references/workflow-model.md`: workflow gates and handoff rules.

## Path Rules

- Treat the Obsidian vault as the project source of truth.
- Prefer the `obsidian` CLI for the active vault.
- Never treat the session directory, source repository, or installed skill directory as the vault.
- Resolve the vault filesystem path only for helper scripts or when the CLI cannot perform the operation.
