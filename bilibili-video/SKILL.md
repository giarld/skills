---
name: bilibili-video
description: "Fetch and process Bilibili videos by BV id or URL: download videos (yt-dlp), download cover images with matching filenames, and fetch structured metadata (title/desc/aid/cid) plus hot comments via Bilibili public APIs. Use when user asks to download a Bilibili video, save its cover, summarize based on metadata/comments, or build an automated workflow around bilibili.com videos."
metadata: {"clawdbot":{"emoji":"📺","requires":{"bins":["python3","yt-dlp"],"env":["BILI_OUT_DIR","YTDLP","BILI_OVERWRITE_COVER"],"primaryEnv":"BILI_COOKIE"}}}
---

# Bilibili video workflow

Use this skill to reliably handle Bilibili videos when HTML scraping is blocked or unstable.

## What this skill provides

- Deterministic metadata fetch via public API (`x/web-interface/view`)
- Optional hot comments fetch (`x/v2/reply/main`)
- Cover download with a filename matching the video file
- Video download via `yt-dlp` (cookie optional)

Bundled scripts (run them; no need to rewrite from scratch):
- `scripts/bili_fetch.py`
- `scripts/bili_download.sh`

## Safety / compliance

- Only download content the user has rights to download and will use for personal offline viewing.
- Do not bypass paywalls/DRM/restricted content.
- If login is needed, accept Cookie only from the user and load it from `BILI_COOKIE` env var (do not hardcode).

## Configuration (environment variables)

- `BILI_OUT_DIR` (default: `./video`) — default output directory if you omit the `out_dir` argument
- `YTDLP` (default: `yt-dlp`) — path to yt-dlp binary if it is not in `PATH`
- `BILI_COOKIE` (optional) — Bilibili Cookie string for logged-in access (higher qualities / restricted content)
- `BILI_OVERWRITE_COVER` (default: `0`) — set to `1` to overwrite existing cover file

## Quick start

### 1) Fetch metadata (title/desc/aid/cid)

```bash
python skills/bilibili-video/scripts/bili_fetch.py "https://www.bilibili.com/video/BVxxxx" | jq
```

### 2) Fetch metadata + hot comments

```bash
python skills/bilibili-video/scripts/bili_fetch.py BVxxxx --hot --hot-ps 20 --out-json /tmp/bv.json
cat /tmp/bv.json | jq
```

### 3) Download video + cover (recommended)

```bash
# optional defaults
export BILI_OUT_DIR="./video"
# export YTDLP="/path/to/yt-dlp"

skills/bilibili-video/scripts/bili_grab.sh "https://www.bilibili.com/video/BVxxxx/"
```

If login is required for best quality, set cookie:

```bash
export BILI_COOKIE='SESSDATA=...; bili_jct=...;'
skills/bilibili-video/scripts/bili_grab.sh BVxxxx
```

### 4) Download only cover image with matching filename

Use metadata API to get the cover URL, then save alongside the MP4 with the same base name.

Example (assumes your output filename uses `%(title)s [%(id)s]`):

```bash
BV=BVxxxx
OUTDIR=./video
TITLE_AND_ID=$(python3 skills/bilibili-video/scripts/bili_fetch.py "$BV" | jq -r '(.title + " [" + .bvid + "]")')
python3 skills/bilibili-video/scripts/bili_fetch.py "$BV" \
  --download-cover \
  --cover-out "$OUTDIR/${TITLE_AND_ID}.jpg"
```

## Notes / troubleshooting

- If subtitles are required: try the player API (`x/player/wbi/v2`) and check `data.subtitle.subtitles`. Many videos have no subtitles.
- If comments are empty/restricted, fall back to summary based on title+desc, and ask user for extra text (transcript/highlights).
- If `yt-dlp` fails due to quality restriction, request user-provided `BILI_COOKIE`.
