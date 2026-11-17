from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

from app.core.models import Status


class CalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expression: str = Field(min_length=1, max_length=512)
    initial_guess: FiniteFloat = Field(default=1.5, ge=-1e12, le=1e12)
    tolerance: FiniteFloat = Field(default=1e-6, ge=1e-14, le=1)
    max_iterations: int = Field(default=100, ge=1, le=200)


class IterationResponse(BaseModel):
    index: int
    x: FiniteFloat
    fx: FiniteFloat
    derivative: FiniteFloat
    next_x: FiniteFloat
    absolute_error: FiniteFloat
    residual: FiniteFloat


class CurveResponse(BaseModel):
    x: list[FiniteFloat]
    y: list[FiniteFloat | None]
    notice: str


class CalculationResponse(BaseModel):
    expression: str
    derivative: str
    parameters: CalculationRequest
    root: FiniteFloat | None
    last_approximation: FiniteFloat
    converged: bool
    status: Status
    termination_reason: str
    final_residual: FiniteFloat | None
    final_error: FiniteFloat | None
    iteration_count: int
    iterations: list[IterationResponse]
    curve: CurveResponse


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["NewtonLab API"] = "NewtonLab API"
