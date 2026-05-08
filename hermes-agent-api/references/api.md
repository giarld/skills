# Hermes Agent API Notes

Use this file only when the bundled script or `SKILL.md` is not enough.

## Auth And Base URL

- Hermes expects bearer auth: `Authorization: Bearer <token>`.
- Use a base URL without a trailing slash, for example `http://192.168.177.59:8642`.
- Do not persist API keys in repo files. Prefer `HERMES_API_KEY` and `HERMES_BASE_URL`.

## Endpoint Selection

- `GET /health`
  - Fast reachability check.
  - Typical response: `{"status":"ok","platform":"hermes-agent"}`.
- `GET /v1/models`
  - Discover the advertised model id.
  - The validated server on 2026-05-08 returned `hermes-agent`.
- `GET /v1/capabilities`
  - Discover whether chat completions, responses, runs, run polling, run stop, and Hermes session headers are enabled.
- `POST /v1/chat/completions`
  - Use when the caller already has an OpenAI-style `messages` array.
  - Stateless. The client sends the full conversation every time.
- `POST /v1/responses`
  - Use when Hermes should keep server-side context.
  - Prefer `conversation` for named continuity or `previous_response_id` for explicit chaining.
  - Use `store: true` when a follow-up is likely.
- `POST /v1/runs`
  - Use for long-running agent work that should be tracked separately.
  - Poll with `GET /v1/runs/{run_id}` until `completed`, `failed`, or `cancelled`.
- `POST /v1/runs/{run_id}/stop`
  - Ask Hermes to interrupt a running turn.

## Minimal Request Shapes

Chat Completions:

```json
{
  "model": "hermes-agent",
  "messages": [
    {"role": "user", "content": "Reply with exactly: pong"}
  ],
  "stream": false
}
```

Responses API:

```json
{
  "model": "hermes-agent",
  "input": "Inspect this project",
  "instructions": "Be concise.",
  "store": true,
  "conversation": "project-a"
}
```

Runs API:

```json
{
  "model": "hermes-agent",
  "input": "Inspect the repo and summarize the build issues.",
  "session_id": "build-debug"
}
```

## Session Headers

If the Hermes server advertises them in `/v1/capabilities`, these headers may be used:

- `X-Hermes-Session-Id`
- `X-Hermes-Session-Key`

Use them only when the caller explicitly needs Hermes-side session routing or continuity.

## Practical Rules

- Trust the live `capabilities` endpoint over this note if they disagree.
- Prefer the bundled `scripts/hermes_api.py` over ad hoc HTTP snippets.
- Use `--raw` when integrating a new frontend or investigating schema drift.
