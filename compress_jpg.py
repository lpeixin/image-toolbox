#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch JPG/JPEG compressor.

Compress a single .jpg/.jpeg file or all .jpg/.jpeg files under a directory.
The script re-encodes images with high quality and optimization flags to reduce
file size while preserving the main visual content and EXIF metadata.

Note:
    JPEG is inherently a lossy format. This script uses a high default quality
    (92) to keep the re-encoding visually close to the original. You can
    override the quality via the --quality argument. A lower value produces
    smaller files but may introduce visible artifacts.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compress JPG/JPEG image(s) with minimal quality loss."
    )
    parser.add_argument(
        "path",
        type=str,
        help="Path to a .jpg/.jpeg file or a directory containing images.",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=92,
        metavar="Q",
        help="JPEG output quality, 1-100. Default is 92.",
    )
    parser.add_argument(
        "-s",
        "--suffix",
        type=str,
        default="compressed",
        metavar="TEXT",
        help="Suffix added to the output filename. Default is 'compressed'.",
    )
    parser.add_argument(
        "--strip-exif",
        action="store_true",
        help="Strip EXIF metadata to reduce file size further.",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        default=True,
        help="Recursively search subdirectories for images. Default is True.",
    )
    parser.add_argument(
        "--no-recursive",
        dest="recursive",
        action="store_false",
        help="Only compress .jpg/.jpeg files directly in the given directory.",
    )
    return parser.parse_args()


def validate_quality(value: int) -> int:
    if not 1 <= value <= 100:
        raise argparse.ArgumentTypeError("Quality must be between 1 and 100.")
    return value


def collect_jpg_files(root: Path, recursive: bool) -> list[Path]:
    """Collect all .jpg/.jpeg files under the given path."""
    if root.is_file():
        if root.suffix.lower() in (".jpg", ".jpeg"):
            return [root]
        return []

    if not root.is_dir():
        raise FileNotFoundError(f"Path does not exist: {root}")

    if recursive:
        return sorted(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in (".jpg", ".jpeg")
        )
    return sorted(
        path
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in (".jpg", ".jpeg")
    )


def generate_output_path(source: Path, suffix: str) -> Path:
    """Generate an output path that does not overwrite an existing file."""
    target = source.with_name(f"{source.stem}_{suffix}.jpg")
    if not target.exists():
        return target

    counter = 1
    while target.exists():
        target = source.with_name(f"{source.stem}_{suffix}_{counter}.jpg")
        counter += 1
    return target


def compress_jpg(source: Path, quality: int, suffix: str, strip_exif: bool) -> tuple[Path, int, int]:
    """
    Compress a single JPG/JPEG file and return the output path plus original
    and compressed sizes in bytes.
    """
    if source.suffix.lower() not in (".jpg", ".jpeg"):
        raise ValueError(f"Not a .jpg/.jpeg file: {source}")

    target = generate_output_path(source, suffix)
    original_size = source.stat().st_size

    with Image.open(source) as img:
        if img.mode not in ("RGB", "L", "CMYK"):
            img = img.convert("RGB")

        exif = None if strip_exif else img.info.get("exif")
        save_kwargs = {
            "format": "JPEG",
            "quality": quality,
            "optimize": True,
            "progressive": True,
        }
        if exif:
            save_kwargs["exif"] = exif

        img.save(target, **save_kwargs)

    compressed_size = target.stat().st_size
    return target, original_size, compressed_size


def format_size(size_bytes: int) -> str:
    """Return a human readable file size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def main() -> int:
    args = parse_args()
    args.quality = validate_quality(args.quality)

    source_path = Path(args.path).expanduser().resolve()

    try:
        jpg_files = collect_jpg_files(source_path, args.recursive)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not jpg_files:
        print("No .jpg/.jpeg files found.")
        return 0

    compressed = 0
    failed = 0
    total_original = 0
    total_compressed = 0

    for jpg_file in jpg_files:
        try:
            target, original_size, compressed_size = compress_jpg(
                jpg_file, args.quality, args.suffix, args.strip_exif
            )
            change_pct = (
                (compressed_size - original_size) / original_size * 100
                if original_size
                else 0
            )
            total_original += original_size
            total_compressed += compressed_size
            print(
                f"Compressed: {jpg_file} -> {target} "
                f"({format_size(original_size)} -> {format_size(compressed_size)}, "
                f"{change_pct:+.1f}%)"
            )
            compressed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to compress {jpg_file}: {exc}", file=sys.stderr)
            failed += 1

    total_change_pct = (
        (total_compressed - total_original) / total_original * 100
        if total_original
        else 0
    )
    print(
        f"\nDone. Compressed: {compressed}, Failed: {failed}, Total: {len(jpg_files)}"
    )
    print(
        f"Total size: {format_size(total_original)} -> {format_size(total_compressed)} "
        f"({total_change_pct:+.1f}%)"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
