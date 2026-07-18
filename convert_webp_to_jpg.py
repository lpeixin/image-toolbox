#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch WebP to JPG converter.

Convert a single .webp file or all .webp files under a directory to .jpg format,
saved in the same location as the source.

Note:
    JPEG is inherently a lossy format. This script uses the highest practical
    quality (default 95) to keep the conversion visually lossless. You can
    override the quality via the --quality argument.
"""

import argparse
import os
import sys
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert WebP image(s) to JPG format."
    )
    parser.add_argument(
        "path",
        type=str,
        help="Path to a .webp file or a directory containing .webp files.",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=95,
        metavar="Q",
        help="JPEG output quality, 1-100. Default is 95.",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        default=True,
        help="Recursively search subdirectories for .webp files. Default is True.",
    )
    parser.add_argument(
        "--no-recursive",
        dest="recursive",
        action="store_false",
        help="Only convert .webp files directly in the given directory.",
    )
    return parser.parse_args()


def validate_quality(value: int) -> int:
    if not 1 <= value <= 100:
        raise argparse.ArgumentTypeError("Quality must be between 1 and 100.")
    return value


def convert_webp_to_jpg(source: Path, quality: int) -> Path:
    """Convert a single WebP file to JPG and return the output path."""
    if source.suffix.lower() != ".webp":
        raise ValueError(f"Not a .webp file: {source}")

    target = source.with_suffix(".jpg")

    # If a JPG with the same name already exists, avoid overwriting by appending a counter.
    counter = 1
    original_target = target
    while target.exists():
        stem = original_target.stem
        target = original_target.with_name(f"{stem}_{counter}.jpg")
        counter += 1

    with Image.open(source) as img:
        # Convert palette/transparent images to RGB, since JPEG does not support alpha.
        if img.mode in ("RGBA", "P", "LA"):
            # For RGBA/LA, blend against a white background to preserve appearance.
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            if img.mode in ("RGBA", "LA"):
                # Use the alpha channel as mask.
                background.paste(
                    img.convert("RGBA") if img.mode == "LA" else img,
                    mask=img.split()[-1],
                )
                img = background
            else:
                img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        img.save(target, format="JPEG", quality=quality, optimize=True)

    return target


def collect_webp_files(root: Path, recursive: bool) -> list[Path]:
    """Collect all .webp files under the given path."""
    if root.is_file():
        return [root] if root.suffix.lower() == ".webp" else []

    if not root.is_dir():
        raise FileNotFoundError(f"Path does not exist: {root}")

    pattern = "**/*.webp" if recursive else "*.webp"
    return sorted(root.glob(pattern))


def main() -> int:
    args = parse_args()
    args.quality = validate_quality(args.quality)

    source_path = Path(args.path).expanduser().resolve()

    try:
        webp_files = collect_webp_files(source_path, args.recursive)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not webp_files:
        print("No .webp files found.")
        return 0

    converted = 0
    failed = 0

    for webp_file in webp_files:
        try:
            target = convert_webp_to_jpg(webp_file, args.quality)
            print(f"Converted: {webp_file} -> {target}")
            converted += 1
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to convert {webp_file}: {exc}", file=sys.stderr)
            failed += 1

    print(f"\nDone. Converted: {converted}, Failed: {failed}, Total: {len(webp_files)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
