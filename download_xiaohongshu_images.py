#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download images from a Xiaohongshu (小红书) note.

Accepts a raw Xiaohongshu URL, an xhslink.cn short link, or an arbitrary string
that contains one of those links. The script resolves short links, parses the
note page, extracts the image list, and downloads the images to a local folder.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import requests


# Common headers to reduce the chance of being blocked by Xiaohongshu.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.xiaohongshu.com/",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download images from a Xiaohongshu note."
    )
    parser.add_argument(
        "input",
        type=str,
        help=(
            "A Xiaohongshu URL, an xhslink.cn short link, "
            "or text containing one of those links."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="xiaohongshu_downloads",
        metavar="DIR",
        help="Output directory for downloaded images. Default: xiaohongshu_downloads",
    )
    parser.add_argument(
        "--original",
        action="store_true",
        help=(
            "Try to download the unprocessed original image by stripping "
            "watermark/processing parameters. May fail if the CDN rejects the URL."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        metavar="SEC",
        help="HTTP request timeout in seconds. Default: 30",
    )
    return parser.parse_args()


def extract_urls(text: str) -> list[str]:
    """Extract URLs from arbitrary user pasted text."""
    # Match http:// or https:// URLs, stopping at common punctuation/delimiters.
    pattern = re.compile(r"https?://[^\s<>\u4e00-\u9fff\"'，。、；：？！]+")
    return pattern.findall(text)


def resolve_short_link(url: str, timeout: int) -> str:
    """Resolve an xhslink.cn short link to the final xiaohongshu.com URL."""
    response = requests.get(
        url, headers=HEADERS, timeout=timeout, allow_redirects=True
    )
    response.raise_for_status()
    final_url = response.url
    if "xiaohongshu.com" not in final_url:
        raise ValueError(f"Short link did not resolve to xiaohongshu.com: {final_url}")
    return final_url


def extract_note_id(url: str) -> str:
    """Extract the note id from a Xiaohongshu note URL."""
    parsed = urlparse(url)
    # /explore/<note_id>
    match = re.search(r"/explore/([a-zA-Z0-9]+)", parsed.path)
    if match:
        return match.group(1)
    # /discovery/item/<note_id>
    match = re.search(r"/discovery/item/([a-zA-Z0-9]+)", parsed.path)
    if match:
        return match.group(1)
    # fallback: query parameter sometimes contains note id
    match = re.search(r"(?:^|&)note_id=([a-zA-Z0-9]+)", parsed.query)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract note id from URL: {url}")


def fetch_note_page(url: str, timeout: int) -> str:
    """Fetch the Xiaohongshu note HTML page."""
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    if response.status_code == 426:
        raise RuntimeError(
            "Xiaohongshu returned a verification/captcha page (HTTP 426). "
            "Try again later or use a different network environment."
        )
    response.raise_for_status()
    return response.text


def parse_initial_state(html: str) -> dict:
    """Extract window.__INITIAL_STATE__ from the page HTML."""
    # Look for the JSON assignment in script tags.
    pattern = re.compile(
        r"(?:window\.)?__INITIAL_STATE__\s*=\s*(\{.*?\});?\s*</script>",
        re.DOTALL,
    )
    match = pattern.search(html)
    if not match:
        # Try a more lenient pattern without the closing script tag anchor.
        pattern = re.compile(
            r"(?:window\.)?__INITIAL_STATE__\s*=\s*(\{.*?\});?\s*(?:</script>|$)",
            re.DOTALL,
        )
        match = pattern.search(html)
    if not match:
        raise ValueError("Could not find note data (__INITIAL_STATE__) in page HTML.")
    raw = match.group(1)
    # Xiaohongshu writes a JavaScript object literal that may contain
    # bare `undefined` values, which is not valid JSON. Normalize them.
    raw = re.sub(r":\s*undefined(?=\s*[,}\]])", ":null", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse __INITIAL_STATE__: {exc}") from exc


def _iter_strings(obj):
    """Yield every string value in a nested dict/list structure."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_strings(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_strings(item)


def extract_image_urls(initial_state: dict) -> list[str]:
    """Extract image URLs from the note's imageList, fallback to string search."""
    # Prefer structured imageList data so we get one URL per image.
    note_detail_map = initial_state.get("note", {}).get("noteDetailMap", {})
    for note_data in note_detail_map.values():
        image_list = note_data.get("note", {}).get("imageList", [])
        if image_list:
            urls = []
            for image in image_list:
                url_default = image.get("urlDefault")
                if url_default:
                    urls.append(url_default)
                    continue
                info_list = image.get("infoList", [])
                for info in info_list:
                    if info.get("imageScene") == "WB_DFT" and info.get("url"):
                        urls.append(info["url"])
                        break
                else:
                    for info in info_list:
                        if info.get("url"):
                            urls.append(info["url"])
                            break
            if urls:
                return urls

    # Fallback: scrape every image-domain URL from the whole state.
    image_domains = (
        "ci.xiaohongshu.com",
        "picasso-free.xhscdn.com",
        "sns-webpic-qc.xhscdn.com",
        "sns-webpic.xhscdn.com",
        "sns-img-hw.xhscdn.com",
        "sns-img-bd.xhscdn.com",
    )
    urls = []
    for text in _iter_strings(initial_state):
        lower = text.lower()
        if any(domain in lower for domain in image_domains):
            candidate = unquote(text)
            for url in re.split(r'[",\s]+', candidate):
                url = url.strip().strip('"')
                if any(domain in url.lower() for domain in image_domains):
                    urls.append(url)
    seen = set()
    unique = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def clean_image_url(url: str, original: bool) -> str:
    """Remove processing parameters / watermark from a Xiaohongshu image URL."""
    if not original:
        return url
    # xhscdn.com URLs use !param suffix.
    if "!" in url:
        url = url.split("!")[0]
    # ci.xiaohongshu.com URLs use query parameters for image processing.
    if "ci.xiaohongshu.com" in url and "?" in url:
        url = url.split("?")[0]
    return url


def download_image(
    url: str, output_path: Path, timeout: int, referer_url: str | None = None
) -> Optional[str]:
    """Download a single image to the given path and return its real extension."""
    headers = {
        **HEADERS,
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    if referer_url:
        headers["Referer"] = referer_url
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    output_path.write_bytes(response.content)

    content_type = response.headers.get("Content-Type", "").lower()
    if "webp" in content_type:
        return ".webp"
    if "png" in content_type:
        return ".png"
    if "gif" in content_type:
        return ".gif"
    if "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"
    return None


def generate_unique_path(directory: Path, note_id: str, index: int, url: str) -> Path:
    """Generate a non-conflicting output path for an image."""
    # Try to infer extension from URL; default to jpg.
    ext = Path(urlparse(url).path).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = ".jpg"
    target = directory / f"{note_id}_{index:03d}{ext}"
    counter = 1
    original_target = target
    while target.exists():
        target = original_target.with_name(
            f"{original_target.stem}_{counter}{original_target.suffix}"
        )
        counter += 1
    return target


def main() -> int:
    args = parse_args()

    # 1. Extract URLs from the input text.
    urls = extract_urls(args.input)
    if not urls:
        print("Error: No URL found in the provided input.", file=sys.stderr)
        return 1

    # 2. Find a Xiaohongshu-related URL (prefer the longest, which is usually the full link).
    xhs_urls = [
        u for u in urls if "xiaohongshu.com" in u.lower() or "xhslink.cn" in u.lower()
    ]
    if not xhs_urls:
        print(
            "Error: No Xiaohongshu (xiaohongshu.com or xhslink.cn) URL found.",
            file=sys.stderr,
        )
        return 1

    target_url = max(xhs_urls, key=len)

    # 3. Resolve short link if needed.
    if "xhslink.cn" in target_url.lower():
        print(f"Resolving short link: {target_url}")
        try:
            target_url = resolve_short_link(target_url, args.timeout)
        except requests.RequestException as exc:
            print(f"Error: Failed to resolve short link: {exc}", file=sys.stderr)
            return 1
        print(f"Resolved to: {target_url}")

    # 4. Validate and extract note id.
    try:
        note_id = extract_note_id(target_url)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Note id: {note_id}")

    # 5. Fetch note page.
    try:
        html = fetch_note_page(target_url, args.timeout)
    except requests.RequestException as exc:
        print(f"Error: Failed to fetch note page: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # 6. Parse initial state and extract images.
    try:
        initial_state = parse_initial_state(html)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 0

    image_urls = extract_image_urls(initial_state)
    if not image_urls:
        print("Warning: No images found in the note.", file=sys.stderr)
        return 0

    print(f"Found {len(image_urls)} image(s).")

    # 7. Prepare output directory.
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 8. Download images.
    downloaded = 0
    failed = 0
    for idx, url in enumerate(image_urls, start=1):
        clean_url = clean_image_url(url, args.original)
        output_path = generate_unique_path(output_dir, note_id, idx, clean_url)
        final_path = output_path
        try:
            actual_ext = download_image(
                clean_url, output_path, args.timeout, referer_url=target_url
            )
            if actual_ext and output_path.suffix.lower() != actual_ext:
                final_path = output_path.with_suffix(actual_ext)
                counter = 1
                original_final_path = final_path
                while final_path.exists():
                    final_path = original_final_path.with_name(
                        f"{original_final_path.stem}_{counter}{original_final_path.suffix}"
                    )
                    counter += 1
                output_path.rename(final_path)
            print(f"Downloaded ({idx}/{len(image_urls)}): {final_path.name}")
            downloaded += 1
        except requests.RequestException as exc:
            if args.original and clean_url != url:
                # Fallback to the signed/processed URL if the original is rejected.
                print(
                    f"Original URL failed for image {idx} ({exc}); "
                    f"retrying with the signed URL.",
                    file=sys.stderr,
                )
                output_path = generate_unique_path(output_dir, note_id, idx, url)
                final_path = output_path
                try:
                    actual_ext = download_image(
                        url, output_path, args.timeout, referer_url=target_url
                    )
                    if actual_ext and output_path.suffix.lower() != actual_ext:
                        final_path = output_path.with_suffix(actual_ext)
                        counter = 1
                        original_final_path = final_path
                        while final_path.exists():
                            final_path = original_final_path.with_name(
                                f"{original_final_path.stem}_{counter}{original_final_path.suffix}"
                            )
                            counter += 1
                        output_path.rename(final_path)
                    print(f"Downloaded ({idx}/{len(image_urls)}): {final_path.name}")
                    downloaded += 1
                except requests.RequestException as exc2:
                    print(
                        f"Failed to download image {idx}: {exc2}",
                        file=sys.stderr,
                    )
                    failed += 1
            else:
                print(
                    f"Failed to download image {idx}: {exc}",
                    file=sys.stderr,
                )
                failed += 1

    print(
        f"\nDone. Downloaded: {downloaded}, Failed: {failed}, Total: {len(image_urls)}"
    )
    print(f"Output directory: {output_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
