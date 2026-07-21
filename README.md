# smart-image-tools

A collection of lightweight Python scripts for common image processing tasks.

## Scripts

### `compress_jpg.py`

Batch compress `.jpg`/`.jpeg` images to reduce file size while preserving the
main visual content.

- Accepts either a single `.jpg`/`.jpeg` file path or a directory path.
- Saves compressed `.jpg` files next to the source file with a configurable suffix.
- Recursively scans subdirectories by default.
- Preserves EXIF metadata by default; can be stripped with `--strip-exif`.
- Avoids overwriting existing files by appending a counter to the filename.

> **Note:** JPEG is a lossy format. This script re-encodes images with a high
> default quality of `92` to keep the result visually close to the original. You
> can tune the trade-off between size and quality via the `--quality` argument.

### `convert_webp_to_jpg.py`

Batch convert `.webp` images to `.jpg` format.

- Accepts either a single `.webp` file path or a directory path.
- Saves converted `.jpg` files in the same directory as the source file.
- Recursively scans subdirectories by default.
- Avoids overwriting existing `.jpg` files by appending a counter to the filename.

> **Note:** JPEG is a lossy format. The script uses a high default quality of `95`
> to keep the conversion visually lossless. You can adjust the quality via the
> `--quality` argument.

## Environment

- Python 3.9+
- [Pillow](https://python-pillow.org/)

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate (Linux / macOS)
source .venv/bin/activate

# Activate (Windows PowerShell)
# .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Compress a single JPG

```bash
python compress_jpg.py /path/to/image.jpg
```

### Compress all JPG/JPEG images in a directory

```bash
python compress_jpg.py /path/to/images
```

### Compress only the current directory (no recursion)

```bash
python compress_jpg.py /path/to/images --no-recursive
```

### Set JPEG quality (1–100)

```bash
python compress_jpg.py /path/to/images --quality 85
```

### Strip EXIF metadata for smaller files

```bash
python compress_jpg.py /path/to/images --strip-exif
```

### Convert a single file

```bash
python convert_webp_to_jpg.py /path/to/image.webp
```

### Convert all WebP images in a directory

```bash
python convert_webp_to_jpg.py /path/to/images
```

### Convert only the current directory (no recursion)

```bash
python convert_webp_to_jpg.py /path/to/images --no-recursive
```

### Set JPEG quality (1–100)

```bash
python convert_webp_to_jpg.py /path/to/images --quality 100
```

## Examples

```bash
# Compress one image
python compress_jpg.py ~/Pictures/photo.jpg
# Output: ~/Pictures/photo_compressed.jpg

# Batch compress a folder
python compress_jpg.py ~/Pictures/vacation --quality 90
# Output: creates _compressed.jpg files next to each source image

# Convert one image
python convert_webp_to_jpg.py ~/Pictures/photo.webp
# Output: ~/Pictures/photo.jpg

# Batch convert a folder
python convert_webp_to_jpg.py ~/Pictures/vacation --quality 95
# Output: creates .jpg files next to each .webp file
```

## License

MIT
