"""
alerts.py — Alert generation logic router

Endpoints:
  GET /alerts?district=Kolhapur
    → Returns list of high-risk villages/areas with risk level and ETA

  GET /historical?start=2023-07-01&end=2023-07-31&district=Kolhapur
    → Returns historical flood events + rainfall for comparison
"""

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/alerts")
async def get_alerts(district: str = Query("Kolhapur", description="District name")):
    """Get flood alert list for a district."""
    # TODO: Implement in Phase 2
    return {"message": "Alerts endpoint — to be implemented"}


@router.get("/historical")
async def get_historical(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    district: str = Query("Kolhapur", description="District name"),
):
    """Get historical flood events and rainfall data."""
    # TODO: Implement in Phase 2
    return {"message": "Historical data endpoint — to be implemented"}
