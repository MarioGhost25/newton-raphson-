"""Integración REAL PostgreSQL. Se omite explícitamente sin TEST_DATABASE_URL.

Usa una base de pruebas dedicada y crea/elimina únicamente un esquema aleatorio.
Nunca se conecta a DATABASE_URL ni sustituye PostgreSQL por SQLite.
"""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from backend.app.database import database_engine, get_session
from backend.app.main import app
from backend.app.repositories.history import Base, HistoryRecord


@pytest.fixture(scope="module")
def postgres_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("PostgreSQL no disponible: configurá TEST_DATABASE_URL con una base aislada.")
    main_url = os.environ.get("DATABASE_URL")
    if main_url and make_url(url).database == make_url(main_url).database:
        pytest.fail("TEST_DATABASE_URL debe apuntar a una base de pruebas dedicada.")
    engine = database_engine(url)
    schema = "newtonlab_test_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    isolated = engine.execution_options(schema_translate_map={None: schema})
    try:
        Base.metadata.create_all(isolated)
        yield isolated
    finally:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()


@pytest.fixture
def client(postgres_engine):
    def session():
        with Session(postgres_engine, expire_on_commit=False) as value:
            yield value
    app.dependency_overrides[get_session] = session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def token():
    return {"X-History-Token": uuid4().hex + uuid4().hex}


def save(client, headers, expression="x**2-2", request_id=None):
    body = {"request_id": str(request_id or uuid4()), "parameters": {"expression": expression, "initial_guess": 1.5, "tolerance": 1e-6, "max_iterations": 100}}
    response = client.post("/api/history", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json(), body


def test_persistence_and_idempotence(client, postgres_engine):
    headers = token()
    saved, body = save(client, headers)
    assert client.post("/api/history", headers=headers, json=body).json()["id"] == saved["id"]
    assert len(client.get("/api/history", headers=headers).json()["items"]) == 1
    with Session(postgres_engine) as session:
        record = session.scalar(select(HistoryRecord).where(HistoryRecord.expression == "x**2-2"))
        assert record is not None
        assert "curve" not in record.summary and "iterations" not in record.summary
        assert "derivative" in record.summary
        assert record.owner_hash != headers["X-History-Token"]
    body["parameters"]["expression"] = "x**2-3"
    assert client.post("/api/history", headers=headers, json=body).status_code == 409


def test_pagination_search_and_limits(client):
    headers = token()
    for expression in ("x**2-2", "cos(x)-x", "x**3-x-2"):
        save(client, headers, expression)
    first = client.get("/api/history?limit=2", headers=headers).json()
    second = client.get("/api/history?limit=2&offset=2", headers=headers).json()
    assert first["has_more"] and not second["has_more"]
    assert len({item["id"] for item in first["items"] + second["items"]}) == 3
    assert len(client.get("/api/history?q=cos", headers=headers).json()["items"]) == 1
    assert client.get("/api/history", params={"q": "%"}, headers=headers).json()["items"] == []
    assert client.get("/api/history?limit=51", headers=headers).status_code == 422


def test_isolation_restore_and_deletion(client):
    a, b = token(), token()
    saved, _ = save(client, a)
    path = "/api/history/" + saved["id"]
    assert client.get("/api/history", headers=b).json()["items"] == []
    assert client.get(path, headers=b).status_code == 404
    assert client.delete(path, headers=b).status_code == 404
    restored = client.get(path, headers=a).json()
    assert restored["result"]["root"] == pytest.approx(2 ** .5)
    assert restored["result"]["iterations"] and len(restored["result"]["curve"]["x"]) == 401
    assert client.delete("/api/history", headers=b).status_code == 204
    assert client.get(path, headers=a).status_code == 200
    assert client.delete(path, headers=a).status_code == 204
    assert client.get(path, headers=a).status_code == 404
    save(client, a)
    save(client, b)
    assert client.delete("/api/history", headers=a).status_code == 204
    assert client.get("/api/history", headers=a).json()["items"] == []
    assert len(client.get("/api/history", headers=b).json()["items"]) == 1


def test_missing_invalid_token_and_untrusted_results(client):
    assert client.get("/api/history").status_code == 422
    assert client.get("/api/history", headers={"X-History-Token": "short"}).status_code == 422
    assert client.post("/api/history", headers=token(), json={"request_id": str(uuid4()), "parameters": {"expression": "x", "root": 42}}).status_code == 422
