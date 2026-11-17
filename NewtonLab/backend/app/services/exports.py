"""Reutiliza reportes de escritorio sin abrir Qt ni tocar el historial SQLite."""
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from app.core.expression_parser import parse_expression
from app.core.newton_raphson import solve
from app.services.export_service import export_csv, export_pdf
from app.services.history_service import Calculation
from app.ui.theme import COLORS  # Módulo de constantes sin dependencia de Qt.
from ..schemas.calculations import CalculationRequest


def export_bytes(request: CalculationRequest, kind: Literal["pdf", "csv"], directory: Path | None = None) -> bytes:
    if directory is None:
        with TemporaryDirectory(prefix="newtonlab-export-") as temporary:
            return export_bytes(request, kind, Path(temporary))
    parsed = parse_expression(request.expression)
    result = solve(parsed, request.initial_guess, request.tolerance, request.max_iterations)
    calculation = Calculation(request.expression, str(parsed.derivative), request.initial_guess,
                              request.tolerance, request.max_iterations, result)
    path = directory / f"newtonlab.{kind}"
    if kind == "pdf":
        export_pdf(calculation, path, COLORS)
    else:
        # Sólo encabezados fijos y floats del motor: no hay celdas de texto
        # aportadas por el usuario que Excel pueda interpretar como fórmulas.
        export_csv(calculation, path)
    return path.read_bytes()
