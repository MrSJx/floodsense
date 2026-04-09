"""
weather_fetcher.py — Open-Meteo API integration

Functions:
  get_rainfall_forecast(lat, lon, days)
    → Fetch hourly rainfall forecast (no API key needed)

  get_historical_rainfall(lat, lon, start, end)
    → Fetch historical rainfall from Open-Meteo Archive API

  get_grid_forecast(lat, lon, radius_km, days)
    → Fetch forecasts for a grid of points around a centre

  parse_hourly_precipitation(response)
    → Extract structured hourly rainfall from Open-Meteo response

  get_current_soil_moisture(lat, lon)
    → Return latest soil moisture value for a location
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
REQUEST_TIMEOUT = 15  # seconds


# =========================================================================
# Core API calls
# =========================================================================

def get_rainfall_forecast(lat: float, lon: float, days: int = 3) -> Dict[str, Any]:
    """
    Fetch hourly rainfall forecast from Open-Meteo (no API key needed).
    Returns the raw JSON response dict.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,precipitation_probability,soil_moisture_0_to_1cm",
        "daily": "precipitation_sum,precipitation_probability_max",
        "forecast_days": days,
        "timezone": "Asia/Kolkata",
    }
    try:
        response = requests.get(FORECAST_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.error("Open-Meteo forecast request failed: %s", exc)
        return _mock_forecast(lat, lon, days)


def get_historical_rainfall(
    lat: float, lon: float, start: str, end: str
) -> Dict[str, Any]:
    """
    Fetch historical rainfall from Open-Meteo Archive API.
    start / end format: "YYYY-MM-DD"
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": "precipitation_sum",
        "timezone": "Asia/Kolkata",
    }
    try:
        response = requests.get(ARCHIVE_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.error("Open-Meteo archive request failed: %s", exc)
        return _mock_historical(start, end)


# =========================================================================
# Grid forecast — sample multiple locations
# =========================================================================

def get_grid_forecast(
    center_lat: float,
    center_lon: float,
    radius_km: float = 25.0,
    grid_size: int = 3,
    days: int = 3,
) -> List[Dict[str, Any]]:
    """
    Fetch forecasts for a grid_size × grid_size grid of points around
    the centre coordinate.  Returns list of dicts with latlng + data.
    """
    # ~0.009° per km at this latitude
    delta_lat = (radius_km / 111.0)
    delta_lon = (radius_km / (111.0 * np.cos(np.radians(center_lat))))

    lats = np.linspace(center_lat - delta_lat, center_lat + delta_lat, grid_size)
    lons = np.linspace(center_lon - delta_lon, center_lon + delta_lon, grid_size)

    results = []
    for lat in lats:
        for lon in lons:
            data = get_rainfall_forecast(float(lat), float(lon), days)
            results.append({"lat": float(lat), "lon": float(lon), "forecast": data})
    return results


# =========================================================================
# Parsing helpers
# =========================================================================

def parse_hourly_precipitation(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract structured hourly rainfall entries from an Open-Meteo response.
    Returns list of {timestamp, rainfall_mm, probability, soil_moisture}.
    """
    hourly = response.get("hourly", {})
    times = hourly.get("time", [])
    precip = hourly.get("precipitation", [])
    prob = hourly.get("precipitation_probability", [])
    soil = hourly.get("soil_moisture_0_to_1cm", [])

    entries = []
    for i, ts in enumerate(times):
        entries.append(
            {
                "timestamp": ts,
                "rainfall_mm": precip[i] if i < len(precip) else 0.0,
                "probability": prob[i] if i < len(prob) else None,
                "soil_moisture": soil[i] if i < len(soil) else None,
            }
        )
    return entries


def get_cumulative_rainfall(
    hourly_entries: List[Dict[str, Any]], hours: int
) -> float:
    """Return total rainfall in the first `hours` entries."""
    return sum(e.get("rainfall_mm", 0.0) for e in hourly_entries[:hours])


def get_current_soil_moisture(lat: float, lon: float) -> float:
    """
    Return the latest soil-moisture value (m³/m³) for a location.
    Falls back to 0.3 (moderate) if the API call fails.
    """
    try:
        data = get_rainfall_forecast(lat, lon, days=1)
        soil_values = (
            data.get("hourly", {}).get("soil_moisture_0_to_1cm", [])
        )
        if soil_values:
            # Return the most recent non-null value
            for v in reversed(soil_values):
                if v is not None:
                    return float(v)
    except Exception:
        pass
    return 0.3  # default moderate moisture


# =========================================================================
# Mock / fallback data (when API is unreachable at the hackathon)
# =========================================================================

def _mock_forecast(lat: float, lon: float, days: int) -> Dict[str, Any]:
    """Generate plausible mock forecast data for demo purposes."""
    np.random.seed(int(lat * 100 + lon * 10) % 2**31)
    hours = days * 24
    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)

    times = [
        (base_time + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M")
        for h in range(hours)
    ]

    # Simulate monsoon-like pattern: bursts of rain with dry spells
    precip = []
    for h in range(hours):
        # Higher rain probability in afternoon (12-20 IST)
        hour_of_day = (base_time.hour + h) % 24
        base_rate = 2.0 if 12 <= hour_of_day <= 20 else 0.5
        rain = max(0.0, np.random.exponential(base_rate))
        precip.append(round(rain, 1))

    probability = [min(95, int(p * 10 + 20)) for p in precip]
    soil_moisture = [round(0.25 + 0.1 * np.random.randn(), 3) for _ in range(hours)]

    daily_precip = [
        round(sum(precip[d * 24 : (d + 1) * 24]), 1) for d in range(days)
    ]

    return {
        "latitude": lat,
        "longitude": lon,
        "hourly": {
            "time": times,
            "precipitation": precip,
            "precipitation_probability": probability,
            "soil_moisture_0_to_1cm": soil_moisture,
        },
        "daily": {
            "time": [
                (base_time + timedelta(days=d)).strftime("%Y-%m-%d")
                for d in range(days)
            ],
            "precipitation_sum": daily_precip,
            "precipitation_probability_max": [min(95, max(probability[d * 24 : (d + 1) * 24]) if precip else 50) for d in range(days)],
        },
    }


def _mock_historical(start: str, end: str) -> Dict[str, Any]:
    """Generate mock historical rainfall data."""
    from datetime import date as dt_date

    start_dt = datetime.strptime(start, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end, "%Y-%m-%d").date()
    num_days = (end_dt - start_dt).days + 1

    np.random.seed(42)
    dates = [
        (start_dt + timedelta(days=d)).isoformat() for d in range(num_days)
    ]
    precip = [round(max(0, np.random.exponential(8)), 1) for _ in range(num_days)]

    return {
        "daily": {
            "time": dates,
            "precipitation_sum": precip,
        }
    }
