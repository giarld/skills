#!/usr/bin/env bash
set -euo pipefail

# Download a bilibili video using yt-dlp.
# - Requires: yt-dlp in PATH (recommended) OR set YTDLP to a yt-dlp binary path
# - Optional: BILI_COOKIE env var for logged-in access (higher qualities / restricted videos)

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <BV_or_URL> <out_dir>" >&2
  exit 2
fi

INPUT="$1"
OUT_DIR="$2"

mkdir -p "$OUT_DIR"

COOKIE_ARGS=()
if [[ -n "${BILI_COOKIE:-}" ]]; then
  COOKIE_ARGS=(--add-header "Cookie: ${BILI_COOKIE}")
fi

${YTDLP:-yt-dlp} \
  --no-playlist \
  -o "${OUT_DIR}/%(title)s [%(id)s].%(ext)s" \
  "${COOKIE_ARGS[@]}" \
  "$INPUT"
