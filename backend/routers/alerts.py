"""
alerts.py — Alert generation logic router

Endpoints:
  GET /alerts?district=Kolhapur
    → Returns list of high-risk villages/areas with risk level and ETA

  GET /historical?start=2023-07-01&end=2023-07-31&district=Kolhapur
    → Returns historical flood events + rainfall for comparison
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException

from backend.services.weather_fetcher import (
    get_rainfall_forecast,
    get_historical_rainfall,
    parse_hourly_precipitation,
    get_cumulative_rainfall,
)
from backend.services.flood_simulator import classify_rainfall

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Known settlements per district (seed data for demo)
# In production, this would come from the villages.geojson file
# ---------------------------------------------------------------------------
DISTRICT_SETTLEMENTS = {
    "Kolhapur": [
        {"name": "Shirol Taluka", "lat": 16.73, "lon": 74.60, "population": 45000, "type": "taluka"},
        {"name": "Hatkanangle", "lat": 16.77, "lon": 74.44, "population": 32000, "type": "taluka"},
        {"name": "Kagal", "lat": 16.58, "lon": 74.31, "population": 28000, "type": "taluka"},
        {"name": "Panhala", "lat": 16.81, "lon": 74.11, "population": 18000, "type": "town"},
        {"name": "Ichalkaranji", "lat": 16.69, "lon": 74.46, "population": 287570, "type": "city"},
        {"name": "Gadhinglaj", "lat": 16.23, "lon": 74.35, "population": 52000, "type": "taluka"},
        {"name": "Radhanagari", "lat": 16.41, "lon": 73.99, "population": 22000, "type": "taluka"},
        {"name": "Shahuwadi", "lat": 16.88, "lon": 73.97, "population": 15000, "type": "town"},
        {"name": "Karvir", "lat": 16.68, "lon": 74.22, "population": 35000, "type": "taluka"},
        {"name": "Bavda", "lat": 16.02, "lon": 73.88, "population": 8500, "type": "town"},
    ],
    "Raigad": [
        {"name": "Mahad", "lat": 18.08, "lon": 73.42, "population": 35000, "type": "taluka"},
        {"name": "Panvel", "lat": 18.99, "lon": 73.12, "population": 180000, "type": "city"},
        {"name": "Alibag", "lat": 18.64, "lon": 72.87, "population": 25000, "type": "town"},
        {"name": "Murud", "lat": 18.32, "lon": 72.96, "population": 12000, "type": "town"},
        {"name": "Roha", "lat": 18.44, "lon": 73.12, "population": 32000, "type": "taluka"},
    ],
    "Sangli": [
        {"name": "Miraj", "lat": 16.83, "lon": 74.65, "population": 125000, "type": "city"},
        {"name": "Palus", "lat": 17.10, "lon": 74.44, "population": 18000, "type": "town"},
        {"name": "Walwa", "lat": 17.06, "lon": 74.19, "population": 22000, "type": "taluka"},
    ],
    "Satara": [
        {"name": "Patan", "lat": 17.38, "lon": 73.90, "population": 30000, "type": "taluka"},
        {"name": "Karad", "lat": 17.28, "lon": 74.18, "population": 65000, "type": "city"},
        {"name": "Wai", "lat": 17.95, "lon": 73.89, "population": 35000, "type": "town"},
    ],
}

# ---------------------------------------------------------------------------
# Alert severity thresholds (hours to flood = ETA)
# ---------------------------------------------------------------------------
def _compute_eta(cum_6h: float, cum_12h: float, cum_24h: float) -> Optional[int]:
    """Estimate when flooding begins (hours from now)."""
    if cum_6h >= 115:
        return 6
    if cum_12h >= 115:
        return 12
    if cum_24h >= 115:
        return 24
    if cum_24h >= 65:
        return 48
    return None


def _estimate_depth(cum_rain_mm: float) -> float:
    """Rough estimated flood depth for an area based on cumulative rain."""
    if cum_rain_mm >= 204:
        return round(1.0 + (cum_rain_mm - 204) / 200, 1)
    if cum_rain_mm >= 115:
        return round(0.5 + (cum_rain_mm - 115) / 200, 1)
    if cum_rain_mm >= 65:
        return round(0.2 + (cum_rain_mm - 65) / 250, 1)
    return 0.0


# =========================================================================
# GET /alerts
# =========================================================================

@router.get("/alerts")
async def get_alerts(
    district: str = Query("Kolhapur", description="District name"),
):
    """
    Generate flood alerts for settlements in the given district.
    Sorted by severity descending.
    """
    try:
        settlements = DISTRICT_SETTLEMENTS.get(district)
        if not settlements:
            # Return empty alerts for unknown district
            return {
                "district": district,
                "alert_count": 0,
                "alerts": [],
                "summary": f"No settlement data available for {district}. Supported: {list(DISTRICT_SETTLEMENTS.keys())}",
            }

        alerts = []
        for s in settlements:
            raw = get_rainfall_forecast(s["lat"], s["lon"], days=3)
            hourly = parse_hourly_precipitation(raw)

            cum_6h = get_cumulative_rainfall(hourly, 6)
            cum_12h = get_cumulative_rainfall(hourly, 12)
            cum_24h = get_cumulative_rainfall(hourly, 24)
            cum_72h = get_cumulative_rainfall(hourly, 72)

            severity = classify_rainfall(cum_24h)
            eta = _compute_eta(cum_6h, cum_12h, cum_24h)
            depth = _estimate_depth(cum_24h)

            if severity == "none" and cum_72h < 30:
                continue  # skip safe areas

            # Determine risk level based on rain + location factors
            risk_level = severity
            if risk_level == "none" and cum_72h >= 30:
                risk_level = "low"

            alert = {
                "location": s["name"],
                "lat": s["lat"],
                "lon": s["lon"],
                "district": district,
                "population": s["population"],
                "settlement_type": s["type"],
                "risk_level": risk_level,
                "rainfall_24h_mm": round(cum_24h, 1),
                "rainfall_72h_mm": round(cum_72h, 1),
                "expected_depth_m": depth,
                "eta_hours": eta,
                "recommendations": _get_recommendations(risk_level),
            }
            alerts.append(alert)

        # Sort: extreme > high > medium > low
        severity_order = {"extreme": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
        alerts.sort(key=lambda a: severity_order.get(a["risk_level"], 5))

        return {
            "district": district,
            "alert_count": len(alerts),
            "high_risk_count": sum(
                1 for a in alerts if a["risk_level"] in ("extreme", "high")
            ),
            "alerts": alerts,
        }

    except Exception as exc:
        logger.exception("Alerts endpoint error")
        raise HTTPException(status_code=500, detail=str(exc))


def _get_recommendations(risk_level: str) -> List[str]:
    """Return action recommendations for the given risk level."""
    recs = {
        "extreme": [
            "Immediate evacuation recommended",
            "Move to higher ground",
            "Avoid river crossings and low-lying roads",
            "Contact NDRF / District Emergency Operations Centre",
        ],
        "high": [
            "Prepare for possible evacuation",
            "Secure livestock and farming equipment",
            "Avoid travel near rivers and streams",
            "Monitor official weather updates hourly",
        ],
        "medium": [
            "Stay alert and monitor conditions",
            "Keep emergency kit ready",
            "Avoid unnecessary travel after dark",
            "Clear drains and waterways near property",
        ],
        "low": [
            "Be aware of rising water levels",
            "Check local drainage and water bodies periodically",
            "Keep emergency contacts handy",
        ],
    }
    return recs.get(risk_level, ["Monitor weather updates"])


# =========================================================================
# GET /historical
# =========================================================================

@router.get("/historical")
async def get_historical(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    district: str = Query("Kolhapur", description="District name"),
):
    """
    Return historical rainfall and known flood events for a district
    and date range.
    """
    try:
        # District centre coordinates
        district_centres = {
            "Kolhapur": (16.70, 74.24),
            "Raigad": (18.52, 73.18),
            "Sangli": (16.85, 74.56),
            "Satara": (17.68, 74.00),
        }
        lat, lon = district_centres.get(district, (16.70, 74.24))

        # Get historical rainfall from Open-Meteo archive
        rainfall_data = get_historical_rainfall(lat, lon, start, end)

        # Known major flood events in Maharashtra (hardcoded for demo)
        known_events = _get_known_flood_events(district, start, end)

        daily = rainfall_data.get("daily", {})
        dates = daily.get("time", [])
        precip = daily.get("precipitation_sum", [])

        total_rain = sum(precip)
        max_daily = max(precip) if precip else 0
        rainy_days = sum(1 for p in precip if p >= 2.5)

        return {
            "district": district,
            "period": {"start": start, "end": end},
            "summary": {
                "total_rainfall_mm": round(total_rain, 1),
                "max_daily_mm": round(max_daily, 1),
                "rainy_days": rainy_days,
                "total_days": len(dates),
            },
            "daily_rainfall": [
                {"date": d, "rainfall_mm": round(p, 1)}
                for d, p in zip(dates, precip)
            ],
            "flood_events": known_events,
        }

    except Exception as exc:
        logger.exception("Historical endpoint error")
        raise HTTPException(status_code=500, detail=str(exc))


def _get_known_flood_events(
    district: str, start: str, end: str
) -> List[dict]:
    """
    Return known historical flood events for a district.
    In production this would query a database; for the hackathon we
    include major documented events.
    """
    events = {
        "Kolhapur": [
            {
                "year": 2019,
                "date_range": "2019-08-05 to 2019-08-12",
                "description": "Worst floods in 50 years; Panchganga river breached danger level by 12 ft",
                "affected_talukas": ["Shirol", "Hatkanangle", "Kagal", "Radhanagari"],
                "max_rainfall_mm": 312,
                "people_evacuated": 400000,
            },
            {
                "year": 2021,
                "date_range": "2021-07-22 to 2021-07-28",
                "description": "Flash floods due to heavy rainfall; multiple villages inundated",
                "affected_talukas": ["Shirol", "Hatkanangle", "Panhala"],
                "max_rainfall_mm": 250,
                "people_evacuated": 135000,
            },
            {
                "year": 2023,
                "date_range": "2023-07-15 to 2023-07-21",
                "description": "Heavy monsoon flooding along Krishna and Panchganga rivers",
                "affected_talukas": ["Shirol", "Karvir", "Hatkanangle"],
                "max_rainfall_mm": 198,
                "people_evacuated": 80000,
            },
        ],
        "Raigad": [
            {
                "year": 2021,
                "date_range": "2021-07-22 to 2021-07-25",
                "description": "Landslides and floods in Mahad; Taliye village landslide killed 84 people",
                "affected_talukas": ["Mahad", "Poladpur"],
                "max_rainfall_mm": 594,
                "people_evacuated": 100000,
            },
            {
                "year": 2023,
                "date_range": "2023-07-19 to 2023-07-23",
                "description": "Severe flooding in low-lying areas along Savitri river",
                "affected_talukas": ["Mahad", "Roha"],
                "max_rainfall_mm": 220,
                "people_evacuated": 45000,
            },
        ],
    }

    district_events = events.get(district, [])

    # Filter by date range if possible
    filtered = []
    for e in district_events:
        event_year = str(e["year"])
        if start[:4] <= event_year <= end[:4]:
            filtered.append(e)

    return filtered if filtered else district_events
