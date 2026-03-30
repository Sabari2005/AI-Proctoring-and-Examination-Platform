from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .parser import parse_report_input
from .llm_summary import generate_candidate_summary

app = FastAPI(
    title="Exam Report Generation Agent",
    description="Generates HTML preview data from JIT and LLM-morphed exam data",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate-report")
async def generate_report(payload: dict):
    """Accept raw exam JSON and return parsed data + AI summary (HTML-only mode)."""
    try:
        report_data = parse_report_input(payload)
        report_data["ai_summary"] = await generate_candidate_summary(report_data)
        return JSONResponse(content=report_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-report/preview")
async def preview_report_data(payload: dict):
    """Returns the parsed report data structure without generating PDF (for debugging)."""
    report_data = parse_report_input(payload)
    return JSONResponse(content=report_data)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "exam-report-agent"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
