from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .api.routes.calculations import router
from .schemas.calculations import HealthResponse
from .api.routes.history import router as history_router
from .api.routes.exports import router as exports_router
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
import logging
from .database import dispose_engine
from .settings import configure_cors

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # No crea tablas ni conexiones durante el arranque.
    yield
    dispose_engine()


class BodyLimitMiddleware:
    """Limita también cuerpos enviados por fragmentos, antes de leer JSON."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > 8192:
                return await JSONResponse({"detail": "La solicitud supera 8 KiB."}, 413)(scope, receive, send)
            if not message.get("more_body", False):
                break

        async def replay():
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)


app = FastAPI(title="NewtonLab API", version="0.1.0", lifespan=lifespan)
app.add_middleware(BodyLimitMiddleware)
app.include_router(router)
app.include_router(history_router)
app.include_router(exports_router)


@app.middleware("http")
async def private_responses(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/history"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    logger.warning("Database request failed (%s): %s", type(exc).__name__, request.url.path)
    return JSONResponse(status_code=503, content={"detail": "Historial no disponible. Revisá PostgreSQL y el esquema del servidor."})


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    # No reflejar entradas (incluidos NaN/Infinity) ni objetos internos en JSON.
    return JSONResponse(status_code=422, content={
        "detail": "Parámetros inválidos. Revisá los campos y límites indicados en /docs.",
        "fields": [".".join(map(str, error["loc"])) for error in exc.errors()],
    })


@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception):
    logger.error("Request failed (%s): %s", type(exc).__name__, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "No se pudo completar la solicitud."})


configure_cors(app)
