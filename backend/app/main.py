import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure UTF-8 console output on Windows to prevent UnicodeEncodeError on 'ε'
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.api.v1.router import api_v1_router
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AutoVerify - Automated Auditing Platform for Automata Transformations",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router)

    @app.get("/")
    def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "online",
        }

    @app.get("/health")
    def health():
        return {
            "status": "healthy",
            "version": settings.app_version,
        }

    return app


app = create_app()
