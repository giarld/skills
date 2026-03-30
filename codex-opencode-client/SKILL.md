---
name: codex-opencode-client
description: Codex acts as Party A and delegates bounded implementation work to OpenCode as Party B, then reviews and accepts or rejects the result.
---

# Codex OpenCode Client

Use this skill when Codex should orchestrate work and OpenCode should execute it.

Operating model:

- Codex is Party A.
- OpenCode is Party B.
- Codex owns scoping, constraints, acceptance, and final synthesis.
- OpenCode owns execution only.
- OpenCode must not redefine the task, expand scope, or silently change acceptance criteria.

This skill must work with both:

- plain OpenCode
- OpenCode with `oh-my-opencode` installed

## When To Use

Use this skill when:

- Codex needs to delegate a bounded coding task to OpenCode.
- The task can be expressed as a concrete contract.
- Codex needs a clear accept/reject loop for OpenCode output.
- Codex wants to inspect OpenCode results without giving up control of the workflow.

Do not use this skill when:

- The task is too vague to contract.
- Codex does not know the target workspace.
- The work requires continuous interactive steering better handled directly by Codex.

## Runtime Detection

Before delegation, Codex should determine whether the target runtime is plain OpenCode or an `oh-my-opencode` distribution.

Treat `oh-my-opencode` as installed if any of the following are true:

- `opencode --version` identifies an Oh My OpenCode build
- the OpenCode plugin list contains `oh-my-opencode`
- `.opencode/oh-my-opencode.json` or `.opencode/oh-my-opencode.jsonc` exists

Prefer project-local evidence and workspace-safe CLI checks.

Inspect user-level config such as `~/.config/opencode/oh-my-opencode.json` or `.jsonc` only if the user explicitly authorizes reading outside the workspace.

If runtime detection is not possible, assume the command may still be wrapped by `oh-my-opencode` behavior and keep the contract strict.

## Contract-First Rule

Before invoking OpenCode, Codex must write a compact contract in plain language.

Every contract must include:

1. Objective
2. Workspace path
3. Allowed write scope
4. Forbidden changes
5. Deliverables
6. Acceptance criteria
7. Verification expectations
8. Failure reporting format

Every contract must also include these default control clauses, even when `oh-my-opencode` was not positively detected:

- Party B may not further delegate unless the contract explicitly allows subagents.
- Party B may not create parallel workstreams unless the contract explicitly allows them.
- Party B must treat planning as internal only and must not expand the requested deliverables.
- Party B must disclose any hook, built-in skill, MCP tool, formatter, or runtime default that changed files or execution flow.
- Party B must report automatic formatting or lint fixes that changed additional lines.

Preferred contract template:

```text
Party A Contract for Party B

Objective:
- <what must be accomplished>

Workspace:
- <absolute workspace path>

Allowed write scope:
- <files or directories that may be edited>

Forbidden changes:
- <files, systems, or behaviors that must not change>

Deliverables:
- <expected code/docs/tests/output>

Default control clauses:
- No delegation or parallel workstreams unless explicitly allowed.
- Planning is internal only and must not expand scope.
- Disclose any hook, built-in skill, MCP tool, formatter, or runtime default that changed files or execution flow.
- Report any automatic formatting or lint fixes that changed additional lines.

Acceptance criteria:
- <observable conditions that define done>

Verification:
- <tests, commands, or checks to run if possible>

Failure report:
- If blocked, return:
  - blocker
  - attempted approach
  - exact missing input or permission
```

## Invocation

Invoke OpenCode with a non-interactive prompt and request structured output.

Base command:

```bash
opencode -p "<contract>" -f json -q -c "<workspace>"
```

If the task requires a narrower sandbox or a specific profile, include the relevant OpenCode flags supported in the current environment, but keep the contract unchanged.

## Oh My OpenCode Compatibility

If `oh-my-opencode` is installed, Codex must assume the OpenCode runtime may include:

- specialized default agents such as Sisyphus
- automatic subagent delegation
- project or user hooks
- built-in skills such as `git-master` or `playwright`
- project-local or user-level `oh-my-opencode` config overrides

Codex must preserve Party A authority under those conditions.

### Compatibility Rules

When `oh-my-opencode` is present:

1. Do not assume plain OpenCode defaults.
2. Read project-local behavior first, then user-wide behavior.
3. Treat `.opencode/oh-my-opencode.json` or `.jsonc` as higher priority than user config.
4. Assume hooks, agent defaults, and skill injections may alter execution style.
5. Narrow the contract so those runtime additions cannot broaden scope.

### Agent Control

`oh-my-opencode` may default to a planner-style agent such as Sisyphus, which is optimized to plan, delegate, and parallelize.

That is useful for complex work but dangerous for a contractor workflow unless Party A explicitly allows it.

Therefore, when `oh-my-opencode` is detected, Codex should state all of the following inside the contract:

- Re-state the default no-delegation and no-parallel-workstream clauses.
- Re-state that planning is internal only and may not expand the requested deliverables.
- Require Party B to prefer a single bounded implementation pass over exploratory orchestration.

If Party A wants `oh-my-opencode` to use its planner behavior, the contract must explicitly say so and must still bound write scope and deliverables.

### Hooks And Built-In Skills

`oh-my-opencode` may load hooks and built-in skills from OpenCode-compatible or Claude-compatible locations.

Codex must therefore assume:

- formatters or linters may run automatically after edits
- commit-related behavior may be modified by `git-master`
- browser or MCP tooling may be available even if not requested
- project-local automation may inject context or warnings

Codex should instruct Party B:

- do not invoke optional built-in skills unless they are necessary for the contract
- do not create commits, branches, or PRs unless explicitly allowed
- report any hook-triggered side effect that changes files or workflow
- report when automatic formatting or lint fixes changed additional lines

### Config Awareness

When `oh-my-opencode` is present, relevant config may live in:

- `.opencode/oh-my-opencode.json`
- `.opencode/oh-my-opencode.jsonc`

Codex should treat project config as authoritative for project behavior.

Inspect only project-local config by default.

If user-level config such as `~/.config/opencode/oh-my-opencode.json` or `.jsonc` may affect execution and must be checked, ask for explicit permission before reading outside the workspace.

If config inspection is needed, inspect read-only and capture only the settings that affect:

- agent selection
- hook behavior
- enabled or disabled skills
- MCP integrations
- write-affecting automation

## Required Response Shape

Codex must instruct OpenCode to return these fields in substance, even if the JSON schema is not enforced externally:

- `summary`: short description of completed work
- `files_changed`: list of edited files
- `tests_run`: commands run and outcomes
- `acceptance_status`: `done`, `partial`, or `blocked`
- `blockers`: unresolved issues
- `risks`: follow-up concerns or edge cases

If OpenCode returns a free-form answer, Codex must normalize it into those fields before deciding next steps.

## Acceptance Workflow

After OpenCode responds, Codex must do all of the following:

1. Compare the result against the original contract, not against inferred intent.
2. Verify changed files stay inside the allowed write scope.
3. Check whether forbidden changes occurred.
4. Review tests or verification claims.
5. Decide one of:
   - Accept
   - Reject and resend a narrower contract
   - Ask OpenCode for one targeted follow-up

Codex should reject the result if:

- Scope expanded without permission.
- Acceptance criteria were only partially met.
- Claimed verification is missing or inconsistent.
- OpenCode changed files outside the contract.
- The answer hides uncertainty or blockers.
- `oh-my-opencode` hooks or subagents changed behavior without being reported.

## Rework Rule

When rejecting, Codex must not resend the same vague request.

Codex must produce a tighter follow-up contract that states:

- what was not accepted
- what remains to be done
- which previous changes should be preserved
- any newly discovered constraints

## Audit Mode

If the OpenCode result is suspicious, incomplete, or needs traceability, Codex may inspect OpenCode session history in read-only mode.

Possible audit sources:

- project-local `.opencode/opencode.db`
- project-local `.opencode/oh-my-opencode.json` or `.jsonc`

Inspect only project-local audit data by default.

If user-level audit data such as `~/.opencode/opencode.db` or `~/.config/opencode/oh-my-opencode.json` may be necessary, request explicit user permission before reading it.

Audit goals:

- confirm the actual task sent
- inspect whether OpenCode reported blockers earlier
- verify whether the final answer matches execution history

Never mutate audit data as part of this skill.

## MCP Bridge Mode

If an MCP bridge is available between Codex and OpenCode, Codex may use it for:

- status checks
- tool mediation
- permission-aware delegation
- progress collection

Even with MCP, the contract-first rule still applies.

## Default Behavioral Rules

Codex should always:

- keep Party A authority explicit
- delegate only bounded tasks
- preserve a written acceptance standard
- treat OpenCode output as contractor output subject to review

OpenCode should always be instructed to:

- execute only within scope
- report blockers early
- avoid speculative refactors
- avoid hidden assumptions
- prefer minimal, reviewable changes
- avoid delegation or parallel workstreams unless explicitly authorized
- disclose hooks, built-in skills, MCP tools, or runtime defaults that affected files or execution flow

When `oh-my-opencode` is detected, OpenCode should additionally be instructed to:

- disclose whether a specialized agent handled the task
- disclose whether subagents were spawned
- disclose whether hooks modified files or execution flow
- disclose whether built-in skills or MCP tools were invoked because of runtime defaults

## Example Prompt

```text
You are Party B executing a contracted task for Party A.

Return a concise JSON-shaped response with:
- summary
- files_changed
- tests_run
- acceptance_status
- blockers
- risks

Do not expand scope. Do not modify files outside the allowed write scope.
Do not delegate to subagents unless the contract explicitly permits delegation.
Do not create parallel workstreams unless the contract explicitly permits them.
If hooks, built-in skills, MCP tools, formatters, or runtime defaults affect execution, report that explicitly.

Party A Contract for Party B

Objective:
- Add a repository-local skill that lets Codex delegate bounded implementation tasks to OpenCode.

Workspace:
- /absolute/workspace/path

Allowed write scope:
- .agents/skills/codex-opencode-client/SKILL.md

Forbidden changes:
- Any other files

Deliverables:
- A complete SKILL.md defining the client-contractor workflow

Acceptance criteria:
- The skill defines contract format, invocation pattern, acceptance flow, and rework rules

Verification:
- Confirm the file exists and matches the requested workflow

Failure report:
- If blocked, return blocker, attempted approach, and exact missing input
```

## Expected Outcome

This skill creates a stable collaboration pattern:

- Codex manages the project as the client
- OpenCode performs delegated work as the contractor
- acceptance remains with Codex
- the workflow is auditable and repeatable
