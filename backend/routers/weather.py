"""
weather.py — Weather API proxy + processing router

Endpoints:
  GET /weather?lat=16.7&lon=74.2&days=3
    → Returns hourly rainfall forecast for coordinates
"""

import logging

from fastapi import APIRouter, Query, HTTPException

from backend.services.weather_fetcher import (
    get_rainfall_forecast,
    get_historical_rainfall,
    parse_hourly_precipitation,
    get_cumulative_rainfall,
    get_current_soil_moisture,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/weather")
async def get_weather(
    lat: float = Query(..., description="Latitude", ge=-90, le=90),
    lon: float = Query(..., description="Longitude", ge=-180, le=180),
    days: int = Query(3, description="Number of forecast days (1-7)", ge=1, le=7),
):
    """
    Fetch rainfall forecast from Open-Meteo API.

    Returns hourly precipitation, probability, soil moisture,
    and daily summary.
    """
    try:
        raw = get_rainfall_forecast(lat, lon, days)
        hourly = parse_hourly_precipitation(raw)

        # Pre-compute cumulative rainfall for key windows
        cum_6h = get_cumulative_rainfall(hourly, 6)
        cum_12h = get_cumulative_rainfall(hourly, 12)
        cum_24h = get_cumulative_rainfall(hourly, 24)
        cum_72h = get_cumulative_rainfall(hourly, 72)

        # Current soil moisture
        soil = get_current_soil_moisture(lat, lon)

        return {
            "latitude": lat,
            "longitude": lon,
            "forecast_days": days,
            "current_soil_moisture": soil,
            "cumulative_rainfall": {
                "6h_mm": round(cum_6h, 1),
                "12h_mm": round(cum_12h, 1),
                "24h_mm": round(cum_24h, 1),
                "72h_mm": round(cum_72h, 1),
            },
            "hourly": hourly,
            "daily": raw.get("daily", {}),
        }
    except Exception as exc:
        logger.exception("Weather endpoint error")
        raise HTTPException(status_code=500, detail=str(exc))
