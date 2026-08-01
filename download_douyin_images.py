#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download images from a Douyin (抖音) note/work.

Accepts a raw Douyin URL (www.douyin.com/note/<id> or /video/<id>),
a v.douyin.com short link, or an arbitrary string that contains one of
those links. The script resolves short links, parses the work page,
extracts the image list, and downloads the images to a local folder.

For image/note works, the page data is served through the mobile share
endpoint (iesdouyin.com) which does not require executing Douyin's
signature challenge.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import requests


# Mobile Safari headers work best for Douyin's share endpoint.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
        "Mobile/15E148 Safari/604.1"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.douyin.com/",
}

# Hosts that host Douyin image assets.
IMAGE_DOMAINS = (
    "douyinpic.com",
    "douyincdn.com",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download images from a Douyin note/work."
    )
    parser.add_argument(
        "input",
        type=str,
        help=(
            "A Douyin URL (www.douyin.com/note/<id> or /video/<id>), "
            "a v.douyin.com short link, or text containing one of those links."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="douyin_downloads",
        metavar="DIR",
        help="Output directory for downloaded images. Default: douyin_downloads",
    )
    parser.add_argument(
        "--original",
        action="store_true",
        help=(
            "Try to download the unprocessed original image by stripping "
            "signature/query parameters. May fail if the CDN rejects the URL."
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
    """Resolve a v.douyin.com short link to the final share URL."""
    session = requests.Session()
    session.headers.update(HEADERS)
    response = session.get(url, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    final_url = response.url
    if "douyin.com" not in final_url:
        raise ValueError(f"Short link did not resolve to douyin.com: {final_url}")
    return final_url


def extract_work_id(url: str) -> str:
    """Extract the work id from a Douyin note or video URL."""
    parsed = urlparse(url)
    # /note/<work_id>
    match = re.search(r"/note/([a-zA-Z0-9_\-]+)", parsed.path)
    if match:
        return match.group(1)
    # /video/<work_id>
    match = re.search(r"/video/([a-zA-Z0-9_\-]+)", parsed.path)
    if match:
        return match.group(1)
    # fallback: share/query parameters sometimes contain the id
    match = re.search(r"(?:^|&)modal_id=([a-zA-Z0-9_\-]+)", parsed.query)
    if match:
        return match.group(1)
    match = re.search(r"(?:^|&)item_id=([a-zA-Z0-9_\-]+)", parsed.query)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract work id from URL: {url}")


def to_share_url(url: str) -> str:
    """Normalize a Douyin URL to the mobile share endpoint.

    v.douyin.com short links already resolve to the share endpoint.
    www.douyin.com/note/<id> and /video/<id> are converted to the
    corresponding iesdouyin.com/share path.
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    note_match = re.search(r"/note/([a-zA-Z0-9_\-]+)", path)
    if note_match:
        return f"https://www.iesdouyin.com/share/note/{note_match.group(1)}/"

    video_match = re.search(r"/video/([a-zA-Z0-9_\-]+)", path)
    if video_match:
        return f"https://www.iesdouyin.com/share/video/{video_match.group(1)}/"

    if "iesdouyin.com/share/" in url.lower():
        return url.split("?")[0].rstrip("/") + "/"

    raise ValueError(f"Could not convert URL to share endpoint: {url}")


def fetch_share_page(url: str, timeout: int) -> str:
    """Fetch the Douyin share page HTML."""
    session = requests.Session()
    session.headers.update(HEADERS)
    response = session.get(url, timeout=timeout)
    if response.status_code in (403, 429):
        raise RuntimeError(
            "Douyin returned a verification/captcha page. "
            "Try again later, use a different network environment, "
            "or provide a fresh link."
        )
    response.raise_for_status()
    return response.text


def parse_router_data(html: str) -> dict:
    """Extract window._ROUTER_DATA from the share page HTML."""
    pattern = re.compile(
        r"window\._ROUTER_DATA\s*=\s*(\{.*?\});?\s*</script>",
        re.DOTALL,
    )
    match = pattern.search(html)
    if not match:
        raise ValueError(
            "Could not find page data (window._ROUTER_DATA) in the share page HTML."
        )
    raw = match.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse window._ROUTER_DATA: {exc}") from exc


def extract_image_urls(router_data: dict) -> list[str]:
    """Extract image URLs from the share page router data."""
    urls: list[str] = []

    try:
        loader_data = router_data["loaderData"]["note_(id)/page"]
    except (KeyError, TypeError):
        raise ValueError(
            "Could not find note data in the share page. "
            "Video-only works may not provide downloadable images through this endpoint."
        )

    video_info = loader_data.get("videoInfoRes", {})
    item_list = video_info.get("item_list", [])
    if not item_list:
        raise ValueError("No work item found in the share page data.")

    item = item_list[0]
    images = item.get("images") or []
    for image in images:
        url_list = image.get("url_list") if isinstance(image, dict) else None
        if isinstance(url_list, list) and url_list:
            urls.append(url_list[0])

    if urls:
        return _dedupe_urls(urls)

    # Fallback: collect any image-domain URL from the whole state.
    for value in _iter_values(router_data):
        if isinstance(value, str) and _is_image_url(value):
            urls.append(unquote(value).strip())

    return _dedupe_urls(urls)


def _iter_values(obj):
    """Yield every value in a nested dict/list structure."""
    if isinstance(obj, dict):
        for value in obj.values():
            yield value
            yield from _iter_values(value)
    elif isinstance(obj, list):
        for item in obj:
            yield item
            yield from _iter_values(item)


def _is_image_url(text: str) -> bool:
    """Return True if the string looks like a Douyin image URL."""
    if not isinstance(text, str) or not text.startswith("http"):
        return False
    lower = text.lower()
    return any(domain in lower for domain in IMAGE_DOMAINS)


def _dedupe_urls(urls: list[str]) -> list[str]:
    """Remove duplicate URLs while preserving order."""
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def clean_image_url(url: str, original: bool) -> str:
    """Remove signature/query parameters from a Douyin image URL."""
    if not original:
        return url
    if any(domain in url.lower() for domain in IMAGE_DOMAINS) and "?" in url:
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


def generate_unique_path(directory: Path, work_id: str, index: int, url: str) -> Path:
    """Generate a non-conflicting output path for an image."""
    ext = Path(urlparse(url).path).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = ".jpg"
    target = directory / f"{work_id}_{index:03d}{ext}"
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

    # 2. Find a Douyin-related URL (prefer the longest, which is usually the full link).
    douyin_urls = [u for u in urls if "douyin.com" in u.lower()]
    if not douyin_urls:
        print(
            "Error: No Douyin (douyin.com) URL found.",
            file=sys.stderr,
        )
        return 1

    target_url = max(douyin_urls, key=len)

    # 3. Resolve short link if needed.
    if "v.douyin.com" in target_url.lower():
        print(f"Resolving short link: {target_url}")
        try:
            target_url = resolve_short_link(target_url, args.timeout)
        except requests.RequestException as exc:
            print(f"Error: Failed to resolve short link: {exc}", file=sys.stderr)
            return 1
        print(f"Resolved to: {target_url}")

    # 4. Validate and extract work id.
    try:
        work_id = extract_work_id(target_url)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Work id: {work_id}")

    # 5. Normalize to the mobile share endpoint.
    try:
        share_url = to_share_url(target_url)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Share URL: {share_url}")

    # 6. Fetch share page.
    try:
        html = fetch_share_page(share_url, args.timeout)
    except requests.RequestException as exc:
        print(f"Error: Failed to fetch work page: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # 7. Parse router data and extract images.
    try:
        router_data = parse_router_data(html)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        image_urls = extract_image_urls(router_data)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not image_urls:
        print("Warning: No images found in the work.", file=sys.stderr)
        return 1

    print(f"Found {len(image_urls)} image(s).")

    # 8. Prepare output directory.
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 9. Download images.
    downloaded = 0
    failed = 0
    for idx, url in enumerate(image_urls, start=1):
        clean_url = clean_image_url(url, args.original)
        output_path = generate_unique_path(output_dir, work_id, idx, clean_url)
        final_path = output_path
        try:
            actual_ext = download_image(
                clean_url, output_path, args.timeout, referer_url=share_url
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
                # Fallback to the signed URL if the original is rejected.
                print(
                    f"Original URL failed for image {idx} ({exc}); "
                    f"retrying with the signed URL.",
                    file=sys.stderr,
                )
                output_path = generate_unique_path(output_dir, work_id, idx, url)
                final_path = output_path
                try:
                    actual_ext = download_image(
                        url, output_path, args.timeout, referer_url=share_url
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
