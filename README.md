# smart-image-tools

A collection of lightweight Python scripts for common image processing tasks.

## Scripts

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
# Convert one image
python convert_webp_to_jpg.py ~/Pictures/photo.webp
# Output: ~/Pictures/photo.jpg

# Batch convert a folder
python convert_webp_to_jpg.py ~/Pictures/vacation --quality 95
# Output: creates .jpg files next to each .webp file
```

## License

MIT
