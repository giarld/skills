# OpenRouter video generation reference

Source:
- https://openrouter.ai/docs/guides/overview/multimodal/video-generation

## Workflow

OpenRouter video generation is asynchronous:

1. `POST /api/v1/videos`
2. Receive `id`, `polling_url`, and initial `status`
3. Poll `GET /api/v1/videos/{jobId}` until `status` becomes `completed` or `failed`
4. Download from `unsigned_urls[index]` or `GET /api/v1/videos/{jobId}/content?index=0`

## Discovery endpoints

- `GET /api/v1/videos/models`
- `GET /api/v1/models?output_modalities=video`

The dedicated video models endpoint returns per-model fields such as:

- `id`
- `canonical_slug`
- `supported_resolutions`
- `supported_aspect_ratios`
- `supported_sizes`
- `pricing_skus`
- `allowed_passthrough_parameters`

## Request body

Required:

- `model`
- `prompt`

Optional:

- `duration`
- `resolution`
- `aspect_ratio`
- `size`
- `frame_images`
- `input_references`
- `generate_audio`
- `seed`
- `provider`

## Image modes

`frame_images`:
- image-to-video mode
- each item needs `type: "image_url"`
- frame items can include `frame_type: "first_frame"` or `frame_type: "last_frame"`

`input_references`:
- reference-to-video mode
- images guide style/content instead of fixing exact frames

If both are present, `frame_images` takes precedence.

## Job statuses

- `pending`
- `in_progress`
- `completed`
- `failed`

## Practical notes

- OpenRouter recommends a polling interval around 30 seconds.
- Video generation is not eligible for Zero Data Retention because output must be retained briefly for retrieval.
- Higher resolutions take longer and generally cost more.
- Check the model catalog before sending provider-specific passthrough parameters.
