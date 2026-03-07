---
name: remove-background
description: Uses remove_background.py to remove image backgrounds in batch-safe, parameterized workflows.
---

# Remove Background Skill

This skill uses the bundled `remove_background.py` script to quickly remove image backgrounds. It supports both single-image processing and batch directory processing, and is suitable for automation workflows.

## Skill Package Contents

- `SKILL.md`
- `remove_background.py`

## When to Use

Use this skill when the user needs to:

- Remove image backgrounds and export transparent images (usually PNG)
- Integrate background removal into an existing Python/CLI workflow
- Use explicit input/output paths with clear error messages on failure

## Dependencies and Prerequisites

Make sure the runtime environment has:

- Python 3.8+
- `remove_background.py` in this skill directory
- Python packages: `rembg`, `Pillow`

Install with:

```bash
pip install rembg Pillow
```

## Script Interface

Target script: `remove_background.py` (in the same directory as `SKILL.md`)

- Positional arg 1: `input_path` (input image path or input directory path)
- Positional arg 2: `output_path` (output image path or output directory path)
- Optional arg: `--recursive` (when input is a directory, process subdirectories recursively and preserve structure)

Usage:

```bash
python ./remove_background.py "input.jpg" "output.png"
python ./remove_background.py "input_dir" "output_dir"
python ./remove_background.py "input_dir" "output_dir" --recursive
```

Behavior notes:

- Automatically strips surrounding quotes from incoming paths
- Single-image mode: reports an error if the input file does not exist
- Directory mode: reports an error if the input directory does not exist; creates output directory automatically
- Directory mode supports: `.jpg/.jpeg/.png/.bmp/.webp/.tif/.tiff`
- On single-image success, prints: "Background removed successfully and saved to: ..."
- On batch completion, prints totals: "Total X, Success Y, Failed Z"
- On exceptions, prints: "Error processing image: ..."

## Standard Workflow

1. Determine whether the input is a file or directory
2. Validate that the input path exists
3. Generate output path(s) (default export format is PNG)
4. Run the script command
5. Check results (single output file or batch summary)
6. Report results to the user (success path or failure reason)

## Reusable Command Templates

Single image:

```bash
python ./remove_background.py "{input_path}" "{output_path}"
```

Directory batch (current directory only):

```bash
python ./remove_background.py "{input_dir}" "{output_dir}"
```

Directory batch (recursive, preserve structure):

```bash
python ./remove_background.py "{input_dir}" "{output_dir}" --recursive
```

Windows batch loop (use only when you need a custom flow):

```bash
for %f in ("*.jpg") do python .\remove_background.py "%f" "%~nf_no_bg.png"
```

## Interaction and Decision Rules

- If the user does not specify an output filename for single-image mode, default to the input base name with `_no_bg.png`
- In directory mode, output filenames follow `original_filename_no_bg.png`
- If the output directory does not exist, create it automatically
- If the user requests overwriting existing files, clearly warn that files will be overwritten, then proceed
- If the user does not specify a format, default to PNG (with transparency)
- If the user requests recursive directory processing, add `--recursive`

## Troubleshooting

Common issues and suggested fixes:

- Invalid input path: verify absolute path, spaces, and quoting
- Missing dependencies: reinstall `rembg` and `Pillow`
- Model/runtime errors: install `onnxruntime` and retry
- Output not writable: check directory permissions or use a writable path
- No files processed in batch: confirm there are supported image files in the directory

## Response Format

When responding to the user, include:

- The actual command executed
- Input/output file paths
- Result status (success/failure)
- Actionable next steps if it failed
