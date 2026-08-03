# AGENTS.md — smart-image-tools

This file is a guide for AI coding agents working on the `smart-image-tools` repository. It assumes no prior knowledge of the project.

## Project overview

`smart-image-tools` is a small collection of standalone, command-line Python scripts for common image-processing tasks. The repository contains no library code, no web service, and no build pipeline — each script is intended to be run directly from the project root.

Current scripts:

| Script | Purpose |
| --- | --- |
| `compress_jpg.py` | Batch compress `.jpg`/`.jpeg` images, preserving EXIF by default. |
| `convert_webp_to_jpg.py` | Batch convert `.webp` images to `.jpg`. |
| `download_xiaohongshu_images.py` | Download images from a Xiaohongshu (小红书) note. |
| `download_douyin_images.py` | Download images from a Douyin (抖音) note/image work. |

All documentation, comments, and docstrings are written in English.

## Technology stack

- **Language:** Python 3.9+ (the local virtual environment uses Python 3.12.7).
- **Dependencies:**
  - `Pillow>=10.0.0` — image reading, conversion, and compression.
  - `requests>=2.31.0` — HTTP requests for the downloader scripts.
- **No package manifest:** There is no `pyproject.toml`, `setup.py`, `setup.cfg`, `tox.ini`, or `Makefile`. Dependency management is limited to `requirements.txt`.

## Repository layout

```text
.
├── .venv/                         # Local Python virtual environment
├── __pycache__/                   # Python bytecode (ignored by git)
├── .gitignore                     # Standard Python gitignore plus runtime output dirs
├── README.md                      # User-facing documentation and usage examples
├── requirements.txt               # Runtime dependencies
├── compress_jpg.py                # JPG compression utility
├── convert_webp_to_jpg.py         # WebP-to-JPG conversion utility
├── download_xiaohongshu_images.py # Xiaohongshu image downloader
└── download_douyin_images.py      # Douyin image downloader
```

## Setup

Create and activate a virtual environment, then install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Build and run commands

There is no build step. Scripts are executed directly:

```bash
# Compress a single image or a directory of JPG/JPEG files
python compress_jpg.py /path/to/image.jpg
python compress_jpg.py /path/to/images --quality 85 --strip-exif

# Convert WebP images to JPG
python convert_webp_to_jpg.py /path/to/image.webp
python convert_webp_to_jpg.py /path/to/images --quality 95

# Download images from a Xiaohongshu note
python download_xiaohongshu_images.py "http://xhslink.cn/o/xxxxxx" -o ~/Pictures/xhs

# Download images from a Douyin note
python download_douyin_images.py "https://v.douyin.com/xxxxx" -o ~/Pictures/douyin
```

Run any script with `--help` to see its full argument list.

## Code organization

Each script is self-contained and follows the same general structure:

1. `parse_args()` — `argparse` CLI definition.
2. Domain-specific helper functions (URL parsing, HTTP fetching, image processing, path generation).
3. `main()` — orchestration, error handling, and formatted output.
4. `if __name__ == "__main__": sys.exit(main())` guard.

There are no shared modules; copy-paste duplication across downloaders is intentional to keep each script independent. If you add reusable logic, consider whether the project would benefit from a shared module or whether the standalone-script convention should be preserved.

## Code style guidelines

- Target Python 3.9+ syntax and type hints.
- Include the file header `#!/usr/bin/env python3` and `# -*- coding: utf-8 -*-`.
- Write docstrings and comments in English.
- Use `pathlib.Path` for filesystem paths.
- Validate user-facing numeric arguments explicitly (e.g., JPEG quality must be in `1–100`).
- Avoid overwriting existing files; append a counter to the filename instead.
- Use broad `except Exception` only at the top-level per-file loop, and print a clear error message to `stderr`.
- Exit codes: return `0` on success, `1` on failure.

## Testing

There is currently no test suite (no `tests/` directory, no `pytest`, no CI). Before making changes, verify behavior manually:

- Run `python <script>.py --help` to ensure argument parsing still works.
- For image scripts: create a small temporary image and confirm the output file is produced and not overwritten.
- For downloader scripts: use a known-good URL and confirm the expected number of images is downloaded. Note that Xiaohongshu and Douyin URLs are signed and expire quickly; failures may be due to expired links rather than code bugs.

If the project grows, add a `tests/` directory using `pytest` and update `requirements.txt` accordingly.

## Security considerations

- The downloader scripts make outbound HTTP requests to third-party services (Xiaohongshu, Douyin, and their CDNs). They use hardcoded browser-like `User-Agent` headers and referers to reduce the chance of being blocked.
- No authentication tokens, API keys, or credentials are stored in the repository.
- Downloaded content is written to user-specified or default output directories (`xiaohongshu_downloads/`, `douyin_downloads/`). These directories are gitignored.
- Do not commit secrets, downloaded media, or runtime output directories.
- When parsing HTML/JSON extracted from third-party pages, the scripts use defensive `try/except` blocks and fallbacks, but page structures can change at any time and break extraction.

## Deployment

There is no deployment process. The repository is a set of local utilities. Users clone or copy the scripts, install dependencies, and run them directly.

## License

MIT (see `README.md`).
