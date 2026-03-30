"""Compatibility wrapper for the unified FastAPI renderer.

Use preview_server.py for both JIT and LLM previews.
"""

from preview_server import app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("preview_server:app", host="127.0.0.1", port=5050, reload=False)
