#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_BASE_URL = "http://127.0.0.1:8642"
DEFAULT_MODEL = "hermes-agent"
TERMINAL_RUN_STATES = {"completed", "failed", "cancelled"}


def fail(message: str, exit_code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def read_json(path: str) -> Any:
    return json.loads(read_text(path))


def pretty_print(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def resolve_api_key(cli_value: str | None) -> str:
    api_key = cli_value or os.environ.get("HERMES_API_KEY")
    if not api_key:
        fail("Missing Hermes API key. Pass --api-key or set HERMES_API_KEY.")
    return api_key


def build_headers(args: argparse.Namespace, include_json: bool = False) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {resolve_api_key(args.api_key)}",
    }
    if include_json:
        headers["Content-Type"] = "application/json"
    if args.session_id:
        headers["X-Hermes-Session-Id"] = args.session_id
    if args.session_key:
        headers["X-Hermes-Session-Key"] = args.session_key
    return headers


def call_api(
    args: argparse.Namespace,
    method: str,
    path: str,
    body: Any | None = None,
) -> Any:
    base_url = (args.base_url or os.environ.get("HERMES_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    data = None
    headers = build_headers(args, include_json=body is not None)
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=args.timeout) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        fail(f"HTTP {exc.code} {exc.reason}\n{detail}")
    except error.URLError as exc:
        fail(f"Request failed: {exc}")

    if not raw.strip():
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def chat_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""


def response_text(payload: dict[str, Any]) -> str:
    output = payload.get("output") or []
    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "\n".join(parts)


def handle_health(args: argparse.Namespace) -> None:
    pretty_print(call_api(args, "GET", "/health"))


def handle_health_detailed(args: argparse.Namespace) -> None:
    pretty_print(call_api(args, "GET", "/health/detailed"))


def handle_models(args: argparse.Namespace) -> None:
    pretty_print(call_api(args, "GET", "/v1/models"))


def handle_capabilities(args: argparse.Namespace) -> None:
    pretty_print(call_api(args, "GET", "/v1/capabilities"))


def build_chat_messages(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.messages_file:
        messages = read_json(args.messages_file)
        if not isinstance(messages, list):
            fail("--messages-file must contain a JSON array.")
        return messages
    if not args.prompt:
        fail("chat requires --prompt or --messages-file.")
    messages: list[dict[str, Any]] = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": args.prompt})
    return messages


def handle_chat(args: argparse.Namespace) -> None:
    payload = {
        "model": args.model,
        "messages": build_chat_messages(args),
        "stream": False,
    }
    response = call_api(args, "POST", "/v1/chat/completions", payload)
    if args.raw:
        pretty_print(response)
        return
    print(chat_text(response))


def build_response_input(args: argparse.Namespace) -> Any:
    if args.input_json_file:
        return read_json(args.input_json_file)
    if args.input_file:
        return read_text(args.input_file)
    if args.input is None:
        fail("response requires --input, --input-file, or --input-json-file.")
    return args.input


def handle_response(args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {
        "model": args.model,
        "input": build_response_input(args),
        "store": args.store,
    }
    if args.instructions:
        payload["instructions"] = args.instructions
    if args.previous_response_id:
        payload["previous_response_id"] = args.previous_response_id
    if args.conversation:
        payload["conversation"] = args.conversation
    response = call_api(args, "POST", "/v1/responses", payload)
    if args.raw:
        pretty_print(response)
        return
    print(response_text(response))


def poll_run(args: argparse.Namespace, run_id: str) -> dict[str, Any]:
    deadline = time.time() + args.max_wait
    while True:
        payload = call_api(args, "GET", f"/v1/runs/{run_id}")
        status = payload.get("status")
        if status in TERMINAL_RUN_STATES:
            return payload
        if time.time() >= deadline:
            fail(f"Timed out waiting for run {run_id}. Last status: {status}")
        time.sleep(args.poll_interval)


def handle_run(args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {
        "model": args.model,
        "input": args.input,
    }
    if args.instructions:
        payload["instructions"] = args.instructions
    if args.previous_response_id:
        payload["previous_response_id"] = args.previous_response_id
    if args.session_id:
        payload["session_id"] = args.session_id
    if args.conversation_history_file:
        payload["conversation_history"] = read_json(args.conversation_history_file)

    started = call_api(args, "POST", "/v1/runs", payload)
    if not args.wait:
        pretty_print(started)
        return

    run_id = started.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        fail("Run submission did not return a run_id.")
    final = poll_run(args, run_id)
    if args.raw:
        pretty_print(final)
        return
    output = final.get("output")
    if isinstance(output, str) and output:
        print(output)
    else:
        pretty_print(final)


def handle_run_status(args: argparse.Namespace) -> None:
    pretty_print(call_api(args, "GET", f"/v1/runs/{args.run_id}"))


def handle_run_stop(args: argparse.Namespace) -> None:
    pretty_print(call_api(args, "POST", f"/v1/runs/{args.run_id}/stop", {}))


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", help="Hermes server base URL. Defaults to HERMES_BASE_URL or http://127.0.0.1:8642")
    parser.add_argument("--api-key", help="Hermes bearer token. Defaults to HERMES_API_KEY")
    parser.add_argument("--model", default=os.environ.get("HERMES_MODEL", DEFAULT_MODEL), help="Model id. Defaults to HERMES_MODEL or hermes-agent")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds")
    parser.add_argument("--session-id", help="Optional X-Hermes-Session-Id header value")
    parser.add_argument("--session-key", help="Optional X-Hermes-Session-Key header value")
    parser.add_argument("--raw", action="store_true", help="Print the full JSON response instead of extracted text")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call a Hermes Agent API server.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, handler in {
        "health": handle_health,
        "health-detailed": handle_health_detailed,
        "models": handle_models,
        "capabilities": handle_capabilities,
    }.items():
        subparser = subparsers.add_parser(name)
        add_common_arguments(subparser)
        subparser.set_defaults(handler=handler)

    chat = subparsers.add_parser("chat")
    add_common_arguments(chat)
    chat.add_argument("--prompt", help="User prompt text")
    chat.add_argument("--system", help="Optional system prompt")
    chat.add_argument("--messages-file", help="Path to a JSON file containing a Chat Completions messages array")
    chat.set_defaults(handler=handle_chat)

    response = subparsers.add_parser("response")
    add_common_arguments(response)
    response.add_argument("--input", help="Input text")
    response.add_argument("--input-file", help="Path to a UTF-8 text file used as input")
    response.add_argument("--input-json-file", help="Path to a JSON file used as the input field value")
    response.add_argument("--instructions", help="Optional Responses API instructions")
    response.add_argument("--store", action="store_true", help="Request server-side storage for follow-up turns")
    response.add_argument("--conversation", help="Named Hermes conversation")
    response.add_argument("--previous-response-id", help="Chain to an earlier stored response")
    response.set_defaults(handler=handle_response)

    run = subparsers.add_parser("run")
    add_common_arguments(run)
    run.add_argument("--input", required=True, help="Run input text")
    run.add_argument("--instructions", help="Optional run instructions")
    run.add_argument("--previous-response-id", help="Optional response chain to continue")
    run.add_argument("--conversation-history-file", help="JSON file for run conversation_history")
    run.add_argument("--wait", action="store_true", help="Poll the run until it reaches a terminal state")
    run.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval in seconds when --wait is set")
    run.add_argument("--max-wait", type=int, default=900, help="Maximum wait time in seconds when --wait is set")
    run.set_defaults(handler=handle_run)

    run_status = subparsers.add_parser("run-status")
    add_common_arguments(run_status)
    run_status.add_argument("--run-id", required=True, help="Hermes run id")
    run_status.set_defaults(handler=handle_run_status)

    run_stop = subparsers.add_parser("run-stop")
    add_common_arguments(run_stop)
    run_stop.add_argument("--run-id", required=True, help="Hermes run id")
    run_stop.set_defaults(handler=handle_run_stop)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
