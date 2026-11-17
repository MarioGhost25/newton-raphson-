from fastapi import APIRouter
from ...runner import run_calculation
from ...schemas.calculations import CalculationRequest, CalculationResponse

router = APIRouter(prefix="/api/calculations", tags=["calculations"])


@router.post("/newton-raphson", response_model=CalculationResponse)
def newton_raphson(request: CalculationRequest) -> CalculationResponse:
    return run_calculation(request)
