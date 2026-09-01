"""Application configuration settings."""

from __future__ import annotations

import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AutoVerify API"
    app_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS configuration
    cors_origins: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://autoverify.vercel.app",
    ]
    cors_origin_regex: str = r"https://.*\.vercel\.app"

    # AI configuration
    autoverify_ai_api_key: str = ""
    gemini_api_key: str = ""

    # Database
    database_url: str = "sqlite:///./autoverify.db"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.strip().startswith("[") and v.strip().endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("port", mode="before")
    @classmethod
    def parse_port(cls, v: Union[int, str]) -> int:
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                return 8000
        return v

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
