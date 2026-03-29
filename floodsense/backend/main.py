"""
FloodSense Backend — FastAPI Entry Point
main.py

Endpoints:
  GET  /api/weather       — Rainfall forecast for coordinates
  POST /api/simulate      — Flood risk simulation (GeoJSON)
  GET  /api/alerts         — High-risk area alerts
  GET  /api/terrain       — Terrain GeoJSON for base map layer
  GET  /api/historical    — Historical flood events + rainfall
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers (to be implemented in Phase 2)
# from routers import weather, flood, alerts

app = FastAPI(
    title="FloodSense API",
    description="Terrain-Aware Flood Prediction & Simulation API for Maharashtra",
    version="1.0.0",
)

# CORS — enable all origins for hackathon demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers (uncomment when implemented)
# app.include_router(weather.router, prefix="/api")
# app.include_router(flood.router, prefix="/api")
# app.include_router(alerts.router, prefix="/api")


@app.get("/")
def root():
    return {
        "project": "FloodSense",
        "version": "1.0.0",
        "status": "running",
        "description": "Terrain-Aware Flood Prediction & Simulation API",
    }
