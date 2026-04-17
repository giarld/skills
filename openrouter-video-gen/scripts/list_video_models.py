#!/usr/bin/env python3
"""List OpenRouter video generation models."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


API_URL = "https://openrouter.ai/api/v1/videos/models"


def fetch_models(api_key: str | None) -> dict:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(API_URL, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def print_table(payload: dict) -> None:
    rows = payload.get("data", [])
    if not rows:
        print("No video models returned.")
        return

    print("MODEL\tRESOLUTIONS\tASPECT RATIOS")
    print("-" * 96)
    for row in rows:
        model_id = row.get("id", "")
        resolutions = ",".join(row.get("supported_resolutions", []))
        aspect_ratios = ",".join(row.get("supported_aspect_ratios", []))
        print(f"{model_id}\t{resolutions}\t{aspect_ratios}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List video generation models from OpenRouter."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw JSON response.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENROUTER_VIDEO_API_KEY"),
        help="OpenRouter video API key. Defaults to OPENROUTER_VIDEO_API_KEY.",
    )
    args = parser.parse_args()

    try:
        payload = fetch_models(args.api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print_table(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
