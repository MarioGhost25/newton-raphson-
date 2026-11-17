"""Tiempo máximo real: al vencer se termina el proceso, no sólo la espera."""
import json
import os
from pathlib import Path
import subprocess
import sys
import base64
from typing import Any, Literal
from contextlib import nullcontext
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore

from fastapi import HTTPException
from . import settings  # La configuración también aplica al worker/CLI.
from .schemas.calculations import CalculationRequest, CalculationResponse

TIMEOUT_SECONDS = float(os.environ.get("NEWTONLAB_CALCULATION_TIMEOUT", "10"))
if not 0 < TIMEOUT_SECONDS <= 30:
    raise ValueError("NEWTONLAB_CALCULATION_TIMEOUT debe estar entre 0 y 30 segundos.")
SLOTS = BoundedSemaphore(2)


def run_worker(request: CalculationRequest, mode: str = "calculate") -> dict[str, Any]:
    if not SLOTS.acquire(blocking=False):
        raise HTTPException(503, "Servidor ocupado. Intentá nuevamente.")
    try:
        # El padre conserva la limpieza aunque el worker se termine por timeout.
        with TemporaryDirectory(prefix="newtonlab-export-") if mode in ("pdf", "csv") else nullcontext(None) as directory:
            command = [sys.executable, "-m", "backend.app.worker", mode]
            if directory is not None:
                command.append(directory)
            completed = subprocess.run(
                command, input=request.model_dump_json(), capture_output=True, text=True,
                encoding="utf-8", cwd=Path(__file__).resolve().parents[2],
                timeout=TIMEOUT_SECONDS,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        if completed.returncode:
            raise HTTPException(500, "No se pudo completar el cálculo.")
        payload = json.loads(completed.stdout)
        if "invalid_expression" in payload:
            raise HTTPException(422, payload["invalid_expression"])
        if "invalid_export" in payload:
            raise HTTPException(422, payload["invalid_export"])
        if "error" in payload:
            raise HTTPException(500, "No se pudo completar el cálculo.")
        return payload
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "El cálculo excedió el tiempo permitido. Simplificá la expresión.") from None
    except (OSError, ValueError):
        raise HTTPException(500, "No se pudo completar el cálculo.") from None
    finally:
        SLOTS.release()


def run_calculation(request: CalculationRequest) -> CalculationResponse:
    payload = run_worker(request)
    try:
        return CalculationResponse.model_validate(payload["result"])
    except (KeyError, ValueError):
        raise HTTPException(500, "No se pudo completar el cálculo.") from None


def run_export(request: CalculationRequest, kind: Literal["pdf", "csv"]) -> bytes:
    payload = run_worker(request, kind)
    try:
        return base64.b64decode(payload["file"], validate=True)
    except (KeyError, ValueError):
        raise HTTPException(500, "No se pudo generar el archivo.") from None
