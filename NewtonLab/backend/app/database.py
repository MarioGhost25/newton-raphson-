"""PostgreSQL opcional para calcular, obligatorio para el historial."""
from collections.abc import Iterator
from functools import lru_cache
import os

from fastapi import HTTPException
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from . import settings  # Carga el .env local sin reemplazar variables del hosting.


def database_engine(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() not in ("postgresql", "postgres"):
        raise ValueError("El historial requiere PostgreSQL.")
    return create_engine(parsed.set(drivername="postgresql+psycopg"), pool_pre_ping=True,
                         pool_size=5, max_overflow=0, pool_timeout=5,
                         connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"})


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise HTTPException(503, "Historial no disponible: configurá DATABASE_URL en el servidor.")
    try:
        return database_engine(url)
    except (ValueError, ImportError):
        raise HTTPException(503, "La configuración de PostgreSQL no es válida.") from None


def get_session() -> Iterator[Session]:
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session


def dispose_engine() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()
        get_engine.cache_clear()


if __name__ == "__main__":
    from .repositories.history import Base
    # Creación inicial explícita e idempotente; nunca elimina ni migra datos.
    Base.metadata.create_all(get_engine())
    print("Esquema inicial de historial disponible.")
