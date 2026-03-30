# Rendering Service

FastAPI-based report rendering and analysis service for adaptive JIT and LLM-morphed exam attempts, with HTML report generation, AI summary output, and proctoring evidence pagination.

## Table of Contents

- [Overview](#overview)
- [About the Service](#about-the-service)
- [Process Flow](#process-flow)
- [Architecture Diagram](#architecture-diagram)
- [Built With](#built-with)
- [Service Overview](#service-overview)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Sample Request Response](#sample-request-response)

## Overview

The Rendering Service in this repository is implemented under `report_agent` and currently exposes two complementary API surfaces:

- A parsing and summary API (`app/main.py`) that normalizes raw exam payloads and generates AI hiring summaries.
- A unified HTML rendering API (`report_agent/Server.py`) that builds full multi-page report views and serves evidence images in paginated batches.

It supports both assessment modes:

- JIT (adaptive questioning)
- Morphing (LLM-morphed questions)

## About the Service

This service transforms raw exam attempt payloads into a standardized internal report model and then renders a browser/PDF-ready HTML report template.

Core responsibilities include:

- Candidate, exam, attempt, sections, and question normalization.
- Proctoring alert and evidence-frame grouping by warning folder.
- AI summary generation (Groq API with deterministic fallback summary logic).
- Dynamic template selection (`report.html` for JIT and `llm_report.html` for morphing).
- Hybrid evidence loading via paginated endpoints to avoid oversized HTML payloads.

## Process Flow

1. Client submits raw exam JSON.
2. Parser normalizes all entities into a single `report_data` schema.
3. AI summary is generated using Groq; if unavailable, rule-based fallback is used.
4. Renderer chooses template based on mode/question mix.
5. HTML is generated with Jinja2 and stored in in-memory report cache.
6. Client opens rendered report URL.
7. Proctoring evidence images are fetched lazily in pages from `/reports/{report_id}/evidence`.

## Architecture Diagram

```mermaid
flowchart TD
    A[Client or Admin UI] --> B[FastAPI Endpoint]
    B --> C[Parser\nparse_report_input]
    C --> D[Normalized report_data]
    D --> E[AI Summary\nGroq or Fallback]
    E --> F[Template Selector\nJIT or Morphing]
    F --> G[Jinja2 HTML Render]
    G --> H[In-Memory REPORT_STORE]
    H --> I[/reports/{report_id}]
    H --> J[/reports/{report_id}/evidence]
    J --> K[Signed URL refresh\nSupabase storage]
```

## Built With

- FastAPI
- Uvicorn
- Jinja2
- Pydantic
- HTTPX
- Pillow
- Python Dotenv

## Service Overview

### Main modules

- `report_agent/app/parser.py`
  - Normalizes candidate, exam, attempt, sections, question sets, and proctoring data.
  - Supports both raw alert objects and artifact-only evidence inputs.

- `report_agent/app/llm_summary.py`
  - Generates structured summary JSON with keys like `overview`, `strengths`, `weaknesses`, `recommendation`, `verdict`.
  - Uses Groq Chat Completions API with fallback rule engine when API key/errors occur.

- `report_agent/app/html_image_utils.py`
  - Fetches/embeds image data URIs for preview mode.
  - Refreshes Supabase signed evidence URLs.

- `report_agent/app/main.py`
  - Exposes parser + summary API for JSON response workflows.

- `report_agent/Server.py`
  - Unified report renderer.
  - Exposes render, preview, report retrieval, and evidence pagination endpoints.

### Key endpoints

From `app/main.py`:

- `POST /generate-report`
- `POST /generate-report/preview`
- `GET /health`

From `Server.py`:

- `POST /render`
- `GET /reports/{report_id}`
- `GET /reports/{report_id}/evidence`
- `GET /preview`
- `GET /preview/from-json-url`
- `GET /preview/from-storage`
- `GET /static/report.css`
- `GET /health`

## Installation

### Prerequisites

- Python 3.11+ (3.12 also used in this workspace)
- pip

### Setup

```bash
cd Rendering_service/report_agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Run options

Parser + summary API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Unified HTML renderer:

```bash
uvicorn Server:app --host 127.0.0.1 --port 5050 --reload
```

## Environment Variables

Set these in `Rendering_service/report_agent/.env`.

- `GROQ_API_KEY`
  - Required for live AI summary generation.

- `GROQ_MODEL`
  - Optional; defaults to `llama-3.3-70b-versatile`.

- `SUPABASE_URL`
  - Required for storage object access and signed URL refresh.

- `SUPABASE_SERVICE_ROLE_KEY`
  - Required for secure signed URL creation and storage reads.

- `SUPABASE_ANON_KEY`
  - Optional fallback for signed URL refresh path.

- `REPORT_PAGES_BUCKET`
  - Optional bucket naming for report page artifacts.

- `EVIDENCE_SIGNED_URL_EXPIRES_IN`
  - Optional signed URL expiry seconds.

## Sample Request Response

### Request

`POST /render`

```json
{
  "report_json": {
    "exam_mode": {
      "generation_mode": "jit"
    },
    "user_details": {
      "candidate_id": "CAND-101",
      "full_name": "Alex Doe",
      "email": "alex@example.com"
    },
    "exam_details": {
      "drive_id": "DRV-2201",
      "title": "Python Backend Assessment",
      "max_marks": 100,
      "company_name": "Acme Corp"
    },
    "attempt": {
      "selected_attempt": {
        "attempt_id": 3,
        "computed_total_marks": 68,
        "status": "submitted"
      }
    },
    "sections": [],
    "questions": {},
    "proctoring": {
      "alerts": [],
      "evidence_images": []
    }
  },
  "include_preview_frame": false
}
```

### Response

```json
{
  "status": "ok",
  "report_id": "6f5c13f8e7ca488dbf2f3ec2d6a97f31",
  "mode": "jit",
  "template": "report.html",
  "html_url": "/reports/6f5c13f8e7ca488dbf2f3ec2d6a97f31",
  "report_html_url": null,
  "evidence_manifest_url": null,
  "evidence_api": "/reports/6f5c13f8e7ca488dbf2f3ec2d6a97f31/evidence"
}
```

---

Implementation note:
- `report_agent/Server.py` and `report_agent/preview_server_llm.py` reference `preview_server:app` at runtime. In the current folder snapshot, the active unified app is defined in `Server.py`, so production startup should use `uvicorn Server:app ...` unless a separate `preview_server.py` is added.

## Environment Verification (Required)

You must verify this service has a valid `.env` before startup.

```powershell
Test-Path "Rendering_service/report_agent/.env"
Select-String -Path "Rendering_service/report_agent/.env" -Pattern "GROQ_API_KEY|SUPABASE_URL|SUPABASE_SERVICE_ROLE_KEY"
```

If the file is missing, create it from `Rendering_service/report_agent/.env.example` and populate real values.

## Repository Structure (Workspace Context)

```text
virtusa-github/
|- Rendering_service/
|  |- report_agent/             <-- current service runtime folder
|- Web_Server/
|- Coding_Environment_Service/
|- Core_Backend_Services/
|  |- JIT_Generator_Service/
|  |- LLM_Morphing_Service/
|- Report_Generation_service/
|- EXE-Application/
|- observe/
```
