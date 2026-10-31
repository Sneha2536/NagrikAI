"""
main.py: starts the backend server.

Run from the backend/ folder:
    uvicorn main:app --reload --port 8000

Then open http://localhost:8000/docs to try every endpoint in the browser.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ai.llm import LLMError
from config import ROOT, settings
from routes import ask, eligibility, explain, policies

app = FastAPI(title="NagrikAI API", version="1.0.0")

# Lets the React app (on another port) call this server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(policies.router)
app.include_router(explain.router)
app.include_router(ask.router)
app.include_router(eligibility.router)


@app.exception_handler(LLMError)
async def llm_error_handler(_: Request, exc: LLMError):
    # Friendly message for the frontend instead of a crash.
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/api/health")
def health():
    configured = bool(
        settings.ANTHROPIC_API_KEY if settings.LLM_PROVIDER == "anthropic" else settings.GEMINI_API_KEY
    )
    return {"status": "ok", "build": settings.BUILD, "llm_provider": settings.LLM_PROVIDER, "llm_configured": configured}


# ---- Production: serve the built React app from this same server (one URL, no CORS) ----
# Build it with `npm run build` inside frontend/. In local development this folder does not
# exist (Vite serves the frontend on port 5173), so nothing below runs.
DIST = ROOT / "frontend" / "dist"
if (DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        target = (DIST / path).resolve()
        if path and target.is_file() and DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(DIST / "index.html")   # React Router pages (/explorer, /explainer...)
