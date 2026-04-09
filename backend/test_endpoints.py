"""Quick smoke test for all FloodSense API endpoints."""
import requests
import json
import time

BASE = "http://127.0.0.1:8000"

def test(name, method, path, **kwargs):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    try:
        if method == "GET":
            r = requests.get(f"{BASE}{path}", params=kwargs.get("params"), timeout=30)
        else:
            r = requests.post(f"{BASE}{path}", json=kwargs.get("json"), timeout=30)
        data = r.json()
        print(f"Status: {r.status_code}")
        return data
    except Exception as e:
        print(f"ERROR: {e}")
        return None

# 1. Root
data = test("Root Health Check", "GET", "/")
if data:
    print(f"Project: {data.get('project')} v{data.get('version')} — {data.get('status')}")

# 2. Weather
data = test("Weather Forecast", "GET", "/api/weather", params={"lat": 16.7, "lon": 74.2, "days": 1})
if data:
    print(f"Soil moisture: {data.get('current_soil_moisture')}")
    print(f"Cumulative rainfall: {data.get('cumulative_rainfall')}")
    print(f"Hourly entries: {len(data.get('hourly', []))}")

# 3. Terrain
data = test("Terrain GeoJSON", "GET", "/api/terrain", params={"lat": 16.7, "lon": 74.2, "radius_km": 50})
if data:
    features = data.get("terrain", {}).get("features", [])
    print(f"Feature count: {len(features)}")
    if features:
        sample = features[0]
        props = sample.get("properties", {})
        print(f"Sample: elev={props.get('elevation')}m, slope={props.get('slope')}deg, flow_accum={props.get('flow_accumulation')}")

# 4. Simulate
data = test("Flood Simulation", "POST", "/api/simulate", json={"lat": 16.7, "lon": 74.2, "radius_km": 25, "forecast_hours": [6, 24]})
if data:
    ts = data.get("timesteps", {})
    for k, v in ts.items():
        stats = v.get("stats", {})
        feat_count = len(v.get("geojson", {}).get("features", []))
        ml = v.get("ml_overlay", {})
        print(f"  t+{k}h: severity={stats.get('severity')}, flooded={stats.get('flooded_pct')}%, max_depth={stats.get('max_depth_m')}m, features={feat_count}, ml_max_prob={ml.get('max_probability')}")

# 5. Alerts
data = test("Alerts - Kolhapur", "GET", "/api/alerts", params={"district": "Kolhapur"})
if data:
    print(f"Alert count: {data.get('alert_count')}, High risk: {data.get('high_risk_count')}")
    for a in data.get("alerts", [])[:3]:
        print(f"  {a['location']}: {a['risk_level']} | rain24h={a['rainfall_24h_mm']}mm | depth={a['expected_depth_m']}m")

# 6. Historical
data = test("Historical - Kolhapur Jul 2021", "GET", "/api/historical", params={"start": "2021-07-01", "end": "2021-07-31", "district": "Kolhapur"})
if data:
    s = data.get("summary", {})
    print(f"Total rain: {s.get('total_rainfall_mm')}mm, Max daily: {s.get('max_daily_mm')}mm, Rainy days: {s.get('rainy_days')}")
    events = data.get("flood_events", [])
    print(f"Flood events: {len(events)}")
    for e in events:
        print(f"  {e['year']}: {e['description'][:70]}...")

print(f"\n{'='*60}")
print("ALL TESTS COMPLETE")
print(f"{'='*60}")
