### **LLM Morphing Service** - A multi-strategy question transformation engine for MCQ, coding, and typed assessment formats

## Table of contents

- [Overview](#overview)
- [About LLM Morphing Service](#about-llm-morphing-service)
- [Process flow](#process-flow)
- [Architecture Diagram](#architecture-diagram)
- [Installation](#installation)
- [Service Overview](#service-overview)
- [API service](#api-service)
- [Author](#author)

## Overview

LLM Morphing Service generates high-quality variants of assessment questions using an agentic LangGraph pipeline.
It supports:
- Generic MCQ morphing
- Question-type specific morphing (FIB, Short, MSQ, Numerical, Long)
- Coding question morphing with test-case-aware transformations
- Internal registration-time bulk processing and persistence for candidate-specific variants

## About LLM Morphing Service

- The service is designed to produce semantically aligned but pedagogically varied question variants.
- It combines analysis, strategy routing, validation, retry logic, and post-processing.
- It uses Groq as the primary LLM and Gemini as fallback when configured.
- It provides both direct morphing APIs and an internal processing API tied to registration workflows.

## Process flow

### 1. Input acceptance
- Payload is received via FastAPI endpoints.
- Pydantic schemas validate structure and constraints.

### 2. Analyze and calibrate
- The graph analyzes concept, difficulty, and Bloom-level context.
- Difficulty target and strategy context are prepared.

### 3. Strategy fan-out
- LangGraph router dispatches selected morph strategies in parallel.
- Strategy-specific nodes generate candidate variants.

### 4. Validate and retry
- Semantic similarity, answer integrity, difficulty drift, and duplication are checked.
- Failed variants trigger retry until max retry limit.

### 5. Post-process output
- Best valid variants are retained and deduplicated.
- Final response includes trace id, lineage, and variant metadata.

### 6. Internal registration processing
- For registered candidates and exams, source questions are loaded from DB.
- Question payloads are mapped to the proper input schema per type.
- Variants are generated and saved in `llm_question_variants` with job tracking.

## Architecture Diagram

```mermaid
flowchart LR
    A[Client / Orchestrator] --> B[FastAPI API Layer]
    B --> C[MCQ Graph]
    B --> D[QType Graph]
    B --> E[Coding Graph]

    C --> F[Analyze]
    D --> F
    E --> F

    F --> G[Calibrate]
    G --> H[Route Strategies]
    H --> I[Morph Nodes Parallel]
    I --> J[Validate]
    J -->|Pass| K[Post Process]
    J -->|Fail + retries| H

    K --> B
    B --> A

    L[Groq LLM] -. primary .-> I
    M[Gemini LLM] -. fallback .-> I
    N[SQL Database] <--> O[Internal Registration Server]
    O --> D
    O --> E
    O --> C
```

## Built with

- Python
- FastAPI
- LangGraph
- LangChain Core
- LangChain Groq
- LangChain Google GenAI
- Pydantic
- SQLAlchemy
- SentenceTransformers
- Uvicorn
- Pytest

## Service Overview

### Public morphing API surface
- `POST /api/v1/morph` for MCQ pipeline
- `POST /api/v1/coding/morph` for coding pipeline
- `POST /api/v1/fib/morph`
- `POST /api/v1/short/morph`
- `POST /api/v1/msq/morph`
- `POST /api/v1/numerical/morph`
- `POST /api/v1/long/morph`
- `GET /api/v1/health`
- `GET /api/v1/coding/strategies`
- `GET /api/v1/strategies`

### Internal registration server API
- `GET /internal/v1/health`
- `POST /internal/v1/registrations/process`

### Key strategy groups
- MCQ: `rephrase`, `contextual`, `distractor`, `structural`, `difficulty`
- Coding: `code_rephrase`, `code_contextual`, `code_difficulty`, `code_constraint`, `code_tcgen`, `code_tcscale`
- QType families are handled with type-specific strategy enums.

## Installation

### Prerequirements
- Python 3.11+
- Access keys for LLM providers
- Database reachable for internal registration server

### Setup steps

```bash
git clone <your-repo-url>
cd Core_Backend_Services/LLM_Morphing_Service
```

```bash
pip install -r requirements.txt
```

### Environment variables
Create `.env` in this folder with at least:

```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key_optional
DEFAULT_MODEL=llama-3.3-70b-versatile
FALLBACK_MODEL=gemini-1.5-flash
MAX_RETRIES=3
MIN_SEMANTIC_SCORE=0.82
DATABASE_URL=postgresql://user:pass@host/db
MORPHING_SERVICE_TOKEN=optional_internal_token
```

### Run API server (public morphing endpoints)

```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run internal registration server

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8001 --reload
```

### Optional CLI run

```bash
python run.py --strategy rephrase
```

## API service

The service exposes FastAPI endpoints for direct question morphing and internal exam registration-time processing.

### Sample request (MCQ)

```json
{
  "section": "Aptitude",
  "question": "A train travels 60 km in 1 hour. How long will it take to travel 210 km at the same speed?",
  "options": ["2.5 hours", "3.5 hours", "4 hours", "3 hours"],
  "correct_answer": "3.5 hours",
  "morph_config": {
    "strategies": ["rephrase", "contextual"],
    "variant_count": 2
  }
}
```

### Sample request (internal processing)

```json
{
  "candidate_id": 101,
  "exam_id": 55
}
```

### Run tests

```bash
pytest -v
```

```bash
pytest -v -m "not integration"
```

## Author

- NYD Hackathon Team - LLM Morphing Service Contributors

## Environment Verification (Required)

You must verify this service has a valid `.env` before startup.

```powershell
Test-Path "Core_Backend_Services/LLM_Morphing_Service/.env"
Select-String -Path "Core_Backend_Services/LLM_Morphing_Service/.env" -Pattern "GROQ_API_KEY|GEMINI_API_KEY|DATABASE_URL|MORPHING_SERVICE_TOKEN"
```

If the file is missing, create it from `Core_Backend_Services/LLM_Morphing_Service/.env.example` and populate real values.

## Repository Structure (Workspace Context)

```text
observe-github/
|- Core_Backend_Services/
|  |- JIT_Generator_Service/
|  |- LLM_Morphing_Service/     <-- current service
|- Web_Server/
|- Coding_Environment_Service/
|- Rendering_service/
|  |- report_agent/
|- Report_Generation_service/
|- EXE-Application/
|- observe/
```

