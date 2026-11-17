import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.app.settings import configure_cors, cors_origins, load_environment
from backend.app.database import database_engine


def test_environment_has_priority_over_local_file(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.invalid/hosting")
    load_environment()
    assert os.environ["DATABASE_URL"] == "postgresql://example.invalid/hosting"


@pytest.mark.parametrize("value", ["*", "https://*.example.com", "https://example.com/path", "https://user:password@example.com", "https://example.com?query=1"])
def test_cors_requires_explicit_origins(monkeypatch, value):
    monkeypatch.setenv("CORS_ORIGINS", value)
    with pytest.raises(ValueError):
        cors_origins()


def test_cors_history_token_preflight_and_download(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://frontend.example.com,http://127.0.0.1:5173")
    app = FastAPI()
    configure_cors(app)
    @app.get("/api/health")
    def health():
        return {"status": "ok"}
    with TestClient(app) as client:
        headers = {"Origin": "https://frontend.example.com", "Access-Control-Request-Method": "POST",
                   "Access-Control-Request-Headers": "content-type,x-history-token"}
        response = client.options("/api/history", headers=headers)
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == headers["Origin"]
        assert "access-control-allow-credentials" not in response.headers
        assert "x-history-token" in response.headers["access-control-allow-headers"].lower()
        response = client.options("/api/history", headers={**headers, "Origin": "https://untrusted.example"})
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers
        response = client.get("/api/health", headers={"Origin": headers["Origin"]})
        assert response.headers["access-control-expose-headers"] == "Content-Disposition"


def test_remote_database_tls_and_pool_configuration():
    engine = database_engine("postgres://example@db.example.invalid/application?sslmode=require")
    try:
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.url.query["sslmode"] == "require"
        assert engine.pool.size() == 5
    finally:
        engine.dispose()
