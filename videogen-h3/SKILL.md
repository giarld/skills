---
name: videogen-h3
description: Generate videos with the MiniMax H3 V2 API from text, first or last frames, or image, video, and audio references. Use for H3 generation, eligible 768P-to-2K regeneration, asynchronous task tracking, or downloading completed videos.
license: MIT
---

# VideoGen H3

Run [scripts/h3.py](scripts/h3.py) with Python 3.8 or later. It uses only the standard library. Run the examples from the skill directory, or pass the script's full path.

- Set `VIDEOGEN_H3_API_KEY` in the execution environment or its secret manager for live requests. Do not put the key in prompts, command arguments, or request files.
- `VIDEOGEN_H3_API_BASE_URL` defaults to `https://api.minimax.cn/v2`. A custom value must be the complete API base, including any required version prefix. Use HTTPS for remote endpoints. Confirm it implements MiniMax V2 Bearer authentication, the selected route, and the exact model ID. Do not infer capability from a model name or switch providers automatically.

## Choose the mode and model

Read [references/api.md](references/api.md) for the model limits, request examples, and input media requirements. Preserve an explicit user choice and check it against the required resolution, duration, inputs, and provider support. Use `MiniMax-H3` for direct 2K generation or eligible regeneration. Otherwise, choose among verified options based on the user's quality, speed, or cost priorities; do not assume a compatible endpoint supports every official variant. If the user has no preferences, use `MiniMax-H3`, `768P`, and 5 seconds, with `16:9` for text-only generation.

| Input and desired result | Mode |
| --- | --- |
| One text prompt | `create`, with an explicit ratio |
| First frame, last frame, or both | `create`, with `adaptive` ratio |
| Reference image, video, or audio | `create`, with reference roles; do not mix with frame inputs |
| Regenerate an eligible H3 768P output at 2K | `regenerate`, with an eligible task ID or the source video and its original final prompt and inputs |

Task-ID regeneration requires allowlist access. Source-video regeneration is not a general upscaler. Pass the actual reference media with their roles; use accessible URLs, documented platform file IDs, or data URIs. For large or private inputs, use a user-authorized location. The helper validates JSON structure and selected limits, but cannot verify remote media properties or account entitlements.

## Submit, track, and deliver

Write request files as UTF-8 JSON without a BOM. Validate a request locally before submitting when model options or media combinations are uncertain:

```bash
python scripts/h3.py create --json request.json --dry-run
python scripts/h3.py create --json request.json
python scripts/h3.py regenerate --json regen.json --dry-run
python scripts/h3.py regenerate --json regen.json
python scripts/h3.py wait --task-id TASK_ID --timeout 900 --interval 15
python scripts/h3.py download --task-id TASK_ID --output outputs/video.mp4
```

Dry runs need no key and make no network requests. Record the task ID and request file after submission. With no terminal result yet, use `query --task-id TASK_ID` or wait again on the same ID. A timed-out create or regenerate request may already have been accepted; inspect existing tasks before considering a new submission. The script never retries these POSTs.

Download only after `succeeded`; URLs can expire, so refresh them by querying the same task. Downloads do not send the API key to the CDN and will not overwrite an existing file. Inspect the saved video when possible and report its path, task ID, and actual output details. If it cannot be viewed or the task failed, report that status directly.
