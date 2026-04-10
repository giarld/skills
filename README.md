# Skills

Reusable agent skills and helper scripts for common automation workflows.

## Included Skills

| Skill | Purpose | Entry Files |
| --- | --- | --- |
| `bilibili-video` | Fetch Bilibili metadata, hot comments, videos, and cover images | `bilibili-video/SKILL.md` |
| `codex-opencode-client` | Delegate bounded implementation work from Codex to OpenCode with a contract-first workflow | `codex-opencode-client/SKILL.md` |
| `make-pdf` | Generate a compileable LaTeX document and final PDF from mixed source materials | `make-pdf/SKILL.md` |
| `nano-banana-2` | Generate or edit images through OpenRouter using Gemini image preview | `nano-banana-2/SKILL.md` |
| `remove-background` | Remove image backgrounds for single images or whole directories | `remove-background/SKILL.md` |

## Skill Details

### `bilibili-video`

Fetch and process Bilibili videos by BV id or URL.

- Entry files:
  - `bilibili-video/SKILL.md`
  - `bilibili-video/scripts/bili_fetch.py`
  - `bilibili-video/scripts/bili_grab.sh`
  - `bilibili-video/scripts/bili_download.sh`
- Features:
  - fetch structured metadata through the public API
  - fetch hot comments
  - download videos with `yt-dlp`
  - download cover images with matching filenames
- Optional environment variables:
  - `BILI_OUT_DIR` default `./video`
  - `YTDLP` default `yt-dlp`
  - `BILI_COOKIE` for logged-in access when needed
  - `BILI_OVERWRITE_COVER` default `0`

Quick examples:

```bash
python3 bilibili-video/scripts/bili_fetch.py "https://www.bilibili.com/video/BVxxxx"
bilibili-video/scripts/bili_grab.sh "https://www.bilibili.com/video/BVxxxx/"
```

### `codex-opencode-client`

Define a contract-first delegation workflow between Codex and OpenCode.

- Entry files:
  - `codex-opencode-client/SKILL.md`
- Features:
  - scope a bounded task before delegation
  - standardize acceptance criteria and audit guidance
  - support plain OpenCode and `oh-my-opencode` runtimes

Typical use case:

```text
Use this skill when Codex should delegate a tightly scoped coding task to
OpenCode, while keeping final acceptance and review on the Codex side.
```

### `make-pdf`

Generate a professional LaTeX document and compile it into a final PDF.

- Entry files:
  - `make-pdf/SKILL.md`
  - `make-pdf/assets/document-template.tex`
- Features:
  - start from a reusable LaTeX template
  - support notes, reports, tutorials, explainers, and figure-rich documents
  - handle mixed source inputs such as outlines, transcripts, screenshots, and code
  - require final PDF compilation as part of delivery
- Preferred toolchain:
  - `latexmk -xelatex`
  - fallback to repeated `xelatex` runs if needed

Typical use case:

```text
Use this skill when source materials need to be turned into a complete,
compileable `.tex` file and a polished PDF.
```

### `nano-banana-2`

Generate or edit images through OpenRouter with Gemini image preview.

- Entry files:
  - `nano-banana-2/SKILL.md`
  - `nano-banana-2/scripts/generate_image.py`
  - `nano-banana-2/assets/SYSTEM_TEMPLATE`
- Features:
  - prompt-only image generation
  - single-image editing
  - multi-image composition with up to 14 inputs
  - saves local output files and prints `MEDIA: <path>`
- Required environment variables:
  - `OPENROUTER_API_KEY`

Quick examples:

```bash
python3 nano-banana-2/scripts/generate_image.py \
  --prompt "A cinematic banana-shaped spaceship landing in a desert" \
  --filename ./images/banana-ship.png

python3 nano-banana-2/scripts/generate_image.py \
  --prompt "Add a rainbow in the sky, keep everything else unchanged" \
  --input-image ./input.jpg \
  --filename ./images/edit.png
```

Dependencies:

```bash
python3 -m pip install -U openai
```

### `remove-background`

Remove image backgrounds for a single file or an entire directory.

- Entry files:
  - `remove-background/SKILL.md`
  - `remove-background/remove_background.py`
- Supports:
  - `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`, `.tif`, `.tiff`
- Output:
  - transparent PNG files for single-file and batch workflows

Quick examples:

```bash
python3 remove-background/remove_background.py "input.jpg" "output.png"
python3 remove-background/remove_background.py "input_dir" "output_dir"
python3 remove-background/remove_background.py "input_dir" "output_dir" --recursive
```

Dependencies:

```bash
python3 -m pip install rembg Pillow
```

## Repository Layout

```text
.
├── README.md
├── bilibili-video/
│   ├── SKILL.md
│   └── scripts/
├── codex-opencode-client/
│   └── SKILL.md
├── make-pdf/
│   ├── SKILL.md
│   └── assets/
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
- Prefer using the bundled scripts and templates instead of re-implementing the workflow from scratch.
- Follow applicable laws, licenses, and platform terms when downloading or transforming third-party content.
