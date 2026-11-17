"""Muestreo real acotado para visualización; no recalcula pasos de Newton."""
from dataclasses import dataclass
import numpy as np
import sympy as sp
from .expression_parser import X
from .models import Iteration, NewtonResult

VISUAL_LIMIT = 1e12
FUNCTIONS = {sp.sin: np.sin, sp.cos: np.cos, sp.tan: np.tan,
             sp.asin: np.arcsin, sp.acos: np.arccos, sp.atan: np.arctan,
             sp.sinh: np.sinh, sp.cosh: np.cosh, sp.tanh: np.tanh,
             sp.exp: np.exp, sp.log: np.log, sp.Abs: np.abs}


@dataclass(frozen=True)
class CurveData:
    x: np.ndarray
    y: np.ndarray
    notice: str


def initial_interval(x0: float, result: NewtonResult) -> tuple[float, float]:
    points = [x0, result.root]
    points.extend(step.x for step in result.iterations)
    points.extend(step.next_x for step in result.iterations)
    finite = [float(x) for x in points if np.isfinite(x) and abs(x) <= VISUAL_LIMIT]
    if not finite:
        return -1.0, 1.0
    low, high = min(finite), max(finite)
    margin = max((high - low) * .18, max(abs(low), abs(high)) * .025, .5)
    return max(-VISUAL_LIMIT, low - margin), min(VISUAL_LIMIT, high + margin)


def sample_curve(expression: sp.Expr, limits: tuple[float, float], count: int = 1601) -> CurveData:
    low, high = limits
    if not np.isfinite([low, high]).all() or low >= high:
        raise ValueError("El intervalo de visualización debe ser finito y creciente.")
    x = np.linspace(low, high, count)
    breaks = np.zeros(count, dtype=bool)

    def split_at_zeros(values):
        values = np.broadcast_to(values, x.shape)
        crossings = (np.signbit(values[:-1]) != np.signbit(values[1:])) | (values[:-1] == 0) | (values[1:] == 0)
        breaks[1:] |= crossings
        breaks[:-1] |= crossings

    def visit(node):
        if node == X:
            return x
        if node.is_Number or node in (sp.pi, sp.E):
            return float(node)
        args = [visit(arg) for arg in node.args]
        if node.func is sp.Add:
            result = 0.0
            for arg in args:
                result = np.add(result, arg)
            return result
        if node.func is sp.Mul:
            result = 1.0
            for arg in args:
                result = np.multiply(result, arg)
            return result
        if node.func is sp.Pow:
            if node.args[1].is_negative:
                base = node.args[0]
                # Detecta también polos de orden par entre muestras.
                while base.func is sp.Pow and base.args[1].is_positive:
                    base = base.args[0]
                split_at_zeros(visit(base))
            return np.power(args[0], args[1])
        if node.func in FUNCTIONS:
            if node.func is sp.tan:
                split_at_zeros(np.cos(args[0]))
            return FUNCTIONS[node.func](*args)
        raise ValueError("Esta expresión no admite muestreo numérico para la gráfica.")

    try:
        with np.errstate(all="ignore"):
            y = np.array(np.broadcast_to(visit(expression), x.shape), dtype=float, copy=True)
    except (ValueError, TypeError, OverflowError, FloatingPointError) as exc:
        return CurveData(x, np.full(x.shape, np.nan), f"No se pudo dibujar la curva: {exc}")
    invalid = ~np.isfinite(y) | (np.abs(y) > VISUAL_LIMIT)
    # Saltos abruptos restantes se separan de forma conservadora. Un muestreo
    # finito no demuestra continuidad de una expresión arbitraria.
    with np.errstate(all="ignore"):
        jumps = np.abs(np.diff(y))
        valid_jumps = jumps[np.isfinite(jumps)]
        if valid_jumps.size:
            threshold = max(float(np.median(valid_jumps)) * 100, 1e-10)
            abrupt = (jumps > threshold) & (np.signbit(y[:-1]) != np.signbit(y[1:]))
            breaks[1:] |= abrupt
            breaks[:-1] |= abrupt
    y[invalid | breaks] = np.nan
    notice = "Se omiten tramos fuera del dominio, discontinuos o fuera de escala." if (invalid | breaks).any() else ""
    if not np.isfinite(y).any():
        notice = "No hay valores representables en este intervalo. El resultado numérico se conserva."
    return CurveData(x, y, notice)


def vertical_interval(y: np.ndarray, result: NewtonResult) -> tuple[float, float]:
    finite = y[np.isfinite(y)]
    bounds = list(np.percentile(finite, [2, 98])) if finite.size else [-1., 1.]
    bounds.append(0.)
    bounds.extend(step.fx for step in result.iterations if abs(step.fx) <= VISUAL_LIMIT)
    low, high = min(bounds), max(bounds)
    margin = max((high - low) * .12, 1e-6)
    return max(-VISUAL_LIMIT, low - margin), min(VISUAL_LIMIT, high + margin)


def tangent_points(step: Iteration, limits: tuple[float, float]):
    if not np.isfinite([step.x, step.fx, step.derivative, step.next_x]).all() or step.derivative == 0:
        return np.array([]), np.array([])
    x = np.unique([limits[0], step.x, step.next_x, limits[1]])
    with np.errstate(all="ignore"):
        y = step.fx + step.derivative * (x - step.x)
    y[~np.isfinite(y) | (np.abs(y) > VISUAL_LIMIT)] = np.nan
    return x, y
