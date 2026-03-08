---
name: nano-banana-2
description: 'Generate or edit images via OpenRouter with Google Gemini 3.1 Flash Image Preview. Supports prompt-only generation, image edits, and multi-image input (up to 14). Saves outputs to files and prints MEDIA: <path>.'
metadata:
  emoji: 🍌
  requires:
    bins:
      - python3
    env:
      - OPENROUTER_API_KEY
  primaryEnv: OPENROUTER_API_KEY
allowed-tools: Bash(python3 *), Bash(pip *), Bash(python *), Bash(jq *), Bash(ls *), Bash(cat *)
---

# nano-banana-2 (OpenRouter edition)

## Overview

This skill generates / edits images via **OpenRouter** (OpenAI-compatible API) using:
- model: `google/gemini-3.1-flash-image-preview`

Compared to a raw `curl` example, this version is more reliable because it:
- sends multimodal messages (text + optional input images)
- parses the returned base64 `data:image/...` payloads
- writes output images to disk
- prints `MEDIA: <path>` lines (so other tools/agents can pick them up)

## One-time setup

Ensure `OPENROUTER_API_KEY` is set in the environment.

Install Python dependency (if missing):

```bash
python3 -m pip install -U openai
```

## Prompt-only generation

```bash
python3 {baseDir}/scripts/generate_image.py \
  --prompt "二次元风格日式JK女孩，清新明亮的校园背景，半身像，柔和光线，高细节" \
  --filename ./images/jk.png \
  --resolution 1K
```

## Edit an image

```bash
python3 {baseDir}/scripts/generate_image.py \
  --prompt "在天空中加一道彩虹，其他保持不变" \
  --input-image /path/to/input.jpg \
  --filename ./images/edit.png
```

## Multiple input images (composition)

```bash
python3 {baseDir}/scripts/generate_image.py \
  --prompt "把这些人物合成一张自然的合影，统一光线和色调" \
  --input-image a.png \
  --input-image b.png \
  --filename ~/images/composite.png
```

## System prompt customization

You can customize style/behavior by editing:
- `{baseDir}/assets/SYSTEM_TEMPLATE`

(Leave it empty to disable the system prompt.)

## Behavior & constraints

- Up to **14** input images via repeated `--input-image`.
- If multiple images are returned, the script writes `filename-1.png`, `filename-2.png`, ...
- The script prints `MEDIA: <absolute-path>` for each saved image.

## Troubleshooting

- `OPENROUTER_API_KEY is not set`: export it in the service/shell environment.
- Missing `openai` module: run `python3 -m pip install -U openai`.
- HTTP 401: key invalid / no credits.
- HTTP 429/timeouts: wait 30s and retry once (don’t loop forever).
