"""Configuración local opcional; el entorno del hosting siempre tiene prioridad."""
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def load_environment() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def cors_origins() -> list[str]:
    origins: list[str] = []
    for value in os.environ.get("CORS_ORIGINS", "").split(","):
        origin = value.strip().rstrip("/")
        if not origin:
            continue
        url = urlsplit(origin)
        if (url.scheme not in ("http", "https") or not url.hostname or "*" in origin
                or url.username or url.password or url.path or url.query or url.fragment):
            raise ValueError("CORS_ORIGINS requiere orígenes HTTP/HTTPS explícitos, sin rutas ni comodines.")
        if origin not in origins:
            origins.append(origin)
    return origins


def configure_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware, allow_origins=cors_origins(), allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-History-Token"],
        expose_headers=["Content-Disposition"], max_age=600,
    )


load_environment()
