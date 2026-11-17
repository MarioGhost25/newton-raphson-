from hashlib import sha256
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session
from ...database import get_session
from ...repositories.history import HistoryRepository
from ...schemas.history import HistoryEntry, HistoryPage, RestoredCalculation, SaveCalculation
from ...services.history import HistoryService

router = APIRouter(prefix="/api/history", tags=["history"])


def owner_hash(token: Annotated[str, Header(alias="X-History-Token", pattern=r"^[0-9a-f]{64}$")]) -> str:
    return sha256(token.encode("ascii")).hexdigest()


def history_service(owner: Annotated[str, Depends(owner_hash)],
                    session: Annotated[Session, Depends(get_session)]) -> HistoryService:
    return HistoryService(HistoryRepository(session, owner))


Service = Annotated[HistoryService, Depends(history_service)]


@router.get("", response_model=HistoryPage)
def recent(service: Service, q: str = Query(default="", max_length=512),
           limit: int = Query(default=20, ge=1, le=50), offset: int = Query(default=0, ge=0, le=10000)) -> HistoryPage:
    return service.recent(q, limit, offset)


@router.post("", response_model=HistoryEntry, status_code=201)
def save(request: SaveCalculation, service: Service) -> HistoryEntry:
    return service.save(request)


@router.get("/{identifier}", response_model=RestoredCalculation)
def restore(identifier: UUID, service: Service) -> RestoredCalculation:
    return service.restore(identifier)


@router.delete("/{identifier}", status_code=204)
def remove(identifier: UUID, service: Service) -> Response:
    service.remove(identifier)
    return Response(status_code=204)


@router.delete("", status_code=204)
def clear(service: Service) -> Response:
    service.remove()
    return Response(status_code=204)
