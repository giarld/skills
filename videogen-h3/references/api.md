# MiniMax H3 V2 API reference

Official sources: [create](https://platform.minimax.cn/docs/api-reference/video-generation-v2-create), [query](https://platform.minimax.cn/docs/api-reference/video-generation-v2-query), [regeneration](https://platform.minimax.cn/docs/api-reference/video-generation-v2-regeneration). Model options were checked on 2026-11-19. Before sending a live request, verify the configured provider supports the exact model ID, operation, and request fields.

## Endpoints and shared fields

Default base: `https://api.minimax.cn/v2`. `VIDEOGEN_H3_API_BASE_URL`, when set, overrides it without fallback. Supply the complete base, including the provider's required version prefix. The helper removes trailing `/` and appends the paths below. Only local loopback endpoints can use HTTP.

| Operation | Method and relative path |
| --- | --- |
| Create in the first three modes | POST `/video_generation` |
| Regenerate a video | POST `/video_regeneration` |
| Query any of these tasks | GET `/query/video_generation/{task_id}` |

Use Bearer authentication and JSON Content-Type. Creation returns `{"task_id":"..."}`; queries return `{"task":{"id":"...","status":"succeeded","content":{"url":"https://..."}}}`.

Generation requires `model`, `content`, `resolution`, and integer `duration`. Each generation request includes a nonempty `text` item, with at most 7,000 characters per text item.

| Model | Resolution | Integer seconds |
| --- | --- | --- |
| MiniMax-H3 | 768P / 2K | 4–15 |
| MiniMax-H3-Highspeed | 480P / 768P | 4–15 |
| MiniMax-H3-Lite | 480P / 768P | 4–15 |
| MiniMax-H3-Max | 480P / 768P | 5–15 |

These are official API limits, not a guarantee of access or support at a compatible endpoint. The helper only accepts these H3 model IDs. MiniMax describes Highspeed as balancing speed and quality, Lite as lightweight, and Max as focused on generation speed. Check provider-specific pricing and availability when they affect the choice.

Aspect ratios: `21:9`, `16:9`, `4:3`, `1:1`, `3:4`, `9:16`, and `adaptive`. Text-to-video requires an explicit non-adaptive ratio. Image-to-video uses `adaptive`, determined by the images. In reference mode, Lite requires an explicit non-adaptive ratio; the other models default to `adaptive` and also accept an explicit ratio.

Optional fields: `generate_audio` (boolean, default true), `aigc_watermark` (boolean, default false), and `callback_url`. Callback verification sends a challenge that the receiver must return unchanged within 3 seconds. Subsequent status callbacks match query responses. Use polling when callbacks are unnecessary.

Only Max supports `extra: {"prompt_expansion_mode":"balanced"}`. Allowed values are `disabled`, `balanced`, and `quality`; the default is `balanced`. Do not use `balance` or additional undeclared fields.

## Text-to-video

```json
{"model":"MiniMax-H3","content":[{"type":"text","text":"Sunrise at the beach, a slow camera push-in, with ocean waves and gentle music in sync."}],"resolution":"768P","duration":5,"ratio":"16:9"}
```

## Image-to-video

```json
{"model":"MiniMax-H3","content":[{"type":"text","text":"The camera moves smoothly forward, transitioning naturally from the first frame to the last."},{"type":"image_url","image_url":{"url":"https://example.com/first.png"},"role":"first_frame"},{"type":"image_url","image_url":{"url":"https://example.com/last.png"},"role":"last_frame"}],"resolution":"768P","duration":5,"ratio":"adaptive"}
```

You may supply only the first or last frame. A single image without a role defaults to the first frame. The official content-combination description permits last-frame-only input, but the role description says last frames must be paired with first frames. If the API rejects last-frame-only input, report the actual error and choose a paired-frame approach according to user intent.

## Multimodal reference-to-video

```json
{"model":"MiniMax-H3","content":[{"type":"text","text":"Preserve the character's appearance from the reference image and the camera motion from the reference video. Use audio 1 as the voice reference. The character says: Hello, world."},{"type":"image_url","image_url":{"url":"https://example.com/person.png"},"role":"reference_image"},{"type":"video_url","video_url":{"url":"https://example.com/motion.mp4"},"role":"reference_video"},{"type":"audio_url","audio_url":{"url":"https://example.com/voice.mp3"},"role":"reference_audio"}],"resolution":"768P","duration":5,"ratio":"16:9"}
```

Use reference images, videos, or audio individually or in combination; all three are not required. Explain each reference's purpose in the prompt. References are mutually exclusive with `first_frame` / `last_frame`.

### Media limits

Total JSON request size: at most 64 MB. Base64 adds approximately 33% overhead; use public URLs for large files. Media values are objects such as `{"url":"..."}`, not strings.

| Media | Specifications |
| --- | --- |
| Images | JPG/JPEG/PNG/WEBP/HEIC/HEIF; at most 30 MB each; width and height each 256–5760 px; width/height 0.4–2.5; at most 1 first frame, 1 last frame, and 9 reference images |
| Reference videos | MP4/MOV; H.264/AVC or H.265/HEVC; AAC/MP3 audio; at most 50 MB each; at most 3 clips, each 2–15 seconds, combined duration at most 15 seconds; dimensions and aspect ratio as for images; 23.976–60 fps |
| Reference audio | WAV/MP3; at most 15 MB each; at most 3 clips, each 2–15 seconds, combined duration at most 15 seconds |

URLs may be public addresses, `mm_file://{file_id}`, or data URIs such as `data:image/png;base64,...`, `data:video/mp4;base64,...`, and `data:audio/wav;base64,...`, with lowercase format names. `mm_file` refers to a platform file ID, not a local path. Verify custom endpoint compatibility.

## Video regeneration

Requires `model=MiniMax-H3` and `resolution=2K`. Supply exactly one of `source_task_id` or `content`. Do not send duration or ratio.

Task-ID mode requires an allowlisted account. The source task must belong to the current account, have succeeded within the last 7 days, and produce a video meeting H3 768P specifications.

```json
{"model":"MiniMax-H3","source_task_id":"SOURCE_TASK_ID","resolution":"2K"}
```

Source-video mode requires all content actually sent to the model for the original generation, unchanged: the final prompt and all images, reference videos, and audio. Add exactly one `base_video`. The prompt limit is 40,000 characters. Do not substitute the original prompt from before H3-Context-IR processing for the final prompt.

```json
{"model":"MiniMax-H3","content":[{"type":"text","text":"The exact final prompt used for the original 768P generation"},{"type":"video_url","video_url":{"url":"https://example.com/h3-768p.mp4"},"role":"base_video"}],"resolution":"2K"}
```

The source video must have an audio track, run at 24 fps, have width and height divisible by 32, cover 589824–1032192 pixels, and contain 107–362 frames in increments of 17 (107, 124, …, 362). This is not general processing of arbitrary uploaded videos. Reference media limits match generation. Setting `generate_audio: false` does not waive the audio track requirement in source-video mode. In task-ID mode a silent source task still yields silent output.

## Status and errors

`queued` / `running`: continue querying. `succeeded`: retrieve `task.content.url`. `failed`: read `task.error.code/message`. `cancelled`: stop. Queries cover 7 days; download links expire and can be refreshed by querying again.

HTTP errors: 400 invalid parameters, 401 authentication, 402 insufficient credits, 422 content validation, 429 rate limiting, and 500 server error. Error shape: `{"type":"error","error":{"type":"...","message":"...","http_code":"400"},"request_id":"..."}`. Preserve `request_id` for troubleshooting; do not automatically resend a create request when its submission outcome is uncertain.
