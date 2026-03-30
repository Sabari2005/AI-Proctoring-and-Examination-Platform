from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes import router

app = FastAPI(
    title="LLM Morphing Registration Server",
    version="1.0.0",
    description="Internal service that generates and stores candidate-specific variants",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
