#!/usr/bin/env python3
"""Fetch Bilibili metadata, hot replies, and cover.

Goals:
- Deterministic, cookie-optional fetch of: title, desc, aid, cid, cover URL.
- Optionally fetch hot replies (no login required in many cases).
- Download cover image with a filename matching the downloaded video.

This script intentionally avoids any paid/DRM bypass. It uses public web APIs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

UA = "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"


def die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def norm_bvid(s: str) -> str:
    s = s.strip()
    m = re.search(r"(BV[0-9A-Za-z]{10})", s)
    if not m:
        die(f"Could not find BV id in input: {s}")
    return m.group(1)


def http_get_json(url: str, *, params: Optional[dict] = None, headers: Optional[dict] = None, cookie: Optional[str] = None, timeout: int = 25) -> Dict[str, Any]:
    h = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.bilibili.com/",
    }
    if headers:
        h.update(headers)
    if cookie:
        h["Cookie"] = cookie
    r = requests.get(url, params=params, headers=h, timeout=timeout)
    r.raise_for_status()
    return r.json()


def fetch_view(bvid: str, *, cookie: Optional[str] = None) -> Dict[str, Any]:
    js = http_get_json("https://api.bilibili.com/x/web-interface/view", params={"bvid": bvid}, cookie=cookie)
    if js.get("code") != 0:
        die(f"view api failed: code={js.get('code')} msg={js.get('message')}")
    return js["data"]


def fetch_hot_replies(aid: int, *, ps: int = 20, cookie: Optional[str] = None) -> List[Dict[str, Any]]:
    # mode=3: hot; next=0: first page
    js = http_get_json(
        "https://api.bilibili.com/x/v2/reply/main",
        params={"type": 1, "oid": aid, "mode": 3, "next": 0, "ps": ps},
        headers={"Referer": f"https://www.bilibili.com/video/av{aid}"},
        cookie=cookie,
    )
    if js.get("code") != 0:
        # Not fatal; replies can be restricted.
        return []
    data = js.get("data") or {}
    return data.get("replies") or []


def download(url: str, out_path: Path, *, referer: str, cookie: Optional[str] = None, timeout: int = 40) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    h = {"User-Agent": UA, "Referer": referer}
    if cookie:
        h["Cookie"] = cookie
    with requests.get(url, headers=h, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="BV id or bilibili video URL")
    ap.add_argument("--cookie", default=os.environ.get("BILI_COOKIE"), help="Optional bilibili Cookie header (or set env BILI_COOKIE)")
    ap.add_argument("--out-json", help="Write fetched metadata JSON to path")
    ap.add_argument("--hot", action="store_true", help="Also fetch hot replies")
    ap.add_argument("--hot-ps", type=int, default=20, help="Hot replies page size")
    ap.add_argument("--download-cover", action="store_true", help="Download cover image")
    ap.add_argument("--cover-out", help="Cover output file path. If omitted, prints cover url.")

    args = ap.parse_args()
    bvid = norm_bvid(args.input)
    view = fetch_view(bvid, cookie=args.cookie)

    result: Dict[str, Any] = {
        "bvid": bvid,
        "aid": view.get("aid"),
        "cid": (view.get("pages") or [{}])[0].get("cid"),
        "title": view.get("title"),
        "desc": view.get("desc"),
        "pic": view.get("pic"),
        "pubdate": view.get("pubdate"),
        "owner": (view.get("owner") or {}),
        "stat": (view.get("stat") or {}),
    }

    if args.hot:
        replies = fetch_hot_replies(int(result["aid"]), ps=args.hot_ps, cookie=args.cookie)
        # keep a compact subset
        compact = []
        for r in replies:
            compact.append(
                {
                    "mid": (r.get("member") or {}).get("mid"),
                    "uname": (r.get("member") or {}).get("uname"),
                    "like": r.get("like"),
                    "message": ((r.get("content") or {}).get("message") or "").strip(),
                }
            )
        # Some videos return hot replies under data.hots (depending on backend).
        if not compact:
            try:
                js = http_get_json(
                    "https://api.bilibili.com/x/v2/reply/main",
                    params={"type": 1, "oid": int(result["aid"]), "mode": 3, "next": 0, "ps": args.hot_ps},
                    headers={"Referer": f"https://www.bilibili.com/video/{bvid}"},
                    cookie=args.cookie,
                )
                if js.get("code") == 0:
                    hots = (js.get("data") or {}).get("hots") or []
                    for r in hots:
                        compact.append(
                            {
                                "mid": (r.get("member") or {}).get("mid"),
                                "uname": (r.get("member") or {}).get("uname"),
                                "like": r.get("like"),
                                "message": ((r.get("content") or {}).get("message") or "").strip(),
                            }
                        )
            except Exception:
                pass
        result["hot_replies"] = compact

    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.download_cover:
        pic = result.get("pic")
        if not pic:
            die("No cover pic url found")
        if pic.startswith("//"):
            pic = "https:" + pic
        if pic.startswith("http://"):
            pic = "https://" + pic[len("http://") :]

        if args.cover_out:
            out_path = Path(args.cover_out)
        else:
            die("--download-cover requires --cover-out")
        download(pic, out_path, referer=f"https://www.bilibili.com/video/{bvid}", cookie=args.cookie)
    else:
        # default: print compact json to stdout
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
