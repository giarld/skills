import argparse
from rembg import remove
from PIL import Image
import os

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def remove_image_background(input_path, output_path):
    """
    Remove image background and save as PNG.

    Args:
        input_path (str): Full path to the input image.
        output_path (str): Full path to the output image (including filename and extension, e.g. 'output.png').
    """
    try:
        input_path = input_path.strip('"')
        output_path = output_path.strip('"')
        # Ensure input file exists.
        if not os.path.exists(input_path):
            print(f"Error: Input file does not exist - {input_path}")
            return

        # Open image.
        input_image = Image.open(input_path)

        # Remove background.
        output_image = remove(input_image)

        # Save processed image.
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        if isinstance(output_image, bytes):
            with open(output_path, "wb") as f:
                f.write(output_image)
        elif isinstance(output_image, Image.Image):
            output_image.save(output_path)
        else:
            Image.fromarray(output_image).save(output_path)
        print(f"Background removed successfully and saved to: {output_path}")
        return True

    except Exception as e:
        print(f"Error processing image: {e}")
        return False


def is_supported_image(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower() in SUPPORTED_EXTENSIONS


def remove_background_from_directory(input_dir, output_dir, recursive=False):
    input_dir = input_dir.strip('"')
    output_dir = output_dir.strip('"')

    if not os.path.isdir(input_dir):
        print(f"Error: Input directory does not exist - {input_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)

    success_count = 0
    failed_count = 0
    total_count = 0

    for root, _, files in os.walk(input_dir):
        for filename in files:
            if not is_supported_image(filename):
                continue

            total_count += 1
            input_path = os.path.join(root, filename)

            if recursive:
                rel_dir = os.path.relpath(root, input_dir)
                target_dir = output_dir if rel_dir == "." else os.path.join(output_dir, rel_dir)
            else:
                target_dir = output_dir

            name_without_ext, _ = os.path.splitext(filename)
            output_path = os.path.join(target_dir, f"{name_without_ext}_no_bg.png")

            ok = remove_image_background(input_path, output_path)
            if ok:
                success_count += 1
            else:
                failed_count += 1

        if not recursive:
            break

    if total_count == 0:
        print("No processable image files found in the directory.")
        return

    print(
        f"Batch processing complete: total {total_count}, succeeded {success_count}, failed {failed_count}."
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove image backgrounds for single files or directories.")
    parser.add_argument("input_path", type=str, help="Input image path or input directory path.")
    parser.add_argument("output_path", type=str, help="Output image path or output directory path.")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="When input is a directory, process subdirectories recursively and preserve structure.",
    )

    args = parser.parse_args()

    input_path = args.input_path.strip('"')
    output_path = args.output_path.strip('"')

    if os.path.isdir(input_path):
        remove_background_from_directory(input_path, output_path, args.recursive)
    else:
        remove_image_background(input_path, output_path)
