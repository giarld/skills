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

## Repository Layout

```text
.
├── README.md
├── bilibili-video/
│   ├── SKILL.md
│   └── scripts/
└── remove-background/
    ├── SKILL.md
    └── remove_background.py
```

## Notes

- Each skill directory contains its own detailed `SKILL.md`.
- Follow local laws and platform terms when downloading online content.
