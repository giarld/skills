---
name: multica-cli
description: Interact with the Multica CLI and local agent daemon. Use when an AI agent, assistant, or automation workflow needs to install or verify Multica, log in, manage profiles/workspaces, issues, labels, projects, agents, skills, squads, autopilots, runtimes, attachments, repositories, user profile, or daemon status/logs/disk usage through the `multica` command.
---

# Multica CLI

Use this skill to operate Multica from the local `multica` CLI. Multica connects this machine to a Multica workspace and authenticates with a local PAT. It runs a daemon that executes AI agent tasks locally through installed CLIs such as `codex`, `claude`, `opencode`, `hermes`, `gemini`, and others.

## Core Workflow

1. Check the installed CLI before assuming syntax:
   - `multica version`
   - `multica --help`
   - `multica <command> --help`
2. If the command is missing, read `references/cli.md` and follow the install flow for the current OS. On Windows, use PowerShell.
3. Verify authentication and target workspace before state-changing commands:
   - `multica auth status`
   - `multica workspace list`
   - `multica workspace get`
4. Prefer `--output json` for parsing, scripting, and summaries. Use table output when the user just wants a readable view.
5. Prefer names/slugs for interactive work, but use canonical IDs from `--output json` or `--full-id` for automation when names might collide.
6. For installed-version differences, trust local `--help` over cached docs or examples.
7. Treat PowerShell examples as Windows-oriented; translate quoting and line continuation for Bash or other shells when needed.

## Safety Rules

- Never paste or persist PATs, daemon tokens, API keys, or secrets into files, shell history, comments, issue metadata, or logs.
- For headless token login, prefer `multica login --token` so the CLI prompts interactively instead of putting the token in the command line.
- Before destructive or broad-impact operations, confirm intent with the user: `auth logout`, `daemon stop`, `daemon restart`, `update`, `delete`, `archive`, `restore`, changing workspace defaults, assigning/rerunning/canceling issue tasks, triggering autopilots, rotating webhook URLs, updating runtime versions, or replacing audited agent environment variables.
- Before starting a daemon or setup flow that opens a browser, tell the user that authentication may require browser interaction.
- When tailing logs, use bounded output first, such as `multica daemon logs -n 100`; use `-f` only when live monitoring is requested.
- Do not build Multica from source unless the user explicitly asks and confirms.

## Setup And Health

Fast path for Multica Cloud:

```powershell
multica setup cloud
multica auth status
multica daemon status --output json
```

Step-by-step flow:

```powershell
multica login
multica auth status
multica daemon start
multica daemon status --output json
```

Self-hosted flow:

```powershell
multica setup self-host
multica auth status
multica daemon status --output json
```

Manual self-host configuration:

```powershell
multica config set server_url http://localhost:8080
multica config set app_url http://localhost:3000
multica login
multica daemon start
```

Daemon diagnostics:

```powershell
multica daemon status --output json
multica daemon logs -n 100
multica runtime list --output json
```

## Task Routing

Use this decision guide:

- Workspace or member questions: `workspace list`, `workspace get`, `workspace switch`, `workspace update`, `workspace member list`.
- Issue triage and assignment: `issue list/search/get/create/update/assign/status`, `issue label ...`, top-level `label ...`.
- Agent execution tracking: `issue runs`, `issue run-messages`, `issue rerun`, `issue cancel-task`, `agent tasks`, daemon logs.
- Pull requests, comments, and collaboration: `issue pull-requests`, `issue comment list/add/delete`, `issue subscriber ...`.
- Project planning and resources: `project list/get/create/update/delete/status`, `project resource ...`.
- Agent configuration: `agent list/get/create/update/archive/restore/avatar`, `agent skills ...`, `agent env ...`.
- Skill management in Multica: `skill list/search/get/create/update/delete/import/files ...`.
- Squad routing: `squad list/get/create/update/delete`, `squad member ...`, `squad activity ...`.
- Recurring automation: `autopilot list/get/create/update/delete/runs/trigger`, `autopilot trigger-add/update/delete/rotate-url`.
- Runtime management: `daemon status/logs/start/stop/restart/disk-usage`, `runtime list/usage/activity/update`.
- Repository and attachments: `repo checkout <url>`, `attachment download <id>`.
- User account: `user profile`.

## Common Commands

Inspect workspace context:

```powershell
multica workspace list --output json
multica workspace get --output json
multica workspace member list --output json
multica agent list --output json
```

List and inspect issues:

```powershell
multica issue list --limit 20 --output json
multica issue list --status in_progress --output json
multica issue get MUL-123 --output json
```

Create or assign an issue after checking `multica issue create --help` and `multica issue assign --help`:

```powershell
multica issue create --title "Fix login bug" --description "Steps and expected behavior..." --priority high
multica issue create --title "Import logs" --description-file .\issue.md --attachment .\trace.txt
multica issue create --title "Follow up" --attachment-id <attachment-uuid>
multica issue assign MUL-123 --to "Agent Name"
multica issue assign MUL-123 --to-id <assignee-uuid>
```

On Windows, prefer `--description-file` for multi-line or non-ASCII issue bodies and `--content-file` for multi-line comments. Use UTF-8 text files.

Read comments without flooding context:

```powershell
multica issue comment list MUL-123 --recent 20
multica issue comment list MUL-123 --roots-only --summary
multica issue comment list MUL-123 --thread <comment-id> --tail 30
multica issue comment add MUL-123 --content-file .\comment.md
```

Track an agent run:

```powershell
multica issue runs MUL-123 --output json
multica issue run-messages <task-id> --issue MUL-123 --output json
multica issue run-messages <task-id> --since 42 --output json
multica issue cancel-task <task-id> --issue MUL-123 --output json
multica issue rerun MUL-123 --output json
```

Manage metadata sparingly:

```powershell
multica issue metadata list MUL-123
multica issue metadata set MUL-123 --key pr_url --value "https://github.com/org/repo/pull/123"
multica issue metadata set MUL-123 --key code --value 42 --type string
multica issue metadata get MUL-123 --key pr_url
```

Only write metadata that future Multica runs are likely to need, such as PR URLs, deploy URLs, blocked-on state, or pipeline state. Do not store secrets, logs, copied descriptions, large notes, or one-run scratch data.

## References

Read `references/cli.md` when installing, troubleshooting setup, choosing a command family, or checking command examples and known version-drift notes.
