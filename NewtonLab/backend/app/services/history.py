from uuid import UUID
from fastapi import HTTPException
from ..repositories.history import HistoryRecord, HistoryRepository
from ..runner import run_calculation
from ..schemas.history import CalculationSummary, HistoryEntry, HistoryPage, RestoredCalculation, SaveCalculation


def entry(record: HistoryRecord) -> HistoryEntry:
    return HistoryEntry(id=record.id, created_at=record.created_at,
                        summary=CalculationSummary.model_validate(record.summary))


class HistoryService:
    def __init__(self, repository: HistoryRepository):
        self.repository = repository

    def recent(self, query: str, limit: int, offset: int) -> HistoryPage:
        records = self.repository.recent(query, limit, offset)
        return HistoryPage(items=[entry(record) for record in records[:limit]],
                           has_more=len(records) > limit, limit=limit, offset=offset)

    def save(self, request: SaveCalculation) -> HistoryEntry:
        record = self.repository.by_request(request.request_id)
        if record is None:
            # Nunca aceptar resultados numéricos aportados por el navegador.
            result = run_calculation(request.parameters)
            summary = CalculationSummary.model_validate(result.model_dump())
            record = self.repository.add(request.request_id, result.expression, summary.model_dump(mode="json"))
        saved = entry(record)
        if saved.summary.parameters != request.parameters:
            raise HTTPException(409, "El identificador de guardado ya corresponde a otro cálculo.")
        return saved

    def restore(self, identifier: UUID) -> RestoredCalculation:
        record = self.repository.get(identifier)
        if record is None:
            raise HTTPException(404, "Cálculo no encontrado.")
        saved = entry(record)
        return RestoredCalculation(entry=saved, result=run_calculation(saved.summary.parameters))

    def remove(self, identifier: UUID | None = None) -> None:
        removed = self.repository.remove(identifier)
        if identifier is not None and not removed:
            raise HTTPException(404, "Cálculo no encontrado.")
