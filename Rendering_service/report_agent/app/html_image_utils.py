"""HTML preview image helpers.

This module keeps preview image preparation independent from PDF generation code.
"""

import base64
import os
import re
from io import BytesIO

import httpx
from dotenv import load_dotenv
from PIL import Image, ImageDraw

from pathlib import Path

# Load .env for preview runtime.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


async def prepare_html_images(data: dict) -> dict:
    """Embed candidate/evidence images for HTML preview only.

    Evidence images are always converted to data URIs when possible, otherwise
    a generated placeholder is used so the HTML never shows broken image icons.
    
    Skips images that are already embedded to optimize for cached runs.
    Timeouts and failures gracefully skip to placeholders to avoid startup hangs.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False) as client:
            signed_url_cache: dict[tuple[str, str], str] = {}

            # Candidate photo
            photo_url = data.get("candidate", {}).get("photo_url", "")
            if not data.get("candidate", {}).get("photo_b64"):
                data.setdefault("candidate", {})["photo_b64"] = await _fetch_b64(client, photo_url)

            total_images = 0
            embedded_images = 0
            placeholder_images = 0
            skipped_images = 0

            for alert in data.get("proctoring", {}).get("alerts", []):
                for i, img in enumerate(alert.get("images", [])):
                    total_images += 1
                    
                    # Skip if already embedded
                    if img.get("b64", "").startswith("data:image/"):
                        skipped_images += 1
                        embedded_images += 1
                        continue
                    
                    img["b64"] = ""

                    final_url = ""
                    current_url = img.get("url", "")
                    if current_url and await _is_image_url_accessible(client, current_url):
                        final_url = current_url
                    else:
                        try:
                            refreshed_url = await _refresh_signed_evidence_url(client, img, signed_url_cache)
                            if refreshed_url and await _is_image_url_accessible(client, refreshed_url):
                                img["url"] = refreshed_url
                                final_url = refreshed_url
                        except Exception:
                            pass  # Skip if refresh fails

                    if final_url:
                        b64_value = await _fetch_b64(client, final_url)
                        if b64_value:
                            img["b64"] = b64_value
                            embedded_images += 1
                            continue

                    img["b64"] = _generate_placeholder_image(i + 1, img.get("file_name", "Frame"))
                    placeholder_images += 1

            if total_images > 0:
                summary = f"[preview] Evidence images: total={total_images}, embedded={embedded_images}, placeholders={placeholder_images}"
                if skipped_images > 0:
                    summary += f", skipped={skipped_images} (cached)"
                print(summary)
    except Exception as e:
        print(f"[preview] Warning: Image preparation had issues: {type(e).__name__}. Proceeding with placeholders.")

    return data


async def _fetch_b64(client: httpx.AsyncClient, url: str) -> str:
    if not url or not isinstance(url, str):
        return ""

    for _ in range(2):
        try:
            resp = await client.get(url, timeout=20.0)
            if resp.status_code != 200 or len(resp.content) <= 100:
                continue
            mime = (resp.headers.get("content-type") or "image/jpeg").split(";")[0]
            if not mime.startswith("image/"):
                continue
            encoded = base64.b64encode(resp.content).decode()
            return f"data:{mime};base64,{encoded}"
        except Exception:
            continue
    return ""


async def _is_image_url_accessible(client: httpx.AsyncClient, url: str) -> bool:
    if not url or not isinstance(url, str):
        return False

    is_signed_storage_url = "/storage/v1/object/sign/" in url

    if is_signed_storage_url:
        try:
            resp = await client.get(url, timeout=5.0)
            if resp.status_code != 200:
                return False
            ctype = (resp.headers.get("content-type") or "").split(";")[0]
            return ctype.startswith("image/") and len(resp.content) > 100
        except Exception:
            return False

    try:
        resp = await client.head(url, timeout=5.0)
        if resp.status_code == 200:
            ctype = (resp.headers.get("content-type") or "").split(";")[0]
            if ctype.startswith("image/"):
                return True
    except Exception:
        pass
    
    return False

    try:
        resp = await client.get(url, timeout=10.0)
        if resp.status_code != 200:
            return False
        ctype = (resp.headers.get("content-type") or "").split(";")[0]
        return ctype.startswith("image/") and len(resp.content) > 100
    except Exception:
        return False


async def _refresh_signed_evidence_url(
    client: httpx.AsyncClient,
    img: dict,
    cache: dict[tuple[str, str], str],
) -> str:
    path = img.get("supabase_path", "")
    bucket = img.get("bucket") or "evidence-frame"
    if not path:
        return ""

    cache_key = (bucket, path)
    if cache_key in cache:
        return cache[cache_key]

    if not SUPABASE_URL:
        return ""

    api_key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY
    if not api_key:
        return ""

    sign_url = f"{SUPABASE_URL}/storage/v1/object/sign/{bucket}/{path}"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = await client.post(sign_url, headers=headers, json={"expiresIn": 86400}, timeout=20.0)
        if resp.status_code not in (200, 201):
            return ""

        payload = resp.json()
        signed_url = payload.get("signedURL") or payload.get("signedUrl") or ""
        if not signed_url:
            return ""

        full_url = signed_url if signed_url.startswith(("http://", "https://")) else f"{SUPABASE_URL}{signed_url}"
        cache[cache_key] = full_url
        return full_url
    except Exception:
        return ""


def _generate_placeholder_image(frame_num: int, filename: str = "Frame") -> str:
    try:
        img = Image.new("RGB", (400, 300), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)

        square_size = 20
        for x in range(0, 400, square_size * 2):
            for y in range(0, 300, square_size * 2):
                draw.rectangle([x, y, x + square_size, y + square_size], fill=(220, 220, 220))
                draw.rectangle(
                    [x + square_size, y + square_size, x + square_size * 2, y + square_size * 2],
                    fill=(220, 220, 220),
                )

        draw.text((200, 80), f"Frame {frame_num}", fill=(100, 100, 100), anchor="mm")
        draw.text((200, 140), filename[:30], fill=(120, 120, 120), anchor="mm")
        draw.text((200, 240), "Image unavailable", fill=(150, 100, 100), anchor="mm")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        b64_data = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{b64_data}"
    except Exception:
        return ""


def smart_title(value: str) -> str:
    """Title-case display text while preserving common acronyms."""
    if value is None:
        return ""

    text = re.sub(r"\s+", " ", str(value).replace("_", " ").strip())
    if not text:
        return ""

    force_upper = {"AI", "LLM", "JIT", "API", "HR", "SQL", "ID", "UTC", "QA", "UI", "UX"}
    words = []
    for raw in text.split(" "):
        clean = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
        if clean in force_upper:
            words.append(raw.upper())
        else:
            words.append(raw[:1].upper() + raw[1:].lower() if raw else raw)
    return " ".join(words)
