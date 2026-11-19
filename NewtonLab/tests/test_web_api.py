import json
import subprocess

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app import runner

client = TestClient(app)
URL = "/api/calculations/newton-raphson"


def post(**kwargs):
    return client.post(URL, json={"expression": "x**3 - x - 2", **kwargs})


def assert_json(response):
    json.dumps(response.json(), allow_nan=False)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok", "service": "NewtonLab API"}


def test_calculation_and_plot_contract():
    response = post()
    assert response.status_code == 200
    assert_json(response)
    data = response.json()
    assert data["converged"]
    assert data["root"] == pytest.approx(1.5213797068)
    assert data["derivative"] == "3*x**2 - 1"
    assert data["final_error"] <= 1e-6 and data["final_residual"] <= 1e-6
    assert data["iteration_count"] == len(data["iterations"])
    for step in data["iterations"]:
        assert step["next_x"] == pytest.approx(step["x"] - step["fx"] / step["derivative"])
    assert len(data["curve"]["x"]) == len(data["curve"]["y"]) == 401


@pytest.mark.parametrize("expression", ["x +", "y", "__import__('os')", "x.__class__", "sin(x,x)", "9**9**9", "1e309", "x" * 513, "+".join(["x"] * 70)])
def test_invalid_expressions(expression):
    response = post(expression=expression)
    assert response.status_code == 422
    assert_json(response)


@pytest.mark.parametrize("kwargs", [{"tolerance": 0}, {"tolerance": 1e-20}, {"max_iterations": 201}, {"max_iterations": True}, {"initial_guess": 1e13}, {"expression": " "}, {"unexpected": 1}])
def test_invalid_parameters(kwargs):
    assert post(**kwargs).status_code == 422


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_input_has_valid_error_json(value):
    response = client.post(URL, content='{"expression":"x","initial_guess":' + value + '}', headers={"content-type": "application/json"})
    assert response.status_code == 422
    assert_json(response)


@pytest.mark.parametrize("expression, initial, status", [
    ("x**3-2*x+2", 0, "Sin convergencia"),
    ("x**2+1", 0, "Derivada nula o casi nula"),
    ("log(x)", -1, "Error de dominio"),
    ("1/x", 0, "Valor no finito"),
    ("exp(x)", 1000, "Valor no finito"),
])
def test_mathematical_failure_is_a_result(expression, initial, status):
    response = post(expression=expression, initial_guess=initial, max_iterations=8)
    assert response.status_code == 200
    assert_json(response)
    data = response.json()
    assert not data["converged"] and data["root"] is None
    assert data["status"] == status


def test_exact_root_and_discontinuous_curve():
    data = post(expression="x**2", initial_guess=0).json()
    assert data["converged"] and data["root"] == 0
    assert data["iterations"] == [] and data["final_error"] is None
    data = post(expression="1/x", initial_guess=0).json()
    assert None in data["curve"]["y"]


def test_body_limit():
    assert client.post(URL, content=b" " * 8193).status_code == 413


def test_real_process_timeout_and_recovery(monkeypatch):
    monkeypatch.setattr(runner, "TIMEOUT_SECONDS", 0.001)
    assert post().status_code == 408
    monkeypatch.setattr(runner, "TIMEOUT_SECONDS", 10)
    assert post().status_code == 200


def test_capacity_and_internal_failure(monkeypatch):
    runner.SLOTS.acquire()
    runner.SLOTS.acquire()
    try:
        assert post().status_code == 503
        assert client.get("/api/health").status_code == 200
    finally:
        runner.SLOTS.release()
        runner.SLOTS.release()
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 1, "", "private traceback"))
    response = post()
    assert response.status_code == 500
    assert "private" not in response.text


@pytest.mark.parametrize("expression", ["x² - 0.5", "x^3 - x - 2", "2x³ + 6x² - 8x + 2"])
def test_natural_expression_api(expression):
    response = post(expression=expression)
    assert response.status_code == 200
    data = response.json()
    assert data["converged"]
    for step in data["iterations"]:
        assert step["absolute_error"] == abs(step["next_x"] - step["x"])
