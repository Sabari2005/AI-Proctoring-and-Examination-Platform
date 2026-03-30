from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.coding_routes import coding_router
from app.api.qtype_routes import qtype_router



app = FastAPI(
    title="LLM Question Morphing API",
    description="Agentic LangGraph pipeline for morphing exam questions",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(coding_router)
app.include_router(qtype_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=True)