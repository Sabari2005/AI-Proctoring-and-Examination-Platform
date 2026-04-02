# JIT Generator Service
Small, standalone adaptive assessment service that generates questions, evaluates answers, adjusts difficulty in real time, and produces final skill reports.

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
The JIT (Just-In-Time) Generator Service is an adaptive assessment backend that:
- starts a candidate session for a section topic,
- generates one question at a time using LLM prompts,
- evaluates each answer per question type,
- updates candidate ability (theta) and next difficulty,
- switches to the next best sub-topic,
- returns a final report when the session is complete.

It supports these question types:
- `mcq`
- `fib`
- `short`
- `msq`
- `numerical`
- `long`
- `coding`
- `mixed` (rotating sequence)

## About the Service
This service is implemented as a FastAPI application with an adaptive engine inspired by IRT-style progression. It uses:
- Groq as primary LLM provider,
- Gemini as fallback provider,
- in-memory session state for active attempts,
- optional PostgreSQL persistence for session start binding and final report storage.

There are two runnable API entrypoints in this module:
- `app/api/main.py` (main API app, default port 8001)
- `server.py` (standalone compatibility server, default port 8002)

A CLI simulator (`run.py`) is also available to run full interactive sessions from terminal.

## Process Flow
1. Client calls `POST /api/v1/jit/session/start` (or standalone equivalent).
2. Service initializes `JITSessionState` with difficulty, theta, and session metadata.
3. Sub-topics are extracted from `section_topic` using LLM (fallback list on failure).
4. Question generator creates the first question based on:
   - current difficulty,
   - selected sub-topic,
   - question type (or mixed rotation),
   - recent question history for dedup hints.
5. Client submits answer to `POST /api/v1/jit/session/answer`.
6. Evaluator scores answer by type:
   - deterministic logic for objective formats,
   - LLM-assisted scoring for `short`, `long`, and `coding`.
7. Adaptive engine updates:
   - theta,
   - streak and consecutive-wrong counters,
   - sub-topic mastery,
   - next difficulty and next sub-topic.
8. If questions remain, next question is generated and returned.
9. If target count reached, report generator builds final report.
10. Final report is persisted (best effort) to DB and exposed through report endpoint.

## Architecture Diagram
```mermaid
flowchart TD
    A[Client or UI] --> B[FastAPI Routes]
    B --> C[start_session]
    B --> D[submit_answer]

    C --> E[create JITSessionState]
    E --> F[subtopic_extractor]
    F --> G[question_generator]
    G --> H[(In-memory session_store)]
    G --> I[Return first question]

    D --> H
    H --> J[evaluate_answer]
    J --> K[adaptive_engine]
    K -->|more questions| G
    K -->|complete| L[report_generator]

    G --> M[LLM Providers]
    J --> M
    L --> M

    M --> N[Groq primary]
    M --> O[Gemini fallback]

    L --> P[(PostgreSQL via jit_db_store)]
    L --> Q[Return final report]
```

## Built With
- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic
- LangChain Core
- LangChain Groq
- LangChain Google GenAI
- LangGraph
- SQLAlchemy
- psycopg2-binary
- python-dotenv
- pytest / pytest-asyncio

## Service Overview
Core folders and roles:
- `app/api/`
  - `routes.py`: API endpoints under `/api/v1/jit`
  - `jit_service.py`: orchestration layer for session lifecycle
  - `main.py`: FastAPI app setup
- `app/core/`
  - `schemas.py`: request/response/session models
  - `enums.py`: qtypes, difficulty, bloom, skill labels
  - `config.py`: environment-driven settings
  - `state.py`: graph state shape
- `app/nodes/`
  - `subtopic_extractor.py`: topic decomposition
  - `question_generator.py`: type-aware question generation and JSON recovery
  - `adaptive_engine.py`: ability update and difficulty adaptation
  - `report_generator.py`: final summary and recommendations
- `app/evaluators/`
  - `answer_evaluator.py`: multi-type scoring logic
- `app/llm/`
  - `providers.py`: Groq/Gemini invocation with fallback
  - `prompts.py`: generation/evaluation/report prompts
- `app/utils/`
  - `session_store.py`: in-memory session persistence
  - `jit_db_store.py`: optional DB persistence
  - `json_parser.py`: robust LLM JSON extraction
- `run.py`
  - terminal-based end-to-end simulation
- `server.py`
  - standalone API service with compatibility routes

## Installation
### 1. Move into service directory
```bash
cd Core_Backend_Services/JIT_Generator_Service
```

### 2. Create and activate virtual environment
```bash
python -m venv .venv
```

Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
Create `.env` and set required keys (see next section).

### 5. Run API server
Main API app:
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8001 --reload
```

Standalone server:
```bash
python server.py
```

### 6. Optional CLI simulation
```bash
python run.py --topic "Operating Systems" --questions 5 --type mixed --difficulty 2
```

## Environment Variables
Recommended `.env` keys:

```env
# LLM providers
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
# or GOOGLE_API_KEY (supported fallback alias in config)

# Model selection
DEFAULT_MODEL=llama-3.3-70b-versatile
FALLBACK_MODEL=gemini-1.5-flash

# Adaptive engine tuning
JIT_LEARNING_RATE=0.4
JIT_MAX_DIFF_JUMP=2
JIT_STREAK_THRESHOLD=3
JIT_LOCK_AFTER_WRONG=3

# Optional observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=jit-generator

# Optional DB persistence (Neon/Postgres)
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

Notes:
- `GROQ_API_KEY` is required for primary generation/evaluation.
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` is used as fallback provider.
- `DATABASE_URL` is required only if you want persistence to `jit_section_sessions`.

## Sample Request Response
### 1. Start Session
Endpoint:
- `POST /api/v1/jit/session/start`

Request:
```json
{
  "section_topic": "Operating Systems",
  "num_questions": 3,
  "question_type": "mcq",
  "start_difficulty": 2,
  "candidate_id": "student_001"
}
```

Response (example):
```json
{
  "session_id": "jit-3f90c9a4d1",
  "first_question": {
    "question_id": "jit-3f90c9a4d1-q01",
    "session_id": "jit-3f90c9a4d1",
    "question_number": 1,
    "qtype": "mcq",
    "difficulty": 2,
    "bloom_level": "understand",
    "sub_topic": "Process Management",
    "question_text": "Which scheduler is preemptive?",
    "options": [
      "A. FCFS",
      "B. Round Robin",
      "C. SJF (non-preemptive)",
      "D. FIFO"
    ],
    "correct_answers": ["B. Round Robin"],
    "expected_time_seconds": 60,
    "hints": ["Think about time slicing"]
  },
  "session_info": {
    "num_questions": 3,
    "question_type": "mcq",
    "section_topic": "Operating Systems",
    "start_difficulty": 2,
    "sub_topics": [
      "Process Management",
      "Thread Synchronization",
      "Memory Management"
    ]
  }
}
```

### 2. Submit Answer
Endpoint:
- `POST /api/v1/jit/session/answer`

Request:
```json
{
  "session_id": "jit-3f90c9a4d1",
  "question_id": "jit-3f90c9a4d1-q01",
  "question_number": 1,
  "answer": "B",
  "time_taken_seconds": 32,
  "confidence": 4,
  "language": "python"
}
```

Response while session is active (example):
```json
{
  "evaluation": {
    "question_id": "jit-3f90c9a4d1-q01",
    "status": "correct",
    "score": 1.0,
    "correctness": 1.0,
    "time_ratio": 0.533,
    "time_bonus": 1.0,
    "confidence_score": 0.75,
    "feedback": "Correct!",
    "correct_answer_reveal": ["B. Round Robin"]
  },
  "adaptive_decision": {
    "prev_theta": 2.0,
    "new_theta": 2.36,
    "theta_delta": 0.36,
    "next_difficulty": 3,
    "next_sub_topic": "Thread Synchronization",
    "next_qtype": "mcq",
    "streak": 1,
    "reason": "levelling up (theta=2.36)"
  },
  "next_question": {
    "question_id": "jit-3f90c9a4d1-q02",
    "qtype": "mcq"
  },
  "session_complete": false,
  "final_report": null
}
```

Response when session completes (example):
```json
{
  "evaluation": {
    "question_id": "jit-3f90c9a4d1-q03",
    "status": "partial",
    "score": 0.5
  },
  "adaptive_decision": {
    "prev_theta": 2.7,
    "new_theta": 2.76,
    "theta_delta": 0.06,
    "next_difficulty": 3,
    "next_sub_topic": "Memory Management",
    "next_qtype": "mcq",
    "streak": 0,
    "reason": "maintaining level (theta=2.76)"
  },
  "next_question": null,
  "session_complete": true,
  "final_report": {
    "session_id": "jit-3f90c9a4d1",
    "candidate_id": "student_001",
    "section_topic": "Operating Systems",
    "total_questions": 3,
    "correct": 2,
    "partial": 1,
    "wrong": 0,
    "accuracy": 83.3,
    "theta_final": 2.76,
    "skill_label": "Intermediate",
    "highest_bloom": "apply",
    "difficulty_trajectory": [2, 3, 3],
    "sub_topic_mastery": {
      "Process Management": 80.0,
      "Thread Synchronization": 65.0
    },
    "speed_profile": "normal",
    "strengths": ["Process Management"],
    "weaknesses": [],
    "recommendations": [
      "Practice medium-level synchronization problems.",
      "Continue with mixed question sets."
    ]
  }
}
```

## Environment Verification (Required)

You must verify this service has a valid `.env` before startup.

```powershell
Test-Path "Core_Backend_Services/JIT_Generator_Service/.env"
Select-String -Path "Core_Backend_Services/JIT_Generator_Service/.env" -Pattern "GROQ_API_KEY|GEMINI_API_KEY|DATABASE_URL"
```

If the file is missing, create it from `Core_Backend_Services/JIT_Generator_Service/.env.example` and populate real values.

## Repository Structure (Workspace Context)

```text
observe-github/
|- Core_Backend_Services/
|  |- JIT_Generator_Service/    <-- current service
|  |- LLM_Morphing_Service/
|- Web_Server/
|- Coding_Environment_Service/
|- Rendering_service/
|  |- report_agent/
|- Report_Generation_service/
|- EXE-Application/
|- observe/
```

