"""Adaptador ejecutado en un proceso descartable; el motor permanece intacto."""
from dataclasses import asdict
import json
import math
import sys
import base64
from pathlib import Path

from app.core.expression_parser import ExpressionError, parse_expression
from app.core.newton_raphson import solve
from app.core.plot_data import initial_interval, sample_curve
from .schemas.calculations import CalculationRequest, CalculationResponse, CurveResponse


def calculate(request: CalculationRequest) -> CalculationResponse:
    parsed = parse_expression(request.expression)
    result = solve(parsed, request.initial_guess, request.tolerance, request.max_iterations)
    curve = sample_curve(parsed.expression, initial_interval(request.initial_guess, result), count=401)
    return CalculationResponse(
        expression=request.expression, derivative=str(parsed.derivative), parameters=request,
        root=result.root if result.converged else None, last_approximation=result.root,
        converged=result.converged, status=result.status, termination_reason=result.message,
        final_residual=result.residual,
        final_error=result.iterations[-1].absolute_error if result.iterations else None,
        iteration_count=len(result.iterations),
        iterations=[asdict(step) for step in result.iterations],
        curve=CurveResponse(x=curve.x.tolist(),
                            y=[float(y) if math.isfinite(y) else None for y in curve.y],
                            notice=curve.notice),
    )


def main() -> None:
    try:
        request = CalculationRequest.model_validate_json(sys.stdin.read())
        mode = sys.argv[1] if len(sys.argv) > 1 else "calculate"
        if mode in ("pdf", "csv"):
            from app.services.export_service import ExportError
            from .services.exports import export_bytes
            try:
                directory = Path(sys.argv[2]) if len(sys.argv) > 2 else None
                payload = {"file": base64.b64encode(export_bytes(request, mode, directory)).decode("ascii")}
            except ExportError:
                payload = {"invalid_export": "No se pudo exportar. Para CSV se requiere al menos una iteración completada."}
        else:
            result = calculate(request)
            payload = {"result": result.model_dump(mode="json")}
    except ExpressionError as exc:
        payload = {"invalid_expression": str(exc)}
    except Exception:
        payload = {"error": "No se pudo completar el cálculo."}
    sys.stdout.write(json.dumps(payload, allow_nan=False, ensure_ascii=True))


if __name__ == "__main__":
    main()
