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

### `download_xiaohongshu_images.py`

Download images from a Xiaohongshu (小红书) note.

- Accepts a trimmed short link (`xhslink.cn`), a sentence containing a short link,
  or a full `xiaohongshu.com` note URL.
- Resolves short links automatically and extracts the note id from the page.
- Downloads each image in the note to a local folder.
- Detects the real image format (`.webp`, `.jpg`, `.png`, etc.) from the HTTP
  `Content-Type` header and uses the correct file extension.
- Avoids overwriting existing files by appending a counter to the filename.
- Use `--original` to attempt downloading the unprocessed original image.

> **Note:** Xiaohongshu image URLs are signed and may expire quickly. If a
> download fails, rerun the script with a fresh link. `--original` may fail when
> the CDN rejects the unsigned URL; the script falls back to the signed URL in
> that case.

### `download_douyin_images.py`

Download images from a Douyin (抖音) note/image work.

- Accepts a `https://v.douyin.com` short link, pasted share text containing a
  short link, a full `www.douyin.com/note/<id>` URL, or a `/video/<id>` URL.
- The URL must include the `https://` scheme; bare `v.douyin.com/xxxxx` text is
  not extracted.
- Resolves short links and normalizes all inputs to Douyin's mobile share
  endpoint, which avoids the signature challenge on the desktop site.
- Downloads each image in the note to a local folder.
- Detects the real image format (`.webp`, `.jpg`, `.png`, etc.) from the HTTP
  `Content-Type` header and uses the correct file extension.
- Avoids overwriting existing files by appending a counter to the filename.
- Use `--original` to attempt downloading the unsigned original image.

> **Note:** Douyin image URLs are signed and expire quickly. `--original` may
> fail when the CDN rejects the unsigned URL; the script falls back to the
> signed URL in that case. Video-only works (`/video/<id>`) may not provide
> downloadable images through this endpoint.

## Environment

- Python 3.9+
- [Pillow](https://python-pillow.org/)
- [requests](https://requests.readthedocs.io/)

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

### Download images from a Xiaohongshu note

```bash
python download_xiaohongshu_images.py "http://xhslink.cn/o/xxxxxx"
```

### Download from pasted text containing a short link

```bash
python download_xiaohongshu_images.py "复制这段话 打开小红书 http://xhslink.cn/o/xxxxxx 查看笔记~"
```

### Download from a full xiaohongshu.com URL

```bash
python download_xiaohongshu_images.py "https://www.xiaohongshu.com/explore/xxxxx?..."
```

### Specify output directory

```bash
python download_xiaohongshu_images.py "http://xhslink.cn/o/xxxxxx" -o ~/Pictures/xhs
```

### Try to download original unprocessed images

```bash
python download_xiaohongshu_images.py "http://xhslink.cn/o/xxxxxx" --original
```

### Download images from a Douyin note

```bash
python download_douyin_images.py "https://v.douyin.com/xxxxx"
```

### Download from pasted text containing a short link

```bash
python download_douyin_images.py "6.46 复制打开抖音，看看【博主的图文作品】... https://v.douyin.com/xxxxx/ :6pm"
```

### Download from a full douyin.com URL

```bash
python download_douyin_images.py "https://www.douyin.com/note/xxxxx"
```

### Download from a douyin.com video URL

```bash
python download_douyin_images.py "https://www.douyin.com/video/xxxxx"
```

> Video-only works usually do not contain downloadable images through this
> endpoint and will exit with an error.

### Specify output directory for Douyin images

```bash
python download_douyin_images.py "https://v.douyin.com/xxxxx" -o ~/Pictures/douyin
```

### Try to download original unprocessed Douyin images

```bash
python download_douyin_images.py "https://v.douyin.com/xxxxx" --original
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

# Download Xiaohongshu note images
python download_xiaohongshu_images.py "http://xhslink.cn/o/xxxxxx" -o ~/Pictures/xhs
# Output: creates ~/Pictures/xhs/<note_id>_001.webp, ...

# Download Douyin note images
python download_douyin_images.py "https://v.douyin.com/xxxxx" -o ~/Pictures/douyin
# Output: creates ~/Pictures/douyin/<work_id>_001.webp, ...
```

## License

MIT
