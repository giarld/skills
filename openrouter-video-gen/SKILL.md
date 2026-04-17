---
name: openrouter-video-gen
description: Generate videos through OpenRouter's asynchronous video API, including text-to-video, image-to-video (`frame_images`), reference-to-video (`input_references`), model discovery, polling, and download workflows. Use when Codex needs to create a video from a prompt or reference images via OpenRouter, inspect available video models, or automate end-to-end video generation with `OPENROUTER_VIDEO_API_KEY`.
---

# OpenRouter video generation

Use this skill when the task is to generate video via OpenRouter's dedicated video API rather than an image or text endpoint.

## What this skill provides

- `scripts/list_video_models.py` to inspect the current video-capable model catalog
- `scripts/generate_video.py` to submit, poll, and download generated video files
- `references/openrouter-video-generation.md` with the request model and async workflow distilled from the OpenRouter docs

Prefer the bundled scripts over handwritten `curl` loops.

## One-time setup

Ensure `OPENROUTER_VIDEO_API_KEY` is set in the environment.

The scripts use Python's standard library only, so no extra package install is required.

## Model discovery

List current video models:

```bash
python openrouter-video-gen/scripts/list_video_models.py
```

Get raw JSON:

```bash
python openrouter-video-gen/scripts/list_video_models.py --json
```

## Text-to-video

```bash
python openrouter-video-gen/scripts/generate_video.py \
  --model google/veo-3.1 \
  --prompt "A cinematic aerial shot of mist rolling through steep green mountains at sunrise" \
  --resolution 720p \
  --aspect-ratio 16:9 \
  --filename ./outputs/mountains.mp4
```

## Image-to-video

Use `frame_images` when the image should act as the first or last frame:

```bash
python openrouter-video-gen/scripts/generate_video.py \
  --model alibaba/wan-2.7 \
  --prompt "The camera slowly pushes in as the character steps into the forest" \
  --first-frame-url https://example.com/first-frame.png \
  --resolution 1080p \
  --filename ./outputs/forest.mp4
```

## Reference-to-video

Use `input_references` when the images are visual guidance rather than exact frames:

```bash
python openrouter-video-gen/scripts/generate_video.py \
  --model alibaba/wan-2.7 \
  --prompt "A colossal solar flare arcs around a planet, realistic lighting, cinematic motion" \
  --reference-url https://example.com/style-ref.png \
  --resolution 1080p \
  --filename ./outputs/solar-flare.mp4
```

## Provider options

Pass provider-specific options as JSON:

```bash
python openrouter-video-gen/scripts/generate_video.py \
  --model google/veo-3.1 \
  --prompt "A flower blooming in time-lapse" \
  --provider-json '{"options":{"google-vertex":{"parameters":{"personGeneration":"allow","negativePrompt":"blurry, low quality"}}}}' \
  --filename ./outputs/flower.mp4
```

If the JSON is large, put it in a file and use `--provider-json-file`.

## Operational guidance

- Poll at a moderate interval. The OpenRouter docs recommend about 30 seconds between polls.
- Use `--submit-only` if the immediate requirement is to enqueue a job and capture the job id / polling URL.
- Keep prompts concrete: subject, motion, camera, lighting, composition.
- Prefer `resolution` plus `aspect-ratio`, or `size`, but not both unless you know the target model supports the combination.
- If both frame images and references are supplied, OpenRouter treats the request as image-to-video; avoid mixing modes unless that is intended.

## Troubleshooting

- `OPENROUTER_VIDEO_API_KEY is not set`: export the key before running.
- `HTTP 401` or `403`: verify the key and account credits.
- Long `pending` time: keep polling; video generation can take minutes.
- `failed` status: inspect the returned `error` field and confirm the selected model currently supports video output.
- If you need the exact supported resolutions / aspect ratios / passthrough parameters for a model, re-run `list_video_models.py` and inspect that model first.

## References

- OpenRouter video generation guide: [references/openrouter-video-generation.md](references/openrouter-video-generation.md)
