#!/usr/bin/env python3
"""Submit, poll, and download OpenRouter video generations."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


SUBMIT_URL = "https://openrouter.ai/api/v1/videos"


def build_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def request_json(url: str, method: str, headers: dict[str, str], payload: dict | None = None) -> dict:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=120) as response:
        charset = response.headers.get_content_charset("utf-8")
        return json.loads(response.read().decode(charset))


def download_file(url: str, api_key: str, target: Path) -> None:
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "*/*"}
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=300) as response:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)


def load_json_arg(inline_json: str | None, json_file: str | None) -> dict | None:
    if inline_json and json_file:
        raise ValueError("Use either --provider-json or --provider-json-file, not both.")
    if inline_json:
        return json.loads(inline_json)
    if json_file:
        return json.loads(Path(json_file).read_text(encoding="utf-8"))
    return None


def append_image(items: list[dict], url: str | None, frame_type: str | None = None) -> None:
    if not url:
        return
    item = {
        "type": "image_url",
        "image_url": {
            "url": url,
        },
    }
    if frame_type:
        item["frame_type"] = frame_type
    items.append(item)


def build_payload(args: argparse.Namespace) -> dict:
    payload: dict[str, object] = {
        "model": args.model,
        "prompt": args.prompt,
    }

    for key in ("duration", "resolution", "aspect_ratio", "size", "seed"):
        value = getattr(args, key)
        if value is not None:
            payload[key] = value

    if args.generate_audio is not None:
        payload["generate_audio"] = args.generate_audio

    frame_images: list[dict] = []
    append_image(frame_images, args.first_frame_url, "first_frame")
    append_image(frame_images, args.last_frame_url, "last_frame")
    if frame_images:
        payload["frame_images"] = frame_images

    input_references: list[dict] = []
    for url in args.reference_url:
        append_image(input_references, url)
    if input_references:
        payload["input_references"] = input_references

    provider = load_json_arg(args.provider_json, args.provider_json_file)
    if provider is not None:
        payload["provider"] = provider

    return payload


def derive_output_path(filename: str, index: int, multiple: bool) -> Path:
    target = Path(filename)
    if not multiple:
        return target
    return target.with_name(f"{target.stem}-{index}{target.suffix or '.mp4'}")


def print_status(prefix: str, payload: dict) -> None:
    status = payload.get("status", "unknown")
    job_id = payload.get("id", "")
    print(f"{prefix}: job={job_id} status={status}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate videos with OpenRouter's async video API."
    )
    parser.add_argument("--model", required=True, help="Model slug, for example google/veo-3.1.")
    parser.add_argument("--prompt", required=True, help="Video prompt.")
    parser.add_argument("--filename", default="./output.mp4", help="Output filename.")
    parser.add_argument("--api-key", default=os.environ.get("OPENROUTER_VIDEO_API_KEY"))
    parser.add_argument("--duration", type=int, help="Duration in seconds.")
    parser.add_argument("--resolution", help="Resolution, for example 720p or 1080p.")
    parser.add_argument("--aspect-ratio", dest="aspect_ratio", help="Aspect ratio, for example 16:9.")
    parser.add_argument("--size", help="Exact dimensions like 1280x720.")
    parser.add_argument("--seed", type=int, help="Optional generation seed.")
    parser.add_argument(
        "--generate-audio",
        dest="generate_audio",
        action="store_true",
        default=None,
        help="Request audio generation.",
    )
    parser.add_argument(
        "--no-generate-audio",
        dest="generate_audio",
        action="store_false",
        help="Disable audio generation.",
    )
    parser.add_argument("--first-frame-url", help="URL for frame_images first_frame.")
    parser.add_argument("--last-frame-url", help="URL for frame_images last_frame.")
    parser.add_argument(
        "--reference-url",
        action="append",
        default=[],
        help="Repeatable reference image URL for input_references.",
    )
    parser.add_argument("--provider-json", help="Inline JSON for the provider object.")
    parser.add_argument("--provider-json-file", help="Path to a JSON file for the provider object.")
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds between polls. Default: 30.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Maximum seconds to wait for completion. Default: 1800.",
    )
    parser.add_argument(
        "--submit-only",
        action="store_true",
        help="Submit the job and exit without polling or downloading.",
    )
    parser.add_argument(
        "--status-json",
        help="Optional path to write the final poll response JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print("OPENROUTER_VIDEO_API_KEY is not set.", file=sys.stderr)
        return 1

    try:
        payload = build_payload(args)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    headers = build_headers(args.api_key)

    try:
        submit_response = request_json(SUBMIT_URL, "POST", headers, payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    print_status("submitted", submit_response)
    print(f"polling_url={submit_response.get('polling_url', '')}")

    if args.submit_only:
        return 0

    polling_url = submit_response.get("polling_url")
    if not polling_url:
        print("Submit response missing polling_url.", file=sys.stderr)
        return 1

    deadline = time.time() + args.timeout
    final_status = submit_response

    while time.time() < deadline:
        remaining = deadline - time.time()
        sleep_for = min(args.poll_interval, remaining)
        if sleep_for <= 0:
            break
        time.sleep(sleep_for)
        try:
            final_status = request_json(str(polling_url), "GET", headers)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"HTTP {exc.code}: {body}", file=sys.stderr)
            return 1
        except urllib.error.URLError as exc:
            print(f"Polling failed: {exc}", file=sys.stderr)
            return 1

        print_status("polled", final_status)
        state = final_status.get("status")
        if state == "completed":
            break
        if state == "failed":
            print(f"Generation failed: {final_status.get('error', 'Unknown error')}", file=sys.stderr)
            if args.status_json:
                Path(args.status_json).write_text(
                    json.dumps(final_status, indent=2, ensure_ascii=True),
                    encoding="utf-8",
                )
            return 1
    else:
        print("Timed out waiting for video generation.", file=sys.stderr)
        return 1

    if args.status_json:
        Path(args.status_json).write_text(
            json.dumps(final_status, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    unsigned_urls = final_status.get("unsigned_urls") or []
    if not isinstance(unsigned_urls, list) or not unsigned_urls:
        job_id = final_status.get("id")
        if not job_id:
            print("Completed response missing unsigned_urls and id.", file=sys.stderr)
            return 1
        unsigned_urls = [f"https://openrouter.ai/api/v1/videos/{urllib.parse.quote(str(job_id))}/content?index=0"]

    multiple = len(unsigned_urls) > 1
    for index, url in enumerate(unsigned_urls):
        target = derive_output_path(args.filename, index, multiple)
        download_file(str(url), args.api_key, target)
        print(f"SAVED: {target.resolve()}")

    usage = final_status.get("usage")
    if usage:
        print(json.dumps({"usage": usage}, ensure_ascii=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
