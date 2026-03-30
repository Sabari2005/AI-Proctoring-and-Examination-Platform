"""Unified FastAPI rendering service for JIT + LLM morphing reports.

This service renders the appropriate HTML template based on report mode and
serves evidence frames in paged batches for hybrid loading.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from app.html_image_utils import _refresh_signed_evidence_url, smart_title
from app.llm_summary import _fallback_summary
from app.parser import parse_report_input

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Unified Report Renderer", version="1.0.0")
app.mount("/assets", StaticFiles(directory=str(BASE_DIR)), name="assets")


class RenderRequest(BaseModel):
    report_json: dict[str, Any]
    include_preview_frame: bool = False


REPORT_STORE: dict[str, dict[str, Any]] = {}


def _select_template(report_data: dict[str, Any]) -> tuple[str, str]:
    mode = str(report_data.get("mode") or "").lower()
    has_llm = bool((report_data.get("questions") or {}).get("llm_morphed_questions"))
    if mode == "morphing" or has_llm:
        return "llm_report.html", "llm_morphing"
    return "report.html", "jit"


def _build_template_env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
    env.filters["zip"] = zip
    env.filters["smart_title"] = smart_title
    return env


def _preview_styles() -> str:
    return """
<style>
  html, body {
    background: #2d3748 !important;
    margin: 0 !important;
    padding: 40px 0 !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    gap: 30px !important;
    min-height: 100vh;
  }
  .page {
    width: 794px !important;
    min-height: 1123px !important;
    max-width: 794px !important;
    box-sizing: border-box !important;
    border: 3px solid #000 !important;
    outline: none !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.7) !important;
    background: #fff !important;
    position: relative !important;
    overflow: visible !important;
    flex-shrink: 0 !important;
  }
  .page::after {
    content: "A4 Page";
    display: block;
    position: absolute;
    top: -26px;
    left: 0;
    font-family: monospace;
    font-size: 12px;
    color: #a0aec0;
    pointer-events: none;
    z-index: 999;
  }
</style>
"""


def _browser_view_centering() -> str:
    # Minimal centering CSS for all browser views (not just preview mode)
    return """
<style id="browser-view-centering">
    html, body {
        background: #000000 !important;
        margin: 0 !important;
        padding: 20px 0 !important;
        width: 100% !important;
        max-width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        min-height: 100vh;
        overflow-x: hidden !important;
    }
    .page {
        box-shadow: 0 2px 10px rgba(0,0,0,0.1) !important;
        margin-left: auto !important;
        margin-right: auto !important;
        margin-bottom: 30px !important;
    }
</style>
"""


def _load_report_css() -> str:
    css_text = (TEMPLATES_DIR / "report.css").read_text(encoding="utf-8")
    return re.sub(r"\.\./([A-Za-z0-9_\-]+\.svg)", r"/assets/\1", css_text)


def _build_render_context(report_data: dict[str, Any], report_id: str) -> dict[str, Any]:
    context = json.loads(json.dumps(report_data))
    context["report_id"] = report_id
    alerts = ((context.get("proctoring") or {}).get("alerts") or [])
    all_images_by_alert: list[list[dict[str, Any]]] = []
    paged_alerts: list[dict[str, Any]] = []

    for idx, alert in enumerate(alerts):
        images = list(alert.get("images") or [])
        all_images_by_alert.append(images)
        alert_copy = dict(alert)
        alert_copy["images"] = []
        alert_copy["_hybrid_alert_index"] = idx
        alert_copy["_image_total"] = len(images)
        paged_alerts.append(alert_copy)

    context.setdefault("proctoring", {})["alerts"] = paged_alerts
    context["_all_images_by_alert"] = all_images_by_alert
    REPORT_STORE[report_id] = {
        "report_data": report_data,
        "all_images_by_alert": all_images_by_alert,
    }
    return context


async def _build_evidence_manifest(report_id: str, all_images_by_alert: list[list[dict[str, Any]]]) -> dict[str, Any]:
    signed_cache: dict[tuple[str, str], str] = {}
    alerts_payload: list[dict[str, Any]] = []

    for alert_index, images in enumerate(all_images_by_alert):
        items: list[dict[str, Any]] = []
        for item in list(images or []):
            item_copy = dict(item)
            item_copy["url"] = await _ensure_image_url(item_copy, signed_cache)
            items.append(
                {
                    "url": item_copy.get("url", ""),
                    "file_name": item_copy.get("file_name", ""),
                    "time": item_copy.get("time", ""),
                    "supabase_path": item_copy.get("supabase_path", ""),
                    "bucket": item_copy.get("bucket", "evidence-frame"),
                }
            )
        alerts_payload.append({"alert_index": alert_index, "total": len(items), "items": items})

    return {
        "status": "ok",
        "report_id": report_id,
        "page_size": 10,
        "alerts": alerts_payload,
    }


async def _ensure_image_url(item: dict[str, Any], signed_cache: dict[tuple[str, str], str]) -> str:
    current_url = str(item.get("url") or "").strip()
    if current_url and "/storage/v1/object/sign/" in current_url:
        return current_url

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
            refreshed = await _refresh_signed_evidence_url(client, item, signed_cache)
            if refreshed:
                return refreshed
    except Exception:
        return current_url
    return current_url


def _inject_styles(html_content: str, include_preview_frame: bool) -> str:
    stylesheet_tag = '<link rel="stylesheet" href="/static/report.css" />'
    if stylesheet_tag not in html_content:
        html_content = html_content.replace("</head>", f"{stylesheet_tag}\n</head>")

    # Force stylesheet application even when external CSS requests are blocked/cached.
    if 'id="report-inline-css"' not in html_content:
        inline_css = _load_report_css()
        html_content = html_content.replace(
            "</head>",
            f'<style id="report-inline-css">\n{inline_css}\n</style>\n</head>',
        )

    # Always apply browser-centered A4 view in web UI.
    if 'id="browser-view-centering"' not in html_content:
        centering_css = _browser_view_centering()
        html_content = html_content.replace("</head>", f"{centering_css}\n</head>")

    if not include_preview_frame:
        return html_content
    extra = _preview_styles()
    return html_content.replace("</head>", f"{extra}\n</head>")


def _inject_inline_evidence_manifest(html_content: str, manifest: dict[str, Any]) -> str:
    _ = manifest
    return html_content


async def _fetch_report_json_from_url(src: str) -> dict[str, Any]:
    source = str(src or "").strip()
    if not source:
        raise HTTPException(status_code=400, detail="Missing src URL")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False) as client:
            resp = await client.get(source)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Unable to fetch report JSON (HTTP {resp.status_code})")

        content_type = str(resp.headers.get("content-type") or "").lower()
        if "json" not in content_type and "text/plain" not in content_type:
            raise HTTPException(status_code=400, detail="Source URL did not return JSON content")

        payload = resp.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid report JSON payload")
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to load report JSON: {exc}")


async def _fetch_report_json_from_storage(bucket: str, path: str) -> dict[str, Any]:
    storage_bucket = str(bucket or "").strip()
    object_path = str(path or "").strip()
    if not storage_bucket or not object_path:
        raise HTTPException(status_code=400, detail="bucket and path are required")

    supabase_url = str(os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    service_role = str(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()
    if not supabase_url or not service_role:
        raise HTTPException(status_code=500, detail="Supabase credentials not configured in renderer")

    encoded_path = quote(object_path, safe="/-_.~")
    url = f"{supabase_url}/storage/v1/object/{storage_bucket}/{encoded_path}"
    headers = {
        "apikey": service_role,
        "Authorization": f"Bearer {service_role}",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Unable to fetch report JSON from storage (HTTP {resp.status_code})")

        content_type = str(resp.headers.get("content-type") or "").lower()
        if "json" not in content_type and "text/plain" not in content_type:
            raise HTTPException(status_code=400, detail="Storage object did not return JSON content")

        payload = resp.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid report JSON payload")
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to load report JSON from storage: {exc}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "unified-report-renderer"}


async def _render_report_core(req: RenderRequest) -> dict[str, Any]:
    report_id = uuid.uuid4().hex
    parsed = parse_report_input(req.report_json)
    parsed["ai_summary"] = _fallback_summary(parsed)

    template_name, detected_mode = _select_template(parsed)
    context = _build_render_context(parsed, report_id)
    env = _build_template_env()
    template = env.get_template(template_name)
    html_content = template.render(**context)
    html_content = _inject_styles(html_content, req.include_preview_frame)

    all_images_by_alert = context.get("_all_images_by_alert", [])
    evidence_manifest = await _build_evidence_manifest(report_id, all_images_by_alert)
    html_content = _inject_inline_evidence_manifest(html_content, evidence_manifest)

    REPORT_STORE[report_id] = {
        "html": html_content,
        "template_name": template_name,
        "mode": detected_mode,
        "include_preview_frame": req.include_preview_frame,
        "all_images_by_alert": all_images_by_alert,
    }

    return {
        "status": "ok",
        "report_id": report_id,
        "mode": detected_mode,
        "template": template_name,
        "html_url": f"/reports/{report_id}",
        "report_html_url": None,
        "evidence_manifest_url": None,
        "evidence_api": f"/reports/{report_id}/evidence",
    }


@app.post("/render", response_class=JSONResponse)
async def render_report(req: RenderRequest, request: Request):
    _ = request
    return await _render_report_core(req)


@app.get("/reports/{report_id}", response_class=HTMLResponse)
async def get_rendered_report(report_id: str):
    stored = REPORT_STORE.get(report_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Report not found")
    return HTMLResponse(stored["html"])


@app.get("/reports/{report_id}/evidence", response_class=JSONResponse)
async def get_report_evidence(
    report_id: str,
    alert_index: int = Query(..., ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    stored = REPORT_STORE.get(report_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Report not found")

    all_images_by_alert = stored.get("all_images_by_alert") or []
    if alert_index >= len(all_images_by_alert):
        raise HTTPException(status_code=404, detail="Alert index out of range")

    images = all_images_by_alert[alert_index]
    total = len(images)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = images[start:end]

    signed_cache: dict[tuple[str, str], str] = {}
    payload_items: list[dict[str, Any]] = []
    for item in page_items:
        item_copy = dict(item)
        item_copy["url"] = await _ensure_image_url(item_copy, signed_cache)
        payload_items.append(
            {
                "url": item_copy.get("url", ""),
                "file_name": item_copy.get("file_name", ""),
                "time": item_copy.get("time", ""),
                "supabase_path": item_copy.get("supabase_path", ""),
                "bucket": item_copy.get("bucket", "evidence-frame"),
            }
        )

    total_pages = (total + page_size - 1) // page_size if total else 0
    has_next = page < total_pages
    return {
        "status": "ok",
        "report_id": report_id,
        "alert_index": alert_index,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": has_next,
        "items": payload_items,
    }


@app.get("/preview", response_class=HTMLResponse)
async def preview_from_file(
    data_file: str = Query("jit.json"),
    include_preview_frame: bool = Query(True),
):
    file_path = (BASE_DIR / data_file).resolve()
    if not file_path.exists() or BASE_DIR not in file_path.parents:
        raise HTTPException(status_code=404, detail="Data file not found")

    with open(file_path, encoding="utf-8") as f:
        payload = json.load(f)

    render_result = await _render_report_core(
        RenderRequest(report_json=payload, include_preview_frame=include_preview_frame),
    )
    report_id = render_result["report_id"]
    stored = REPORT_STORE.get(report_id)
    if not stored:
        raise HTTPException(status_code=500, detail="Preview cache missing")
    return HTMLResponse(stored["html"])


@app.get("/preview/from-json-url")
async def preview_from_json_url(
    src: str = Query(..., description="Signed URL to report JSON in storage"),
    include_preview_frame: bool = Query(False),
):
    payload = await _fetch_report_json_from_url(src)
    render_result = await _render_report_core(
        RenderRequest(report_json=payload, include_preview_frame=include_preview_frame),
    )
    report_id = str(render_result.get("report_id") or "").strip()
    if not report_id:
        raise HTTPException(status_code=500, detail="Unable to create report preview")
    return RedirectResponse(url=f"/reports/{report_id}", status_code=307)


@app.get("/preview/from-storage")
async def preview_from_storage(
    bucket: str = Query(..., description="Supabase storage bucket"),
    path: str = Query(..., description="Supabase object path for report JSON"),
    include_preview_frame: bool = Query(False),
):
    payload = await _fetch_report_json_from_storage(bucket=bucket, path=path)
    render_result = await _render_report_core(
        RenderRequest(report_json=payload, include_preview_frame=include_preview_frame),
    )
    report_id = str(render_result.get("report_id") or "").strip()
    if not report_id:
        raise HTTPException(status_code=500, detail="Unable to create report preview")
    return RedirectResponse(url=f"/reports/{report_id}", status_code=307)


@app.get("/static/report.css")
async def serve_css():
    css_text = (TEMPLATES_DIR / "report.css").read_text(encoding="utf-8")
    css_text = re.sub(r"\.\./([A-Za-z0-9_\-]+\.svg)", r"/assets/\1", css_text)
    return Response(css_text, media_type="text/css")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("preview_server:app", host="127.0.0.1", port=5050, reload=False)
