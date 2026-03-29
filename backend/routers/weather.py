"""
weather.py — Weather API proxy + processing router

Endpoints:
  GET /weather?lat=16.7&lon=74.2&days=3
    → Returns hourly rainfall forecast for coordinates
"""

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/weather")
async def get_weather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    days: int = Query(3, description="Number of forecast days"),
):
    """Fetch rainfall forecast from Open-Meteo API."""
    # TODO: Implement in Phase 2 using weather_fetcher service
    return {"message": "Weather endpoint — to be implemented"}
