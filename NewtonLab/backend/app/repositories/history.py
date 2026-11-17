from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, UniqueConstraint, delete, func, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class HistoryRecord(Base):
    __tablename__ = "web_history"
    __table_args__ = (
        UniqueConstraint("owner_hash", "request_id", name="uq_history_owner_request"),
        Index("ix_history_owner_created", "owner_hash", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_hash: Mapped[str] = mapped_column(String(64))
    request_id: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expression: Mapped[str] = mapped_column(String(512))
    # Resumen validado, sin iteraciones ni muestras gráficas.
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB)


class HistoryRepository:
    def __init__(self, session: Session, owner_hash: str):
        self.session = session
        self.owner_hash = owner_hash

    def recent(self, query: str, limit: int, offset: int) -> list[HistoryRecord]:
        statement = select(HistoryRecord).where(HistoryRecord.owner_hash == self.owner_hash)
        if query:
            statement = statement.where(HistoryRecord.expression.icontains(query, autoescape=True))
        statement = statement.order_by(HistoryRecord.created_at.desc(), HistoryRecord.id.desc())
        return list(self.session.scalars(statement.limit(limit + 1).offset(offset)))

    def get(self, identifier: UUID) -> HistoryRecord | None:
        return self.session.scalar(select(HistoryRecord).where(
            HistoryRecord.id == identifier, HistoryRecord.owner_hash == self.owner_hash))

    def by_request(self, request_id: UUID) -> HistoryRecord | None:
        return self.session.scalar(select(HistoryRecord).where(
            HistoryRecord.request_id == request_id, HistoryRecord.owner_hash == self.owner_hash))

    def add(self, request_id: UUID, expression: str, summary: dict[str, Any]) -> HistoryRecord:
        self.session.execute(insert(HistoryRecord).values(
            id=uuid4(), owner_hash=self.owner_hash, request_id=request_id,
            expression=expression, summary=summary,
        ).on_conflict_do_nothing(constraint="uq_history_owner_request"))
        self.session.commit()
        record = self.by_request(request_id)
        if record is None:
            raise RuntimeError("No se pudo recuperar el cálculo guardado.")
        return record

    def remove(self, identifier: UUID | None = None) -> bool:
        statement = delete(HistoryRecord).where(HistoryRecord.owner_hash == self.owner_hash)
        if identifier is not None:
            statement = statement.where(HistoryRecord.id == identifier)
        removed = self.session.scalars(statement.returning(HistoryRecord.id)).first() is not None
        self.session.commit()
        return removed
