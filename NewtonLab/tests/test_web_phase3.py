"""Pruebas de exportación y validación que no requieren PostgreSQL."""
import csv
from io import BytesIO, StringIO
import sys
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy.exc import OperationalError

from backend.app.main import app
from backend.app.database import database_engine, get_engine, get_session
from backend.app.api.routes.history import owner_hash
from backend.app import runner

client = TestClient(app)
PARAMETERS = {"expression": "x**3 - x - 2", "initial_guess": 1.5, "tolerance": 1e-6, "max_iterations": 100}


def test_postgres_required_and_unconfigured_history(monkeypatch):
    with pytest.raises(ValueError, match="PostgreSQL"):
        database_engine("sqlite://")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_engine.cache_clear()
    response = client.get("/api/history", headers={"X-History-Token": "a" * 64})
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/health").status_code == 200
    get_engine.cache_clear()


def test_database_error_is_not_exposed():
    def unavailable():
        raise OperationalError("private SQL", {}, Exception("password=secret"))
    app.dependency_overrides[get_session] = unavailable
    try:
        response = client.get("/api/history", headers={"X-History-Token": "a" * 64})
        assert response.status_code == 503
        assert "secret" not in response.text and "private SQL" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_token_is_hashed():
    assert len(owner_hash("a" * 64)) == 64
    assert owner_hash("a" * 64) != "a" * 64
    assert owner_hash("b" * 64) != owner_hash("a" * 64)


def test_csv_download_has_only_numeric_cells():
    response = client.post("/api/exports/csv", json=PARAMETERS)
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert 'attachment; filename="newtonlab.csv"' == response.headers["content-disposition"]
    rows = list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))
    assert len(rows[0]) == 6
    assert rows[0][0] == "Iteración"
    for row in rows[1:]:
        assert len(row) == 6
        for cell in row:
            float(cell)
    assert float(rows[-1][4]) == pytest.approx(1.5213797068)


@pytest.mark.parametrize("parameters", [PARAMETERS, {**PARAMETERS, "expression": "x**3-2*x+2", "initial_guess": 0, "max_iterations": 120}])
def test_pdf_contains_report_graph_and_complete_table(parameters):
    response = client.post("/api/exports/pdf", json=parameters)
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() for page in reader.pages)
    for label in ("NewtonLab", "Generado:", parameters["expression"], "Residuo absoluto", "Error final", "x_(n+1)"):
        assert label in text
    assert len(reader.pages[0].images) == 1
    assert len(reader.pages) >= 2
    if parameters["max_iterations"] == 120:
        assert len(reader.pages) >= 4
        assert "120" in reader.pages[-1].extract_text()
        assert "No se obtuvo una raíz" in text
    assert "PySide6" not in sys.modules


@pytest.mark.parametrize("body", [{**PARAMETERS, "expression": "__import__('os')"}, {**PARAMETERS, "tolerance": 0}, {**PARAMETERS, "root": 42}])
def test_exports_cannot_bypass_validation(body):
    assert client.post("/api/exports/pdf", json=body).status_code == 422


def test_csv_without_iterations_and_invalid_format():
    assert client.post("/api/exports/csv", json={**PARAMETERS, "expression": "x**2", "initial_guess": 0}).status_code == 422
    assert client.post("/api/exports/html", json=PARAMETERS).status_code == 422


def test_export_timeout_cleans_temporary_files(monkeypatch):
    directories = []
    def timeout(command, **kwargs):
        directory = Path(command[-1])
        directories.append(directory)
        (directory / "partial.pdf").write_bytes(b"partial")
        raise subprocess.TimeoutExpired(command, 10)
    monkeypatch.setattr(runner.subprocess, "run", timeout)
    assert client.post("/api/exports/pdf", json=PARAMETERS).status_code == 408
    assert directories and not directories[0].exists()
