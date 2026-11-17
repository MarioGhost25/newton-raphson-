from typing import Literal
from fastapi import APIRouter, Response
from ...runner import run_export
from ...schemas.calculations import CalculationRequest

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.post("/{kind}")
def export(kind: Literal["pdf", "csv"], parameters: CalculationRequest) -> Response:
    # No recibe IDs privados ni resultados del cliente: sólo parámetros públicos.
    content = run_export(parameters, kind)
    return Response(content=content, media_type="application/pdf" if kind == "pdf" else "text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="newtonlab.{kind}"',
                             "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
