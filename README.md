# Skills

A small collection of reusable agent skills and helper scripts.

## Included Skills

### `remove-background`

Remove image backgrounds for a single file or an entire directory.

- Entry files:
  - `remove-background/SKILL.md`
  - `remove-background/remove_background.py`
- Supports: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`, `.tif`, `.tiff`
- Output: transparent PNG files (single mode or batch mode)

Quick examples:

```bash
python remove-background/remove_background.py "input.jpg" "output.png"
python remove-background/remove_background.py "input_dir" "output_dir"
python remove-background/remove_background.py "input_dir" "output_dir" --recursive
```

Dependencies:

```bash
pip install rembg Pillow
```

### `bilibili-video`

Fetch Bilibili metadata and download videos/covers using bundled scripts.

- Entry files:
  - `bilibili-video/SKILL.md`
  - `bilibili-video/scripts/bili_fetch.py`
  - `bilibili-video/scripts/bili_grab.sh`
  - `bilibili-video/scripts/bili_download.sh`
- Supports BV id or full Bilibili URL input
- Can fetch video metadata and hot comments
- Can download cover image with matching filename

Quick examples:

```bash
python bilibili-video/scripts/bili_fetch.py "https://www.bilibili.com/video/BVxxxx" 
bilibili-video/scripts/bili_grab.sh "https://www.bilibili.com/video/BVxxxx/"
```

Optional environment variables:

- `BILI_OUT_DIR` (default: `./video`)
- `YTDLP` (default: `yt-dlp`)
- `BILI_COOKIE` (optional, for logged-in access)
- `BILI_OVERWRITE_COVER` (default: `0`)

### `nano-banana-2`

Generate or edit images through OpenRouter with Gemini image preview.

- Entry files:
  - `nano-banana-2/SKILL.md`
  - `nano-banana-2/scripts/generate_image.py`
  - `nano-banana-2/assets/SYSTEM_TEMPLATE`
- Supports prompt-only generation, single-image edits, and multi-image composition
- Accepts up to 14 input images
- Output: saves image files locally and prints `MEDIA: <path>` for each result

Quick examples:

```bash
python3 nano-banana-2/scripts/generate_image.py --prompt "A cinematic banana-shaped spaceship landing in a desert" --filename ./images/banana-ship.png
python3 nano-banana-2/scripts/generate_image.py --prompt "Add a rainbow in the sky, keep everything else unchanged" --input-image ./input.jpg --filename ./images/edit.png
```

Dependencies:

```bash
python3 -m pip install -U openai
```

Required environment variables:

- `OPENROUTER_API_KEY`

## Repository Layout

```text
.
├── README.md
├── bilibili-video/
│   ├── SKILL.md
│   └── scripts/
├── nano-banana-2/
│   ├── SKILL.md
│   ├── assets/
│   └── scripts/
└── remove-background/
    ├── SKILL.md
    └── remove_background.py
```

## Notes

- Each skill directory contains its own detailed `SKILL.md`.
- Follow local laws and platform terms when downloading online content.
