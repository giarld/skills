# Multica CLI Reference

Version note: this reference was refreshed against local Multica `v0.3.22` help output on 2026-06-16. Because CLI flags can drift between releases, prefer the installed CLI's `multica <command> --help` output over examples here.

Sources:

- Multica README: https://github.com/multica-ai/multica/blob/main/README.md
- Multica CLI docs: https://multica.ai/docs/cli
- CLI and daemon guide: https://github.com/multica-ai/multica/blob/main/CLI_AND_DAEMON.md
- CLI install guide: https://github.com/multica-ai/multica/blob/main/CLI_INSTALL.md

## Contents

- [What Multica CLI Does](#what-multica-cli-does)
- [Install And Update](#install-and-update)
- [Authentication](#authentication)
- [Setup, Daemon, And Runtime](#setup-daemon-and-runtime)
- [Workspaces](#workspaces)
- [Issues](#issues)
- [Projects](#projects)
- [Agents, Skills, Squads, And Autopilots](#agents-skills-squads-and-autopilots)
- [Labels, Attachments, User, And Miscellaneous](#labels-attachments-user-and-miscellaneous)
- [Version Drift Notes](#version-drift-notes)

## What Multica CLI Does

`multica` authenticates a local machine with Multica, manages workspace objects, and starts the local agent daemon. The daemon runs on the user's machine, detects supported AI CLIs on `PATH`, registers runtimes, polls for tasks, creates isolated workspace directories, spawns the selected agent CLI, and streams progress back to Multica.

Supported agent CLIs include `claude`, `codex`, `copilot`, `opencode`, `openclaw`, `hermes`, `gemini`, `pi`, `cursor-agent`, `kimi`, and `kiro-cli`. At least one must be installed and visible on `PATH` for useful daemon execution.

## Install And Update

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/multica-ai/multica/main/scripts/install.ps1 | iex
multica version
```

If PATH does not update immediately, restart the terminal. If execution policy blocks the install script:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

macOS/Linux with Homebrew:

```bash
brew install multica-ai/tap/multica
multica version
brew upgrade multica-ai/tap/multica
```

macOS/Linux install script:

```bash
curl -fsSL https://raw.githubusercontent.com/multica-ai/multica/main/scripts/install.sh | bash
multica version
```

Manual or script installs can usually update with:

```bash
multica update
```

Do not build from source unless the user explicitly asks and confirms. Source build requires the Multica checkout and project build tooling.

## Authentication

Browser login:

```bash
multica login
multica auth status
```

The browser flow opens the web app, creates a local PAT, and stores it in the Multica config. Tell the user to complete the browser login and return.

Headless login:

```bash
multica login --token
multica auth status
```

Use `--token` without a value so the CLI prompts for the token interactively. Avoid passing `--token mul_...` or `--token mcn_...` directly unless the user explicitly accepts command-history exposure.

Logout:

```bash
multica auth logout
```

Treat logout as destructive because it removes local authentication.

## Setup, Daemon, And Runtime

Cloud setup:

```bash
multica setup cloud
```

`multica setup` without a subcommand is currently equivalent to `multica setup cloud`, but prefer the explicit form in automation and docs.

Self-host setup:

```bash
multica setup self-host
multica setup self-host --server-url https://api.example.com --app-url https://app.example.com
```

Daemon:

```bash
multica daemon start
multica daemon start --foreground
multica daemon status
multica daemon status --output json
multica daemon logs
multica daemon logs -n 100
multica daemon logs -f
multica daemon stop
multica daemon restart
```

Runtime:

```bash
multica runtime list
multica runtime usage
multica runtime activity
multica runtime update <runtime-id> --target-version <version>
multica runtime update <runtime-id> --target-version <version> --wait
```

Useful daemon environment variables:

- `MULTICA_DAEMON_POLL_INTERVAL`
- `MULTICA_DAEMON_HEARTBEAT_INTERVAL`
- `MULTICA_AGENT_TIMEOUT`
- `MULTICA_CODEX_SEMANTIC_INACTIVITY_TIMEOUT`
- `MULTICA_DAEMON_MAX_CONCURRENT_TASKS`
- `MULTICA_DAEMON_ID`
- `MULTICA_DAEMON_DEVICE_NAME`
- `MULTICA_AGENT_RUNTIME_NAME`
- `MULTICA_WORKSPACES_ROOT`
- `MULTICA_GC_ENABLED`
- `MULTICA_GC_INTERVAL`
- `MULTICA_GC_TTL`
- `MULTICA_GC_ORPHAN_TTL`
- `MULTICA_GC_ARTIFACT_TTL`
- `MULTICA_GC_ARTIFACT_PATTERNS`

Agent-specific overrides follow the pattern `MULTICA_<AGENT>_PATH`, `MULTICA_<AGENT>_MODEL`, and sometimes `MULTICA_<AGENT>_ARGS`, for example `MULTICA_CODEX_PATH`, `MULTICA_CODEX_MODEL`, and `MULTICA_CODEX_ARGS`.

## Workspaces

Workspace resolution priority:

1. Command-level `--workspace-id`.
2. `MULTICA_WORKSPACE_ID`.
3. Default workspace stored in the current profile.

Common commands:

```bash
multica workspace list
multica workspace list --full-id
multica workspace list --output json
multica workspace get
multica workspace get <id-or-slug> --output json
multica workspace switch <id-or-slug>
multica workspace member list
multica workspace update <id-or-slug> --help
```

Prefer `workspace switch` for day-to-day default changes because it verifies access. `config set workspace_id` writes directly and skips the access check.

Profiles isolate tokens, config, daemon state, and workspace roots:

```bash
multica daemon start --profile staging
multica setup self-host --profile staging --server-url https://api-staging.example.com --app-url https://staging.example.com
```

## Issues

Typical list and get flow:

```bash
multica issue list
multica issue list --limit 20 --output json
multica issue list --status in_progress --priority urgent --assignee "Agent Name"
multica issue list --metadata pipeline_status=waiting_review
multica issue search "login error" --output json
multica issue get <issue-key-or-id> --output json
```

Create and update:

```bash
multica issue create --title "Fix login bug" --description "..." --priority high --assignee "Agent Name"
multica issue create --title "Import trace" --description-file ./issue.md --attachment ./trace.txt
multica issue create --title "Use uploaded artifact" --attachment-id <attachment-uuid>
multica issue update <issue-key-or-id> --title "New title" --priority urgent
```

On Windows, prefer `--description-file` for multi-line or non-ASCII issue descriptions. `--description-stdin` is also available, but file input is less likely to mangle bytes in PowerShell pipelines. Existing attachment UUIDs can be bound at creation time with repeated `--attachment-id`.

Assign and status syntax has changed across docs and versions. Always check local help:

```bash
multica issue assign --help
multica issue status --help
```

Known variants include assignment by name or ID and status values such as `backlog`, `todo`, `in_progress`, `in_review`, `done`, `blocked`, and `cancelled`.

Comments:

```bash
multica issue comment list <issue>
multica issue comment list <issue> --recent 20
multica issue comment list <issue> --thread <comment-id> --tail 30
multica issue comment add <issue> --content "Looks good"
multica issue comment add <issue> --content-file ./comment.md
multica issue comment add <issue> --parent <comment-id> --content "Reply text"
```

Use `--content-file` for multi-line or non-ASCII comment bodies, especially on Windows. `comment list` supports `--roots-only`, `--summary`, `--recent`, `--thread`, `--tail`, and cursor flags `--before/--before-id` for pagination.

Execution history:

```bash
multica issue runs <issue> --output json
multica issue run-messages <task-id> --issue <issue> --output json
multica issue run-messages <task-id> --since 42 --output json
multica issue cancel-task <task-id> --issue <issue> --output json
multica issue rerun <issue> --output json
multica issue pull-requests <issue> --output json
```

`cancel-task` accepts the short task ID prefix shown by `issue runs`; add `--issue` when short IDs are ambiguous.

Metadata:

```bash
multica issue metadata list <issue>
multica issue metadata get <issue> --key pipeline_status
multica issue metadata set <issue> --key pipeline_status --value waiting_review
multica issue metadata set <issue> --key code --value 42 --type string
multica issue metadata delete <issue> --key pipeline_status
```

Use metadata only for values that future runs need. Valid values are primitive strings, numbers, and booleans.

Subscribers:

```bash
multica issue subscriber list <issue>
multica issue subscriber add <issue>
multica issue subscriber add <issue> --user "Name"
multica issue subscriber remove <issue>
```

Labels:

```bash
multica label list --output json
multica label create --help
multica issue label list <issue> --output json
multica issue label add <issue> --help
multica issue label remove <issue> --help
```

## Projects

```bash
multica project list --output json
multica project get <project> --output json
multica project create --title "Sprint" --description "..." --lead "Agent Name"
multica project update <project> --status in_progress
multica project status <project> in_progress
multica project delete <project>
multica project resource list <project> --output json
multica project resource add <project> --type github_repo --url https://github.com/org/repo
```

Project statuses include `planned`, `in_progress`, `paused`, `completed`, and `cancelled`.

## Agents, Skills, Squads, And Autopilots

Agents:

```bash
multica agent list --output json
multica agent get <slug> --output json
multica agent create --help
multica agent update <slug> --help
multica agent archive <slug>
multica agent restore <slug>
multica agent avatar <slug-or-id> --file ./avatar.png
multica agent tasks <slug> --output json
multica agent skills --help
multica agent env get <agent> --output json
multica agent env set <agent> --help
```

`agent env get/set` is owner/admin-only and audited. Values equal to `****` preserve an existing entry when replacing the environment map.

Skills:

```bash
multica skill list --output json
multica skill get <id-or-slug> --output json
multica skill create --help
multica skill update --help
multica skill import --help
multica skill search "browser" --output json
multica skill files --help
multica skill delete <id-or-slug>
```

Squads:

```bash
multica squad list --output json
multica squad get <squad-id> --output json
multica squad create --name "Frontend" --leader <agent>
multica squad update <squad-id> --help
multica squad member list <squad-id>
multica squad member add <squad-id> --help
multica squad activity <issue-id> <action|no_action|failed> --reason "..."
```

Autopilots:

```bash
multica autopilot list --output json
multica autopilot get <id> --output json
multica autopilot create --help
multica autopilot update <id> --status paused
multica autopilot trigger <id>
multica autopilot runs <id> --limit 50 --output json
multica autopilot delete <id>
```

Cron schedule triggers are exposed through the CLI:

```bash
multica autopilot trigger-add <id> --cron "0 9 * * 1-5" --timezone "America/New_York"
multica autopilot trigger-update <trigger-id> --enabled=false
multica autopilot trigger-rotate-url <trigger-id>
multica autopilot trigger-delete <trigger-id>
```

## Labels, Attachments, User, And Miscellaneous

```bash
multica config show
multica config set server_url https://api.example.com
multica config set app_url https://app.example.com
multica version
multica update
multica repo checkout <url>
multica attachment download <id>
multica attachment download <id> --output-dir ./downloads
multica daemon disk-usage --output json
multica daemon disk-usage --by-workspace --top 20
multica user profile --help
```

## Version Drift Notes

The public CLI page is intentionally a top-level overview and says to run `multica <command> --help` for full usage. The README and CLI guide may show slightly different command forms depending on release timing. Prefer this order of authority:

1. The installed CLI's `--help` output.
2. The user's stated Multica version and deployment.
3. The current online docs.
4. The reference examples in this file.
