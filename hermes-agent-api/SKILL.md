---
name: hermes-agent-api
description: Call a Hermes Agent API server over its OpenAI-compatible HTTP interface. Use when Codex needs to health-check a Hermes gateway, list models or capabilities, send prompts to `/v1/chat/completions` or `/v1/responses`, continue Hermes conversations with `conversation` or `previous_response_id`, or submit and poll long-running `/v1/runs` jobs on a remote or local Hermes backend.
---

# Hermes Agent API

## Core Workflow

1. Resolve the target server and credentials from the current task context first. Prefer transient session values, then `HERMES_BASE_URL`, `HERMES_API_KEY`, and `HERMES_MODEL`.
2. Never hard-code or persist API keys in the skill files, repo files, or shared logs.
3. When the server is uncertain, verify it with:
   - `python scripts/hermes_api.py health`
   - `python scripts/hermes_api.py models`
   - `python scripts/hermes_api.py capabilities`
4. Choose the endpoint by intent:
   - Use `chat` for OpenAI Chat Completions compatibility and explicit `messages`.
   - Use `response` for server-side continuity with `--conversation` or `--previous-response-id`.
   - Use `run` for long-running tasks that should be polled until completion.
5. Prefer the bundled script instead of rewriting `Invoke-RestMethod`, `curl`, or ad hoc Python in each task.

## Script

Use `scripts/hermes_api.py` from this skill directory. The script uses only the Python standard library.

PowerShell setup:

```powershell
$env:HERMES_BASE_URL = 'http://192.168.177.59:8642'
$env:HERMES_API_KEY = '<api-key>'
$env:HERMES_MODEL = 'hermes-agent'
```

Basic checks:

```powershell
python scripts/hermes_api.py health
python scripts/hermes_api.py models
python scripts/hermes_api.py capabilities
```

Send a one-shot prompt through Chat Completions:

```powershell
python scripts/hermes_api.py chat --prompt "Reply with exactly: pong"
python scripts/hermes_api.py chat --system "You are a concise coding assistant." --prompt "Summarize this folder."
```

Send a prompt through the Responses API:

```powershell
python scripts/hermes_api.py response --input "What files are in this project?"
python scripts/hermes_api.py response --input "Continue the diagnosis" --conversation "hermes-debug" --store
python scripts/hermes_api.py response --input "Now refine the answer" --previous-response-id "resp_abc123" --store
```

Run a long task and wait for completion:

```powershell
python scripts/hermes_api.py run --input "Inspect the repo and propose a refactor plan." --wait
python scripts/hermes_api.py run --input "Run the test suite and summarize failures." --session-id "ci-debug" --wait --raw
```

Advanced payload inputs:

```powershell
python scripts/hermes_api.py chat --messages-file .\messages.json --raw
python scripts/hermes_api.py response --input-json-file .\response_input.json --conversation "vision"
```

## Usage Rules

- Default to `response` when the user wants multi-turn continuity on the Hermes side.
- Default to `chat` when the caller already has a Chat Completions `messages` array or needs maximum OpenAI-client compatibility.
- Use `run` when the task is long-running, the caller wants polling, or the frontend is better modeled as a job.
- Use `--raw` for debugging response bodies, tool-call traces, or schema drift.
- If the user provides a specific base URL or key in the current conversation, use it transiently instead of editing environment files.
- If the user asks to inspect headers or stable server features, read `references/api.md` first, then verify with the live `capabilities` endpoint if possible.

## References

Read `references/api.md` when request bodies, response shapes, or endpoint selection details are needed.
