# Workflow model

Load this reference only for task creation, planning, multi-agent handoff, review, acceptance, or archive decisions. For read-only status summaries, use the concise Status Query rules in SKILL.md instead.

## Board states

| State | Meaning | Entry requirement | Exit requirement |
| --- | --- | --- | --- |
| 需求池 | Raw ideas, requests, bugs, or opportunities | Clear title and source | Analysis note created or item rejected/archived |
| 待执行 | Ready work | Scope, next action, owner/role, acceptance criteria | Owner starts work |
| 执行中 | Active execution | Owner/agent assigned | Deliverable produced and evidence recorded |
| Review | Review and rework loop | Changed artifacts and validation evidence available | Latest two valid Review records pass and findings are closed, or returned to execution |
| 完成 | Accepted work | Acceptance criteria satisfied and `review_issues_closed: true` | Optional archive after it is no longer operational |
| Archive | Historical/stale/completed record | Reason for archive is clear | Usually terminal |

## Task note minimum fields

- Background: why this exists.
- Goal: what success looks like.
- Scope: included and excluded work.
- Acceptance criteria: checkable statements.
- Dependencies and risks: links to related notes or blockers.
- Execution log: timestamped activity.
- Commit log: git/svn/manual submission metadata when code is committed during the task.
- Commit gate: set `requires_commit: true` only for tasks that must produce code submissions.
- Review: reviewer findings and disposition.
- Review records: each row in `## Review` records time, reviewer, model name, conclusion, and disposition. `review_issues_closed` is true only when the latest two valid Review records have passing conclusions.
- Evidence: tests, screenshots, logs, or links proving completion.

## Workflow steps

1. Capture ideas in `需求池`: concise card, source/problem/value/unknowns in a linked task note when analysis is needed.
2. Analyze to `待执行`: scope, constraints, dependencies, acceptance criteria, and proposed breakdown are clear.
3. Execute in `执行中`: owner or agent role assigned; decisions, commands, outputs, changed files, commit metadata, and questions recorded.
4. Review in `Review`: reviewer, reviewer model name, focus, changed artifacts, evidence, and findings recorded in `## Review`. Each Review attempt must append a new Review row before the turn ends. Each entry into `Review` from another column reopens `review_issues_closed: false`. If fixes are required, first record the failed Review row, then move the card back to `执行中` in the same workflow step; do not leave a failed task in `Review`. After rework, the fixer should only resubmit the task from `执行中` back to `Review` with `scripts/request_review.py`; the fixer must not append a passing Review row on behalf of the reviewer. When this happens, keep `review_issues_closed: false` until two consecutive passing Review records are recorded. Prefer `scripts/record_review.py --decision fail` for the fail path and `scripts/record_review.py --decision pass` for the pass path.
5. Complete/archive: move to `完成` only when acceptance criteria and evidence exist, the latest two valid Review records have passing conclusions, and `review_issues_closed: true`; move stale or historical records to `Archive`.

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
- A failing Review is not complete until the task is moved back to `执行中`.
- A passing Review should stay in `Review` until all completion gates are satisfied; record the passing row and sync the gate before asking the human about commit/submission or moving to `完成`.
- A fixer working in `执行中` may not write a passing Review result. After fixes, the fixer only resubmits the task to `Review` with `scripts/request_review.py`; the reviewer records the next pass/fail outcome there, and the reviewer must differ from that round's recorded requester.

Do not move a card from `Review` to `完成` unless:

- The task's commit chain is complete when code was submitted and the task has `requires_commit: true` or the move command uses `--require-commit`. If `提交记录` lacks a commit id/hash or svn revision, ask the user for the commit id before moving the card.
- If the human explicitly says no commit record is needed, the card may move to `完成` with `scripts/move_task.py --skip-commit-record`, which records `commit_record_skipped: true`.
- The review conclusions are explicit.
- The latest two valid Review records have passing conclusions.
- `review_issues_closed` is true.
- Required fixes are complete or intentionally deferred.
- Acceptance criteria are checked or updated with a reason.
- Evidence is linked or summarized in the task note.

## Commit recording

When code is submitted during task execution, record it in `## 提交记录`.

- Git: record commit hash, author, and message.
- SVN: record revision, author, and message.
- Manual user commit: if the user says they committed manually, record the commit hash/revision/message they provide and mark source as `user/manual`. Manual records must include a commit hash or revision.
- After Review passes, ask the human whether to submit/commit before creating a commit. If the human confirms, create the commit, record that exact commit, then move the task to `完成`. If the human refuses, stop.
- If the human already submitted code and says the task can move to `完成`, record only the commit id/revision the human provides. Do not infer the task commit from the repository's latest commit.
- If the human explicitly says no commit record is needed, skip commit recording and complete the task.
- Do not run commit commands solely for logging; logging records existing or user-provided submission metadata.

## Knowledge indexing

- Store overview/design/decision notes under `文档/`.
- Link task notes to relevant docs and docs back to active tasks.
- Use Obsidian search, tags, backlinks, and frontmatter properties for discovery.
