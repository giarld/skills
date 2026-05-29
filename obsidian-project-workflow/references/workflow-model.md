# Workflow model

Load this reference only for task creation, planning, multi-agent handoff, review, acceptance, or archive decisions. For read-only status summaries, use the concise Status Query rules in SKILL.md instead.

## Board states

| State | Meaning | Entry requirement | Exit requirement |
| --- | --- | --- | --- |
| 需求池 | Raw ideas, requests, bugs, or opportunities | Clear title and source | Analysis note created or item rejected/archived |
| 待执行 | Ready work | Scope, next action, owner/role, acceptance criteria | Owner starts work |
| 执行中 | Active execution | Owner/agent assigned | Deliverable produced and evidence recorded |
| Review | Review and rework loop | Changed artifacts and validation evidence available | Accepted or returned to execution |
| 完成 | Accepted work | Acceptance criteria satisfied | Optional archive after it is no longer operational |
| Archive | Historical/stale/completed record | Reason for archive is clear | Usually terminal |

## Task note minimum fields

- Background: why this exists.
- Goal: what success looks like.
- Scope: included and excluded work.
- Acceptance criteria: checkable statements.
- Dependencies and risks: links to related notes or blockers.
- Execution log: timestamped activity.
- Review: reviewer findings and disposition.
- Evidence: tests, screenshots, logs, or links proving completion.

## Workflow steps

1. Capture ideas in `需求池`: concise card, source/problem/value/unknowns in a linked task note when analysis is needed.
2. Analyze to `待执行`: scope, constraints, dependencies, acceptance criteria, and proposed breakdown are clear.
3. Execute in `执行中`: owner or agent role assigned; decisions, commands, outputs, changed files, and questions recorded.
4. Review in `Review`: reviewer, focus, changed artifacts, evidence, and findings recorded. Return to `执行中` if fixes are required.
5. Complete/archive: move to `完成` only when acceptance criteria and evidence exist; move stale or historical records to `Archive`.

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

Do not move a card from `Review` to `完成` unless:

- The review conclusion is explicit.
- Required fixes are complete or intentionally deferred.
- Acceptance criteria are checked or updated with a reason.
- Evidence is linked or summarized in the task note.

## Knowledge indexing

- Store overview/design/decision notes under `文档/`.
- Link task notes to relevant docs and docs back to active tasks.
- Use Obsidian search, tags, backlinks, and frontmatter properties for discovery.
