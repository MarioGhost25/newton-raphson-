"""Método real de Newton-Raphson con historial inmutable."""
import math
import sympy as sp
from .expression_parser import ParsedExpression, X, parse_expression
from .models import Iteration, NewtonResult, Status


class EvaluationError(Exception):
    def __init__(self, status: Status, message: str):
        self.status = status
        super().__init__(message)


def evaluate(expression: sp.Expr, x: float) -> float:
    try:
        value = expression.subs(X, sp.Float(x)).evalf()
        if value.has(sp.zoo, sp.oo, -sp.oo, sp.nan):
            raise EvaluationError(Status.NON_FINITE, "La evaluación produjo un valor infinito o indefinido.")
        if value.is_real is not True:
            raise EvaluationError(Status.DOMAIN_ERROR, "La función o su derivada no está definida en los reales en este punto.")
        result = float(value)
        if not math.isfinite(result):
            raise EvaluationError(Status.NON_FINITE, "La evaluación excedió el rango numérico disponible.")
        return result
    except EvaluationError:
        raise
    except (ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
        raise EvaluationError(Status.DOMAIN_ERROR, "No se pudo evaluar la función en este punto.") from exc


def solve(function: str | ParsedExpression, x0: float = 1.5,
          tolerance: float = 1e-8, max_iterations: int = 100,
          derivative_threshold: float = 1e-12) -> NewtonResult:
    for value, label in ((x0, "El valor inicial"), (tolerance, "La tolerancia"),
                         (derivative_threshold, "El umbral de derivada")):
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{label} debe ser un número finito.")
    if tolerance <= 0 or derivative_threshold <= 0:
        raise ValueError("La tolerancia y el umbral de derivada deben ser positivos.")
    if type(max_iterations) is not int or not 1 <= max_iterations <= 1000:
        raise ValueError("El máximo de iteraciones debe ser un entero entre 1 y 1000.")
    parsed = parse_expression(function) if isinstance(function, str) else function
    history: list[Iteration] = []
    x, residual = float(x0), None

    def finish(status: Status, message: str) -> NewtonResult:
        return NewtonResult(status, message, x, residual, tuple(history))

    try:
        fx = evaluate(parsed.expression, x)
        residual = abs(fx)
        if fx == 0:
            return finish(Status.CONVERGED, "El valor inicial es una raíz exacta.")
        for index in range(1, max_iterations + 1):
            derivative = evaluate(parsed.derivative, x)
            if abs(derivative) <= derivative_threshold:
                return finish(Status.ZERO_DERIVATIVE, "La derivada es demasiado pequeña. Probá otro valor inicial.")
            next_x = x - fx / derivative
            if not math.isfinite(next_x):
                return finish(Status.NON_FINITE, "El siguiente valor de x no es finito.")
            error = abs(next_x - x)
            if not math.isfinite(error):
                return finish(Status.NON_FINITE, "El error absoluto excedió el rango numérico.")
            next_fx = evaluate(parsed.expression, next_x)
            next_residual = abs(next_fx)
            history.append(Iteration(index, x, fx, derivative, next_x, error, next_residual))
            x, fx, residual = next_x, next_fx, next_residual
            if error <= tolerance and residual <= tolerance:
                return finish(Status.CONVERGED, "El error absoluto y el residuo cumplen la tolerancia.")
        return finish(Status.MAX_ITERATIONS, "Se alcanzó el límite de iteraciones sin cumplir ambos criterios de convergencia.")
    except EvaluationError as exc:
        return finish(exc.status, str(exc))
