"""
flood.py — Flood simulation endpoint router

Endpoints:
  POST /simulate
    Body: { lat, lon, radius_km, forecast_hours: [6, 12, 24, 72] }
    → Returns GeoJSON FeatureCollection with flood risk per cell per time step

  GET /terrain?lat=16.7&lon=74.2&radius_km=50
    → Returns terrain GeoJSON (elevation, flow channels) for base map layer
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/simulate")
async def simulate_flood():
    """Run flood simulation and return GeoJSON results."""
    # TODO: Implement in Phase 2 using flood_simulator service
    return {"message": "Flood simulation endpoint — to be implemented"}


@router.get("/terrain")
async def get_terrain(lat: float = 16.7, lon: float = 74.2, radius_km: float = 50):
    """Return terrain GeoJSON for map base layer."""
    # TODO: Implement in Phase 2 using dem_processor service
    return {"message": "Terrain endpoint — to be implemented"}
