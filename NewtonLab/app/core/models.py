"""Resultados independientes de la interfaz gráfica."""
from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    CONVERGED = "Convergencia alcanzada"
    ZERO_DERIVATIVE = "Derivada nula o casi nula"
    DOMAIN_ERROR = "Error de dominio"
    NON_FINITE = "Valor no finito"
    MAX_ITERATIONS = "Sin convergencia"


@dataclass(frozen=True)
class Iteration:
    index: int
    x: float
    fx: float
    derivative: float
    next_x: float
    absolute_error: float
    residual: float


@dataclass(frozen=True)
class NewtonResult:
    status: Status
    message: str
    root: float
    residual: float | None
    iterations: tuple[Iteration, ...]

    @property
    def converged(self) -> bool:
        return self.status is Status.CONVERGED
