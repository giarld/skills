# Workflow model

Load this reference only for task creation, planning, multi-agent handoff, review, acceptance, or archive decisions. For read-only status summaries, use the concise Status Query rules in SKILL.md instead.

## Board states

| State | Meaning | Entry requirement | Exit requirement |
| --- | --- | --- | --- |
| Backlog | Raw ideas, requests, bugs, or opportunities | Clear title and source | Analysis note created or item rejected/archived |
| Todo | Ready work | Scope, next action, owner/role, acceptance criteria | Owner starts work |
| In Progress | Active execution | Owner/agent assigned | Deliverable produced and evidence recorded |
| Review | Review and rework loop | Changed artifacts and validation evidence available | Latest two valid Review records pass and findings are closed, or returned to execution |
| Done | Accepted work | Acceptance criteria satisfied and `review_issues_closed: true` | Optional archive after it is no longer operational |
| Archive | Historical/stale/completed record | Reason for archive is clear | Usually terminal |

## Task note minimum fields

- Background: why this exists.
- Goal: what success looks like.
- Scope: included and excluded work.
- Acceptance criteria: checkable statements.
- Dependencies and risks: links to related notes or blockers.
- Execution log: timestamped activity.
- Execution attempts: append-only `start` / `succeed` / `fail` events with attempt number, executor, model, result or failure reason, and next action.
- Commit log: git/svn/manual submission metadata when code is committed during the task.
- Commit gate: set `requires_commit: true` only for tasks that must produce code submissions.
- Review: reviewer findings and disposition.
- Review records: each row in `## Review` records time, reviewer, model name, conclusion, and disposition. `review_issues_closed` is true only when the latest two valid Review records have passing conclusions.
- Evidence: tests, screenshots, logs, or links proving completion.

## Workflow steps

1. Capture ideas in `Backlog`: concise card, source/problem/value/unknowns in a linked task note when analysis is needed.
2. Analyze to `Todo`: scope, constraints, dependencies, acceptance criteria, and proposed breakdown are clear.
3. Execute in `In Progress`: use `record_execution.py --event start` to open an attempt. For repository work, bind its worktree with `--repo-path`; this installs a static `AGENTS.md` / `CLAUDE.md` bootstrap and writes `.obsidian-project/current-task.md`. The agent must immediately read the generated pointer and linked task note in the current turn. Record decisions, commands, outputs, changed files, commit metadata, and questions. End the attempt with `succeed` (moves to Review) or `fail` (stays in execution with reason and next action). A retry is a new `start`, never an overwrite of the failed attempt.
4. Review in `Review`: reviewer, reviewer model name, focus, changed artifacts, evidence, and findings recorded in `## Review`. Each Review attempt must append a new Review row before the turn ends. Each entry into `Review` from another column reopens `review_issues_closed: false`. If fixes are required, first record the failed Review row, then move the card back to `In Progress` in the same workflow step; do not leave a failed task in `Review`. After rework, the fixer should only resubmit the task from `In Progress` back to `Review` with `scripts/request_review.py`; the fixer must not append a passing Review row on behalf of the reviewer. When this happens, keep `review_issues_closed: false` until two consecutive passing Review records are recorded. Prefer `scripts/record_review.py --decision fail` for the fail path and `scripts/record_review.py --decision pass` for the pass path.
5. Complete/archive: move to `Done` only when acceptance criteria and evidence exist, the latest two valid Review records have passing conclusions, and `review_issues_closed: true`; move stale or historical records to `Archive`.

## Conversation and repository context

- `AGENTS.md` and `CLAUDE.md` contain only a stable instruction to read `.obsidian-project/current-task.md`; task-specific content never accumulates in those files.
- `.obsidian-project/current-task.md` identifies one task note and execution attempt for one worktree. The linked task note remains authoritative.
- Creating the files does not refresh an already-running model session. The skill must read the emitted pointer and task note immediately after `start`, which brings the task context into the current conversation through tool output.
- The pointer persists across turns, failed attempts, retries, and Review. It is removed when the matching task enters `Done` or `Archive`.
- Use separate worktrees for parallel tasks. Replacing a different active pointer requires explicit human intent.

## Multi-agent handoff pattern

Use this structure in the task note when work changes hands:

```markdown
### Handoff YYYY-MM-DD HH:mm

- From:
- To:
- Current state:
- Required outcome:
- Inputs:
- Constraints:
- Acceptance criteria:
- Known risks:
```

Every handoff should state current state, desired outcome, inputs, constraints, deliverables, acceptance criteria, review expectations, and known risks. Prefer small task notes owned by one actor; use parent/child wikilinks for parallel work.

## Review gate

When a task is currently in `Review`:

- Every Review attempt must append a row to `## Review`, even if the outcome is "needs fixes" or "missing evidence".
- A failing Review is not complete until the task is moved back to `In Progress`.
- A passing Review should stay in `Review` until all completion gates are satisfied; record the passing row and sync the gate before asking the human about commit/submission or moving to `Done`.
- A fixer working in `In Progress` may not write a passing Review result. After fixes, the fixer only resubmits the task to `Review` with `scripts/request_review.py`; the reviewer records the next pass/fail outcome there, and the reviewer must differ from that round's recorded requester.

Do not move a card from `Review` to `Done` unless:

- The task's commit chain is complete when code was submitted and the task has `requires_commit: true` or the move command uses `--require-commit`. If `Commit Log` lacks a commit id/hash or svn revision, ask the user for the commit id before moving the card.
- If the human explicitly says no commit record is needed, the card may move to `Done` with `scripts/move_task.py --skip-commit-record`, which records `commit_record_skipped: true`.
- The review conclusions are explicit.
- The latest two valid Review records have passing conclusions.
- `review_issues_closed` is true.
- Required fixes are complete or intentionally deferred.
- Acceptance criteria are checked or updated with a reason.
- Evidence is linked or summarized in the task note.

## Commit recording

When code is submitted during task execution, record it in `## Commit Log`.

- Git: record commit hash, author, and message.
- SVN: record revision, author, and message.
- Manual user commit: if the user says they committed manually, record the commit hash/revision/message they provide and mark source as `user/manual`. Manual records must include a commit hash or revision.
- After Review passes, ask the human whether to submit/commit before creating a commit. If the human confirms, create the commit, record that exact commit, then move the task to `Done`. If the human refuses, stop.
- If the human already submitted code and says the task can move to `Done`, record only the commit id/revision the human provides. Do not infer the task commit from the repository's latest commit.
- If the human explicitly says no commit record is needed, skip commit recording and complete the task.
- Do not run commit commands solely for logging; logging records existing or user-provided submission metadata.

## Knowledge indexing

- Store overview/design/decision notes under `Docs/`.
- Link task notes to relevant docs and docs back to active tasks.
- Use Obsidian search, tags, backlinks, and frontmatter properties for discovery.
