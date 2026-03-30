import json
import os
import re
import ssl
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import quote

from fastapi import FastAPI, Header, HTTPException, status
from sqlalchemy import create_engine, text

try:
    from Report_Generation.main import generate_candidate_exam_report
except ImportError:
    from main import generate_candidate_exam_report

app = FastAPI(title="Report Generation Service", version="1.0.0")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Treat empty process env vars as unset so .env can provide defaults.
        if key and not str(os.environ.get(key) or "").strip():
            os.environ[key] = value


_load_env_file(Path(__file__).resolve().parent / ".env")
_load_env_file(PROJECT_ROOT / ".env")
_DB_ENGINE = create_engine(str(os.getenv("DATABASE_URL") or ""), pool_pre_ping=True)


def _safe_path_component(value: str, fallback: str) -> str:
    text = str(value or "").strip().lower()
    cleaned = re.sub(r"[^a-z0-9._-]+", "_", text).strip("._-")
    return cleaned[:80] or fallback


def _escape_pdf_text(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_dummy_pdf(lines: list[str]) -> bytes:
    text_lines = [line for line in lines if str(line or "").strip()]
    if not text_lines:
        text_lines = ["Candidate report generated"]

    commands: list[str] = ["BT", "/F1 14 Tf", "72 740 Td"]
    for index, line in enumerate(text_lines):
        if index > 0:
            commands.append("0 -20 Td")
        commands.append(f"({_escape_pdf_text(line)}) Tj")
    commands.append("ET")

    stream = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    payload = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for idx, body in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{idx} 0 obj\n".encode("ascii"))
        payload.extend(body)
        payload.extend(b"\nendobj\n")

    xref_start = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    payload.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(payload)


def _call_rendering_service(report_json: dict[str, Any]) -> str | None:
    """Call the rendering service to generate HTML report URL."""
    rendering_service_url = str(
        os.getenv("RENDERING_SERVICE_URL")
        or os.getenv("REPORT_RENDERING_SERVICE_URL")
        or ""
    ).strip().rstrip("/")
    if not rendering_service_url:
        return None

    verify_tls_raw = str(os.getenv("REPORT_RENDER_VERIFY_TLS") or "true").strip().lower()
    verify_tls = verify_tls_raw not in {"0", "false", "no", "off"}
    ssl_context = None if verify_tls else ssl._create_unverified_context()

    try:
        payload_json = json.dumps(
            {"report_json": report_json, "include_preview_frame": False},
            default=_json_default,
        )
        for attempt in range(2):
            req = urllib_request.Request(
                url=f"{rendering_service_url}/render",
                data=payload_json.encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib_request.urlopen(req, timeout=30, context=ssl_context) as resp:
                    if resp.getcode() != 200:
                        continue
                    response_data = json.loads(resp.read().decode("utf-8"))
                    report_html_url = response_data.get("report_html_url")
                    if report_html_url:
                        return str(report_html_url)

                    html_url = response_data.get("html_url")
                    if html_url:
                        html_url_text = str(html_url)
                        if html_url_text.startswith("http://") or html_url_text.startswith("https://"):
                            return html_url_text
                        return f"{rendering_service_url}{html_url_text}"
            except Exception as inner_exc:
                if attempt == 1:
                    raise inner_exc
    except Exception as e:
        print(f"Warning: Failed to call rendering service: {e}")
    return None


def _build_persistent_render_url(report_json_bucket: str, report_json_path: str) -> str | None:
    rendering_service_url = str(
        os.getenv("RENDERING_SERVICE_URL")
        or os.getenv("REPORT_RENDERING_SERVICE_URL")
        or ""
    ).strip().rstrip("/")
    if not rendering_service_url:
        return None

    bucket = quote(str(report_json_bucket or "").strip(), safe="")
    path = quote(str(report_json_path or "").strip(), safe="")
    if not bucket or not path:
        return None
    return f"{rendering_service_url}/preview/from-storage?bucket={bucket}&path={path}"


def _supabase_upload(bucket: str, object_path: str, payload: bytes, content_type: str) -> None:
    supabase_url = str(os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    service_role = str(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()
    if not supabase_url or not service_role:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Supabase credentials missing")

    encoded_object_path = quote(str(object_path or ""), safe="/-_.~")
    url = f"{supabase_url}/storage/v1/object/{bucket}/{encoded_object_path}"
    req = urllib_request.Request(
        url=url,
        data=payload,
        headers={
            "Authorization": f"Bearer {service_role}",
            "apikey": service_role,
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=20) as resp:
            if resp.getcode() not in (200, 201):
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Supabase upload failed")
    except urllib_error.HTTPError as exc:
        details = ""
        try:
            details = exc.read().decode("utf-8", errors="ignore")[:500]
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Supabase upload HTTP {exc.code}: {details}")
    except urllib_error.URLError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Supabase upload error: {exc}")


def _upsert_exam_result_report(
    report: dict[str, Any],
    report_json_bucket: str,
    report_json_path: str,
    report_pdf_bucket: str,
    report_pdf_path: str,
    report_html_url: str | None = None,
) -> dict[str, Any]:
    """Upsert exam result with report paths and HTML URL.
    
    The report_html_url is the rendering service URL (e.g., https://rendering.../reports/{id})
    and is stored alongside existing PDF/JSON paths in exam_results.
    """
    user_details = report.get("user_details") or {}
    launch_details = report.get("launch_code_details") or {}
    selected_attempt = (report.get("attempt") or {}).get("selected_attempt") or {}

    candidate_id = int(user_details.get("candidate_id") or 0)
    drive_id = int(launch_details.get("drive_id") or 0)
    attempt_id = int(selected_attempt.get("attempt_id") or 0)

    if candidate_id <= 0 or drive_id <= 0 or attempt_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Report payload did not include candidate/drive/attempt identifiers",
        )

    score_value = selected_attempt.get("computed_total_marks")
    if score_value is None:
        score_value = selected_attempt.get("total_marks")
    score = None
    if score_value is not None:
        try:
            score = float(score_value)
        except (TypeError, ValueError):
            score = None

    max_marks_raw = (report.get("summary") or {}).get("exam_max_marks")
    try:
        max_marks = float(max_marks_raw) if max_marks_raw is not None else 0.0
    except (TypeError, ValueError):
        max_marks = 0.0

    result_status = "pending_eval"
    if score is not None and max_marks > 0:
        percentage = (float(score) / max_marks) * 100.0
        result_status = "pass" if percentage >= 50.0 else "fail"

    with _DB_ENGINE.begin() as conn:
        existing = conn.execute(
            text(
                """
                SELECT result_id
                FROM exam_results
                WHERE attempt_id = :attempt_id
                   OR (drive_id = :drive_id AND candidate_id = :candidate_id)
                ORDER BY result_id
                LIMIT 1
                """
            ),
            {
                "attempt_id": attempt_id,
                "drive_id": drive_id,
                "candidate_id": candidate_id,
            },
        ).mappings().first()

        if existing:
            result_id = int(existing["result_id"])
            conn.execute(
                text(
                    """
                    UPDATE exam_results
                    SET drive_id = :drive_id,
                        candidate_id = :candidate_id,
                        attempt_id = :attempt_id,
                        score = :score,
                        result_status = :result_status,
                        evaluated_at = NOW(),
                        report_json_bucket = :report_json_bucket,
                        report_json_path = :report_json_path,
                        report_json_uploaded_at = NOW(),
                        report_preview_status = 'ready',
                        report_pdf_bucket = :report_pdf_bucket,
                        report_pdf_path = :report_pdf_path,
                        report_html_url = :report_html_url,
                        updated_at = NOW()
                    WHERE result_id = :result_id
                    """
                ),
                {
                    "result_id": result_id,
                    "drive_id": drive_id,
                    "candidate_id": candidate_id,
                    "attempt_id": attempt_id,
                    "score": score,
                    "result_status": result_status,
                    "report_json_bucket": report_json_bucket,
                    "report_json_path": report_json_path,
                    "report_pdf_bucket": report_pdf_bucket,
                    "report_pdf_path": report_pdf_path,
                    "report_html_url": report_html_url,
                },
            )
        else:
            result_id = int(
                conn.execute(
                    text(
                        """
                        INSERT INTO exam_results (
                            drive_id,
                            candidate_id,
                            attempt_id,
                            score,
                            result_status,
                            evaluated_at,
                            report_json_bucket,
                            report_json_path,
                            report_json_uploaded_at,
                            report_preview_status,
                            report_pdf_bucket,
                            report_pdf_path,
                            report_html_url
                        )
                        VALUES (
                            :drive_id,
                            :candidate_id,
                            :attempt_id,
                            :score,
                            :result_status,
                            NOW(),
                            :report_json_bucket,
                            :report_json_path,
                            NOW(),
                            'ready',
                            :report_pdf_bucket,
                            :report_pdf_path,
                            :report_html_url
                        )
                        RETURNING result_id
                        """
                    ),
                    {
                        "drive_id": drive_id,
                        "candidate_id": candidate_id,
                        "attempt_id": attempt_id,
                        "score": score,
                        "result_status": result_status,
                        "report_json_bucket": report_json_bucket,
                        "report_json_path": report_json_path,
                        "report_pdf_bucket": report_pdf_bucket,
                        "report_pdf_path": report_pdf_path,
                        "report_html_url": report_html_url,
                    },
                ).scalar_one()
            )

    return {
        "result_id": result_id,
        "candidate_id": candidate_id,
        "drive_id": drive_id,
        "attempt_id": attempt_id,
        "report_json_bucket": report_json_bucket,
        "report_json_path": report_json_path,
        "report_pdf_bucket": report_pdf_bucket,
        "report_pdf_path": report_pdf_path,
        "report_html_url": report_html_url,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "report-generation"}


@app.post("/v1/reports/generate")
def generate_report_endpoint(
    payload: dict[str, Any],
    x_report_service_token: str | None = Header(default=None, alias="x-report-service-token"),
):
    required_token = (os.getenv("REPORT_SERVICE_AUTH_TOKEN") or "").strip()
    if required_token and str(x_report_service_token or "").strip() != required_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid report service token")

    email = str(payload.get("email") or "").strip().lower()
    launch_code = str(payload.get("launch_code") or "").strip().upper()
    if not email or not launch_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email and launch_code are required")

    reports_dir = PROJECT_ROOT / "Report_Generation" / "generated_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_email = _safe_path_component(email, "candidate")
    safe_launch = _safe_path_component(launch_code, "launch")

    json_filename = f"report_{safe_email}_{safe_launch}_{timestamp}.json"
    json_path = reports_dir / json_filename

    try:
        report = generate_candidate_exam_report(
            email=email,
            launch_code=launch_code,
            output_path=str(json_path),
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Report generation failed: {exc}")

    json_bucket = (os.getenv("REPORT_JSON_BUCKET") or "report-json").strip()
    bucket = (os.getenv("CANDIDATE_REPORTS_BUCKET") or "candidate-reports").strip()
    json_storage_path = f"reports/{safe_email}/{safe_launch}_{timestamp}.json"
    pdf_path = f"reports/{safe_email}/{safe_launch}_{timestamp}.pdf"

    json_bytes = json.dumps(report, ensure_ascii=False, default=_json_default).encode("utf-8")
    _supabase_upload(
        bucket=json_bucket,
        object_path=json_storage_path,
        payload=json_bytes,
        content_type="application/json",
    )

    user_details = report.get("user_details") or {}
    exam_details = report.get("exam_details") or {}
    pdf_bytes = _build_dummy_pdf(
        [
            "Candidate Exam Report",
            f"Candidate: {user_details.get('full_name') or email}",
            f"Email: {user_details.get('email') or email}",
            f"Exam: {exam_details.get('title') or exam_details.get('exam_name') or 'N/A'}",
            f"Launch Code: {launch_code}",
        ]
    )

    _supabase_upload(
        bucket=bucket,
        object_path=pdf_path,
        payload=pdf_bytes,
        content_type="application/pdf",
    )

    report_html_url = _build_persistent_render_url(
        report_json_bucket=json_bucket,
        report_json_path=json_storage_path,
    )
    if not report_html_url:
        # Fallback to legacy direct render call behavior if persistent URL cannot be built.
        report_html_url = _call_rendering_service(report)

    row = _upsert_exam_result_report(
        report=report,
        report_json_bucket=json_bucket,
        report_json_path=json_storage_path,
        report_pdf_bucket=bucket,
        report_pdf_path=pdf_path,
        report_html_url=report_html_url,
    )

    return {
        "status": "ok",
        "result_id": row["result_id"],
        "candidate_id": row["candidate_id"],
        "drive_id": row["drive_id"],
        "attempt_id": row["attempt_id"],
        "report_json_bucket": row["report_json_bucket"],
        "report_json_path": row["report_json_path"],
        "report_pdf_bucket": row["report_pdf_bucket"],
        "report_pdf_path": row["report_pdf_path"],
        "report_html_url": report_html_url,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("Report_Generation.server:app", host="0.0.0.0", port=int(os.getenv("REPORT_SERVER_PORT", "8010")))
