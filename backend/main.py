"""
FloodSense Backend — FastAPI Entry Point
main.py

Endpoints:
  GET  /                    — Health check
  GET  /api/weather         — Rainfall forecast for coordinates
  POST /api/simulate        — Flood risk simulation (GeoJSON)
  GET  /api/alerts          — High-risk area alerts
  GET  /api/terrain         — Terrain GeoJSON for base map layer
  GET  /api/historical      — Historical flood events + rainfall
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import weather, flood, alerts

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("floodsense")


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown hooks
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-process DEM on startup so first request is fast."""
    logger.info("🌊 FloodSense API starting up …")
    # We intentionally don't block startup with DEM processing;
    # it will be lazy-loaded on the first /simulate or /terrain call.
    yield
    logger.info("FloodSense API shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="FloodSense API",
    description=(
        "Terrain-Aware Flood Prediction & Simulation API for Maharashtra. "
        "Combines DEM analysis, real-time weather data, physics-based "
        "simulation, and ML risk scoring."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — enable all origins for hackathon demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------
app.include_router(weather.router, prefix="/api", tags=["Weather"])
app.include_router(flood.router, prefix="/api", tags=["Flood Simulation"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts & History"])


# ---------------------------------------------------------------------------
# Root health-check
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    return {
        "project": "FloodSense",
        "version": "1.0.0",
        "status": "running",
        "description": "Terrain-Aware Flood Prediction & Simulation API",
        "endpoints": {
            "weather": "/api/weather?lat=16.7&lon=74.2&days=3",
            "simulate": "POST /api/simulate",
            "alerts": "/api/alerts?district=Kolhapur",
            "terrain": "/api/terrain?lat=16.7&lon=74.2&radius_km=50",
            "historical": "/api/historical?start=2023-07-01&end=2023-07-31&district=Kolhapur",
        },
    }
