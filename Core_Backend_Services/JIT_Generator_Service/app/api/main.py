from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(
    title="JIT Adaptive Assessment Engine",
    description=(
        "Just-In-Time question generator that adapts difficulty in real-time "
        "based on candidate performance, response time, and confidence."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "service": "JIT Adaptive Assessment Engine",
        "version": "1.0.0",
        "docs":    "/docs",
        "endpoints": {
            "start_session": "POST /api/v1/jit/session/start",
            "submit_answer": "POST /api/v1/jit/session/answer",
            "status":        "GET  /api/v1/jit/session/{id}/status",
            "report":        "GET  /api/v1/jit/session/{id}/report",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8001, reload=True)