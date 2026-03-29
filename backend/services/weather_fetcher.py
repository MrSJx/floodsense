"""
weather_fetcher.py — Open-Meteo API integration

Functions:
  get_rainfall_forecast(lat, lon, days)
    → Fetch hourly rainfall forecast (no API key needed)

  get_historical_rainfall(lat, lon, start, end)
    → Fetch historical rainfall from Open-Meteo Archive API
"""

import requests


def get_rainfall_forecast(lat: float, lon: float, days: int = 3):
    """
    Fetch hourly rainfall forecast from Open-Meteo (no API key needed).
    Returns: list of {timestamp, rainfall_mm} for next `days` days
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,precipitation_probability,soil_moisture_0_to_1cm",
        "daily": "precipitation_sum,precipitation_probability_max",
        "forecast_days": days,
        "timezone": "Asia/Kolkata",
    }
    response = requests.get(url, params=params)
    return response.json()


def get_historical_rainfall(lat: float, lon: float, start: str, end: str):
    """
    Fetch historical rainfall from Open-Meteo Archive API.
    start/end format: "YYYY-MM-DD"
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": "precipitation_sum",
        "timezone": "Asia/Kolkata",
    }
    response = requests.get(url, params=params)
    return response.json()
