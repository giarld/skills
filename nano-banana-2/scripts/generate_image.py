#!/usr/bin/env python3
"""Generate or edit images via OpenRouter using openai-python.

- Supports prompt-only generation and edits with 1..N input images.
- Saves returned base64 images to disk and prints MEDIA: <path> lines.

Requires:
  pip install openai
  export OPENROUTER_API_KEY=...
"""

import argparse
import base64
import mimetypes
import os
from pathlib import Path

try:
    from openai import OpenAI
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "Missing dependency 'openai'. Install with: python3 -m pip install -U openai\n"
        f"Import error: {e}"
    )

# Tuneables
MAX_INPUT_IMAGES = 14
MODEL = "google/gemini-3.1-flash-image-preview"
MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
}


def parse_args():
    p = argparse.ArgumentParser(description="Generate or edit images via OpenRouter")
    p.add_argument("--prompt", required=True, help="What to generate or how to edit")
    p.add_argument("--filename", required=True, help="Output filename (relative or absolute)")
    p.add_argument(
        "--resolution",
        type=str.upper,
        choices=["1K", "2K", "4K"],
        default="1K",
        help="Output resolution: 1K/2K/4K (default: 1K)",
    )
    p.add_argument(
        "--input-image",
        action="append",
        default=[],
        help=f"Optional input image path (repeatable, max {MAX_INPUT_IMAGES})",
    )
    return p.parse_args()


def require_api_key() -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is not set in the environment.")
    return api_key


def load_system_prompt() -> str | None:
    base_dir = Path(__file__).parent.parent
    template_path = base_dir / "assets" / "SYSTEM_TEMPLATE"
    if template_path.exists():
        content = template_path.read_text(encoding="utf-8").strip()
        if content:
            return content
    return None


def encode_image_to_data_url(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"Input image not found: {path}")
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        mime = "image/png"
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def build_user_content(prompt: str, input_images: list[str]) -> list[dict]:
    content: list[dict] = [{"type": "text", "text": prompt}]
    for image_path in input_images:
        data_url = encode_image_to_data_url(Path(image_path))
        content.append({"type": "image_url", "image_url": {"url": data_url}})
    return content


def parse_data_url(data_url: str) -> tuple[str, bytes]:
    if not data_url.startswith("data:") or ";base64," not in data_url:
        raise SystemExit("Image payload is not a base64 data URL.")
    header, encoded = data_url.split(",", 1)
    mime = header[5:].split(";", 1)[0]
    try:
        raw = base64.b64decode(encoded)
    except Exception as e:
        raise SystemExit(f"Failed to decode base64 image payload: {e}")
    return mime, raw


def extract_image_url(image: object) -> str | None:
    # openai-python may return dicts or typed objects depending on version
    if isinstance(image, dict):
        return (image.get("image_url") or {}).get("url") or image.get("url")
    # fallback: attribute access
    try:
        image_url = getattr(image, "image_url", None)
        if image_url:
            return getattr(image_url, "url", None)
    except Exception:
        pass
    try:
        return getattr(image, "url", None)
    except Exception:
        return None


def resolve_output_path(filename: str, idx: int, total: int, mime: str) -> Path:
    out = Path(filename)
    expected = MIME_TO_EXT.get(mime, ".png")

    suffix = out.suffix
    if suffix and suffix.lower() != expected.lower():
        suffix = expected
    elif not suffix:
        suffix = expected

    if total <= 1:
        return out.with_suffix(suffix)

    return out.with_name(f"{out.stem}-{idx + 1}{suffix}")


def main():
    args = parse_args()

    if len(args.input_image) > MAX_INPUT_IMAGES:
        raise SystemExit(f"Too many input images: {len(args.input_image)} (max {MAX_INPUT_IMAGES}).")

    # OpenRouter image generation can be a bit slow; use a longer timeout.
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=require_api_key(),
        timeout=180.0,
    )

    messages: list[dict] = []

    system_prompt = load_system_prompt()
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": build_user_content(args.prompt, args.input_image)})

    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        extra_body={
            "modalities": ["image", "text"],
            "image_config": {
                "image_size": args.resolution,
            },
        },
    )

    msg = resp.choices[0].message
    images = getattr(msg, "images", None)
    if not images:
        raise SystemExit("No images returned by the API.")

    out_base = Path(args.filename)
    if out_base.parent and str(out_base.parent) != ".":
        out_base.parent.mkdir(parents=True, exist_ok=True)

    saved = []
    for idx, image in enumerate(images):
        url = extract_image_url(image)
        if not url:
            raise SystemExit("Image payload missing image_url.url.")
        mime, raw = parse_data_url(url)
        out_path = resolve_output_path(args.filename, idx, len(images), mime)
        out_path.write_bytes(raw)
        saved.append(out_path.resolve())

    for p in saved:
        print(f"Saved image to: {p}")
        print(f"MEDIA: {p}")


if __name__ == "__main__":
    main()
