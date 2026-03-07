#!/usr/bin/env bash
set -euo pipefail

# Download a Bilibili video AND its cover image into a directory.
#
# Output filenames:
#   <title> [<BV>].mp4
#   <title> [<BV>].jpg   (or .png/.webp depending on cover url)
#
# Requirements:
# - yt-dlp in PATH OR set YTDLP to the yt-dlp binary path
# - python3 with requests installed (system python is fine on Raspberry Pi OS)
#
# Optional:
# - Set BILI_COOKIE env var for logged-in access (higher quality / restricted content)

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <BV_or_URL> [out_dir]" >&2
  echo "Env:   BILI_OUT_DIR=./video (default if out_dir omitted)" >&2
  echo "Env:   BILI_COOKIE='SESSDATA=...; bili_jct=...;' (optional)" >&2
  echo "Env:   YTDLP=/path/to/yt-dlp (optional)" >&2
  echo "Env:   BILI_OVERWRITE_COVER=0|1 (optional, default 0)" >&2
  exit 2
fi

INPUT="$1"
OUT_DIR="${2:-${BILI_OUT_DIR:-./video}}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
FETCH_PY="${SCRIPT_DIR}/bili_fetch.py"
DOWNLOAD_SH="${SCRIPT_DIR}/bili_download.sh"

mkdir -p "$OUT_DIR"

# 1) Download video
YTDLP_BIN="${YTDLP:-yt-dlp}"
if ! command -v "$YTDLP_BIN" >/dev/null 2>&1; then
  die_msg="yt-dlp not found. Install it or set YTDLP to its path (e.g. export YTDLP=\"/path/to/yt-dlp\")."
  echo "[error] $die_msg" >&2
  exit 127
fi

YTDLP="$YTDLP_BIN" "$DOWNLOAD_SH" "$INPUT" "$OUT_DIR"

# 2) Compute base name: <title> [<BV>]
BASE_NAME=$(python3 "$FETCH_PY" "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["title"] + " [" + d["bvid"] + "]")')

# 3) Decide cover extension by asking fetcher to print pic url, then download
PIC_URL=$(python3 "$FETCH_PY" "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("pic") or "")')
if [[ -z "$PIC_URL" ]]; then
  echo "[warn] cover url missing; skip cover download" >&2
  exit 0
fi

# Normalize scheme for extension detection
PIC_URL_NORM="$PIC_URL"
PIC_URL_NORM="${PIC_URL_NORM#//}"
PIC_URL_NORM="https://${PIC_URL_NORM#https://}"
PIC_URL_NORM="https://${PIC_URL_NORM#http://}"

EXT="jpg"
FNAME="${PIC_URL_NORM%%\?*}"
if [[ "$FNAME" == *.* ]]; then
  EXT="${FNAME##*.}"
fi

COVER_OUT="${OUT_DIR}/${BASE_NAME}.${EXT}"
if [[ -f "$COVER_OUT" && "${BILI_OVERWRITE_COVER:-0}" != "1" ]]; then
  echo "[info] cover exists; skip (set BILI_OVERWRITE_COVER=1 to overwrite): $COVER_OUT" >&2
else
  python3 "$FETCH_PY" "$INPUT" --download-cover --cover-out "$COVER_OUT"
fi

echo "[ok] saved video + cover to: $OUT_DIR" >&2
echo "[ok] video: ${OUT_DIR}/${BASE_NAME}.mp4" >&2
echo "[ok] cover: $COVER_OUT" >&2
