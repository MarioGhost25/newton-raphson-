from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, FiniteFloat
from app.core.models import Status
from .calculations import CalculationRequest, CalculationResponse


class SaveCalculation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    parameters: CalculationRequest


class CalculationSummary(BaseModel):
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


class HistoryEntry(BaseModel):
    id: UUID
    created_at: datetime
    summary: CalculationSummary


class HistoryPage(BaseModel):
    items: list[HistoryEntry]
    has_more: bool
    offset: int
    limit: int


class RestoredCalculation(BaseModel):
    entry: HistoryEntry
    result: CalculationResponse
