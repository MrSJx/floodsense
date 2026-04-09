"""
flood.py — Flood simulation endpoint router

Endpoints:
  POST /simulate
    Body: { lat, lon, radius_km, forecast_hours: [6, 12, 24, 72] }
    → Returns GeoJSON FeatureCollection with flood risk per cell per time step

  GET /terrain?lat=16.7&lon=74.2&radius_km=50
    → Returns terrain GeoJSON (elevation, flow channels) for base map layer
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.dem_processor import process_dem
from backend.services.flood_simulator import simulate_flood, DEFAULT_TIMESTEPS
from backend.services.weather_fetcher import (
    get_rainfall_forecast,
    parse_hourly_precipitation,
    get_current_soil_moisture,
)
from backend.services.ml_predictor import predict_flood_risk, build_feature_grid

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Cache DEM products so we don't reprocess every request
# ---------------------------------------------------------------------------
_dem_cache: dict = {}


def _get_dem_products() -> dict:
    """Return cached DEM processing results, computing them on first call."""
    if not _dem_cache:
        logger.info("Processing DEM (first request — may take a few seconds) …")
        products = process_dem(export_geojson=True)
        _dem_cache.update(products)
    return _dem_cache


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SimulationRequest(BaseModel):
    lat: float = Field(16.7, description="Centre latitude")
    lon: float = Field(74.2, description="Centre longitude")
    radius_km: float = Field(25.0, description="Simulation radius in km")
    forecast_hours: List[int] = Field(
        default=[6, 12, 24, 72],
        description="Hours into the future to simulate",
    )


# ---------------------------------------------------------------------------
# POST /simulate
# ---------------------------------------------------------------------------

@router.post("/simulate")
async def simulate_flood_endpoint(req: SimulationRequest):
    """
    Run a flood simulation and return GeoJSON results for each
    requested time step.
    """
    try:
        dem_products = _get_dem_products()
        elevation = dem_products["filled_dem"]
        flow_accum = dem_products["flow_accum"]
        slope = dem_products["slope"]
        meta = dem_products["meta"]

        # Fetch rainfall forecast
        raw_forecast = get_rainfall_forecast(req.lat, req.lon, days=3)
        hourly_entries = parse_hourly_precipitation(raw_forecast)
        hourly_rain = [e["rainfall_mm"] for e in hourly_entries]

        # Current soil moisture
        soil = get_current_soil_moisture(req.lat, req.lon)

        # Run physics-based simulation
        sim_results = simulate_flood(
            elevation=elevation,
            flow_accum=flow_accum,
            slope=slope,
            meta=meta,
            hourly_rainfall=hourly_rain,
            soil_moisture=soil,
            timesteps=req.forecast_hours,
        )

        # Optionally overlay ML predictions for 24h & 72h windows
        ml_overlay = {}
        for hours in req.forecast_hours:
            cum_24 = sum(hourly_rain[:min(24, len(hourly_rain))])
            cum_72 = sum(hourly_rain[:min(72, len(hourly_rain))])
            feature_df = build_feature_grid(
                elevation, slope, flow_accum,
                rainfall_24h=cum_24,
                rainfall_72h=cum_72,
                soil_moisture=soil,
            )
            ml_probs = predict_flood_risk(feature_df)
            ml_overlay[hours] = {
                "mean_probability": round(float(ml_probs.mean()), 4),
                "max_probability": round(float(ml_probs.max()), 4),
                "high_risk_pct": round(
                    float((ml_probs >= 0.6).sum() / len(ml_probs) * 100), 2
                ),
            }

        # Build response — serialise only JSON-safe fields
        response_data = {}
        for hours, data in sim_results.items():
            response_data[str(hours)] = {
                "geojson": data["geojson"],
                "stats": data["stats"],
                "ml_overlay": ml_overlay.get(hours, {}),
            }

        return {
            "centre": {"lat": req.lat, "lon": req.lon},
            "radius_km": req.radius_km,
            "timesteps": response_data,
        }

    except Exception as exc:
        logger.exception("Simulation endpoint error")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /terrain
# ---------------------------------------------------------------------------

@router.get("/terrain")
async def get_terrain(
    lat: float = Query(16.7, description="Centre latitude"),
    lon: float = Query(74.2, description="Centre longitude"),
    radius_km: float = Query(50, description="Radius in km"),
):
    """
    Return terrain GeoJSON (elevation, flow accumulation, slope)
    for the base map layer.
    """
    try:
        dem_products = _get_dem_products()
        geojson = dem_products.get("geojson")

        if geojson is None:
            raise HTTPException(status_code=404, detail="Terrain data not yet processed")

        return {
            "centre": {"lat": lat, "lon": lon},
            "radius_km": radius_km,
            "terrain": geojson,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Terrain endpoint error")
        raise HTTPException(status_code=500, detail=str(exc))
