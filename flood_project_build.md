# 🌊 FloodSense — Agro Pune Hackathon Project Build Instructions
> **For AI Agent (Anti-Gravity) Execution — Task-by-Task Build Guide**
> Project: Terrain-Aware Flood Prediction & Simulation Web Platform
> Context: Agro Pune Hackathon | Team: AIT Computer Science

---

## 📌 Project Overview

**FloodSense** is a web platform that:
- Ingests Digital Elevation Model (DEM) data of Maharashtra terrain
- Pulls real-time + forecast rainfall data from weather APIs
- Simulates how water flows and accumulates across terrain
- Predicts flood-risk zones for the next 6 / 12 / 24 / 72 hours
- Displays everything on an interactive map with color-coded risk overlays
- Provides early warning alerts for villages, farmland, and roads in flood zones

**Target Region:** Maharashtra (focus district: Kolhapur or Raigad — historically flood-prone)
**Primary Users:** Farmers, local government, disaster management teams

---

## 🗂️ Project Structure to Generate

```
floodsense/
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Map.jsx              # Main Leaflet/MapLibre map
│   │   │   ├── RiskOverlay.jsx      # Color-coded flood risk layer
│   │   │   ├── Timeline.jsx         # 6h/12h/24h/72h forecast toggle
│   │   │   ├── AlertPanel.jsx       # High-risk zone alerts
│   │   │   ├── StatsBar.jsx         # Rainfall mm, risk %, affected area
│   │   │   └── Sidebar.jsx          # Controls and legend
│   │   ├── hooks/
│   │   │   ├── useWeatherData.js    # Fetches Open-Meteo API
│   │   │   └── useFloodData.js      # Fetches flood prediction from backend
│   │   └── styles/
│   │       └── main.css
├── backend/
│   ├── main.py                      # FastAPI entry point
│   ├── routers/
│   │   ├── weather.py               # Weather API proxy + processing
│   │   ├── flood.py                 # Flood simulation endpoint
│   │   └── alerts.py                # Alert generation logic
│   ├── services/
│   │   ├── dem_processor.py         # DEM loading, flow direction, accumulation
│   │   ├── flood_simulator.py       # Core simulation logic
│   │   ├── ml_predictor.py          # XGBoost risk score model
│   │   └── weather_fetcher.py       # Open-Meteo API integration
│   ├── models/
│   │   └── xgb_flood_model.pkl      # Trained model (see Data section)
│   └── data/
│       ├── maharashtra_dem.tif      # SRTM elevation raster
│       ├── maharashtra_boundary.geojson
│       ├── rivers.geojson           # From India WRIS
│       ├── villages.geojson         # Settlement points
│       └── roads.geojson            # Road network
├── notebooks/
│   ├── 01_dem_processing.ipynb      # EDA + flow accumulation
│   ├── 02_model_training.ipynb      # XGBoost training
│   └── 03_simulation_test.ipynb     # End-to-end test
├── requirements.txt
├── package.json
└── README.md
```

---

## 🔢 PHASE 1 — Data Acquisition & Setup

### Task 1.1 — Download DEM Data
- Go to: https://earthdata.nasa.gov (free account required)
- Search: `SRTM 1 Arc-Second Global` or `NASADEM`
- Download tile: `N16E073` to `N22E080` (covers Maharashtra)
- Alternatively use ALOS World 3D at 12.5m from: https://search.asf.alaska.edu
- Save as: `backend/data/maharashtra_dem.tif`

### Task 1.2 — Download Boundary & Vector Data
- Maharashtra district boundary GeoJSON: https://data.gov.in (search "Maharashtra district shapefile")
- River network shapefile: https://india-wris.nrsc.gov.in
- Village points: https://bhuvan.nrsc.gov.in
- Roads: OpenStreetMap via https://download.geofabrik.de/asia/india.html (Maharashtra extract)
- Convert all shapefiles to GeoJSON using: `ogr2ogr -f GeoJSON output.geojson input.shp`

### Task 1.3 — Historical Flood Data (for ML training)
- NRSC Flood Monitoring Archive: https://bhuvan.nrsc.gov.in/disaster/disaster.php
- Dartmouth Flood Observatory: https://floodobservatory.colorado.edu
- Download Maharashtra flood extent rasters for years 2019, 2020, 2021, 2022, 2023
- IMD Gridded Rainfall: https://imdpune.gov.in (0.25° resolution daily rainfall)

### Task 1.4 — Environment Setup
```bash
# Python environment
pip install fastapi uvicorn rasterio richdem whitebox geopandas \
            shapely numpy pandas scikit-learn xgboost joblib \
            requests python-dotenv pyproj fiona

# Node/React environment
npm create vite@latest frontend -- --template react
cd frontend && npm install leaflet react-leaflet axios recharts lucide-react
```

---

## 🔢 PHASE 2 — Backend: Data Processing Pipeline

### Task 2.1 — DEM Processor (`backend/services/dem_processor.py`)

Build a Python module that does the following steps:

**Step A — Load and clip DEM**
```python
import rasterio
from rasterio.mask import mask
import geopandas as gpd

# Load DEM
# Clip to Maharashtra boundary using the GeoJSON
# Reproject to EPSG:32643 (UTM Zone 43N — standard for Maharashtra)
# Fill NoData values
# Save processed DEM
```

**Step B — Sink Filling**
```python
import richdem as rd

# Load DEM as richdem array
# Fill sinks (depressions) using rd.FillDepressions()
# This is critical — unfilled sinks create fake pooling in simulation
```

**Step C — Flow Direction**
```python
# Use richdem D8 or D-infinity method
# rd.FlowProportions() or rd.FlowDirectionD8()
# Output: flow direction raster (each cell points to downhill neighbor)
```

**Step D — Flow Accumulation**
```python
# rd.FlowAccumulation(flow_directions)
# Output: raster where each cell value = number of upstream cells draining into it
# High accumulation = natural drainage channels = flood risk corridors
```

**Step E — Slope Calculation**
```python
# Calculate slope in degrees from DEM
# Flat areas (low slope) accumulate water = higher risk
# Use: rd.TerrainAttribute(dem, attrib='slope_degrees')
```

**Step F — Export to GeoJSON grid**
```python
# Convert raster results to a grid of polygons or points with attributes:
# - elevation, flow_accumulation, slope, x, y
# Export as GeoJSON for frontend consumption
```

---

### Task 2.2 — Weather Fetcher (`backend/services/weather_fetcher.py`)

```python
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
        "timezone": "Asia/Kolkata"
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
        "timezone": "Asia/Kolkata"
    }
    response = requests.get(url, params=params)
    return response.json()
```

---

### Task 2.3 — Flood Simulator (`backend/services/flood_simulator.py`)

**Core Logic:**
```
Flood Risk Score (per grid cell) =
    f(flow_accumulation, slope, rainfall_mm, soil_moisture, distance_to_river, elevation)
```

**Algorithm steps:**
1. Load pre-processed DEM attributes (flow accumulation, slope, elevation)
2. Get rainfall forecast from weather fetcher for region
3. For each time step (6h, 12h, 24h, 72h):
   a. Compute cumulative rainfall for that window
   b. Adjust for soil moisture (saturated soil = faster runoff)
   c. Apply rainfall to flow accumulation grid — high accumulation cells fill first
   d. Mark cells as `flooded` if estimated water depth > threshold (0.3m)
   e. Spread water to adjacent lower cells (simple cellular automata step)
4. Output: GeoJSON with flood probability + estimated depth per cell per time step

**Thresholds (adjustable):**
```python
FLOOD_THRESHOLDS = {
    "low":      rainfall_mm >= 30,   # Yellow zone
    "medium":   rainfall_mm >= 65,   # Orange zone
    "high":     rainfall_mm >= 115,  # Red zone (IMD heavy rain classification)
    "extreme":  rainfall_mm >= 204   # Dark red (IMD extremely heavy rain)
}
```

---

### Task 2.4 — ML Risk Predictor (`backend/services/ml_predictor.py`)

**Feature Vector per grid cell:**
```python
features = [
    'elevation_m',           # from DEM
    'slope_degrees',          # from DEM
    'flow_accumulation',      # from DEM processing
    'distance_to_river_m',    # from river shapefile
    'soil_moisture',          # from Open-Meteo API
    'rainfall_24h_mm',        # from weather API
    'rainfall_72h_mm',        # cumulative
    'land_cover_type',        # 0=water, 1=urban, 2=cropland, 3=forest (from LULC)
    'antecedent_rainfall_7d', # from historical weather API
]
```

**Training:**
```python
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

# Label: 1 = flooded (from historical flood extent rasters), 0 = not flooded
# Train XGBoost binary classifier
# Target: >85% recall on flood class (missing a flood is worse than a false alarm)

model = XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.05)
model.fit(X_train, y_train)
joblib.dump(model, 'backend/models/xgb_flood_model.pkl')
```

**Inference:**
```python
def predict_flood_risk(feature_grid: pd.DataFrame) -> np.ndarray:
    model = joblib.load('backend/models/xgb_flood_model.pkl')
    probabilities = model.predict_proba(feature_grid)[:, 1]  # flood probability 0-1
    return probabilities
```

---

### Task 2.5 — FastAPI Routes (`backend/main.py` + routers)

**Endpoints to build:**

```
GET  /api/weather?lat=16.7&lon=74.2&days=3
     → Returns hourly rainfall forecast for coordinates

POST /api/simulate
     Body: { lat, lon, radius_km, forecast_hours: [6, 12, 24, 72] }
     → Returns GeoJSON FeatureCollection with flood risk per cell per time step

GET  /api/alerts?district=Kolhapur
     → Returns list of high-risk villages/areas with risk level and ETA

GET  /api/terrain?lat=16.7&lon=74.2&radius_km=50
     → Returns terrain GeoJSON (elevation, flow channels) for base map layer

GET  /api/historical?start=2023-07-01&end=2023-07-31&district=Kolhapur
     → Returns historical flood events + rainfall for comparison
```

**CORS config** — enable all origins for hackathon demo
**Response format** — always return GeoJSON FeatureCollection for map-ready consumption

---

## 🔢 PHASE 3 — Frontend Build

### Task 3.1 — Design Direction
- **Theme:** Dark map aesthetic (dark basemap like CartoDB Dark Matter)
- **Colors:**
  - Background: `#0d1117` (near black)
  - Safe zone: `#22c55e` (green)
  - Low risk: `#eab308` (yellow)
  - Medium risk: `#f97316` (orange)
  - High risk: `#ef4444` (red)
  - Extreme risk: `#7f1d1d` (dark red)
  - Accent: `#38bdf8` (sky blue — water theme)
- **Font:** Use `Space Mono` for data values, `DM Sans` for UI text
- **Feel:** Command-center / emergency dashboard — serious but clear

### Task 3.2 — Map Component (`frontend/src/components/Map.jsx`)

Use **React-Leaflet** with:
- Base tile: `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`
- Overlay layers:
  1. **Terrain layer** — elevation heatmap (subtle, always on)
  2. **River layer** — blue polylines from rivers GeoJSON
  3. **Flood risk layer** — choropleth colored polygons from simulation API
  4. **Village markers** — red pulsing dots for high-risk settlements
  5. **Road layer** — gray lines, red where intersecting flood zones

**Interactivity:**
- Click any cell → popup with: elevation, slope, predicted flood depth, risk %, rainfall forecast
- Hover → tooltip with location name and risk level
- Toggle layers on/off from sidebar

### Task 3.3 — Timeline Slider (`frontend/src/components/Timeline.jsx`)

- Horizontal slider or button group: `NOW | +6h | +12h | +24h | +72h`
- Switching time step re-fetches or re-renders flood risk overlay from cached simulation data
- Show animated transition between time steps (CSS opacity fade)
- Display timestamp of when forecast was last updated

### Task 3.4 — Alert Panel (`frontend/src/components/AlertPanel.jsx`)

Right sidebar panel showing:
```
🔴 EXTREME RISK
   Shirol Taluka, Kolhapur
   Expected depth: 1.2m | ETA: 6 hours

🟠 HIGH RISK
   Hatkanangle, Kolhapur
   Expected depth: 0.6m | ETA: 12 hours

🟡 MODERATE RISK
   Kagal, Kolhapur
   Expected depth: 0.2m | ETA: 24 hours
```
- Sorted by severity descending
- Each alert has a "Zoom to location" button
- Pulsing red border animation for EXTREME alerts

### Task 3.5 — Stats Bar (`frontend/src/components/StatsBar.jsx`)

Top bar showing live metrics:
```
🌧 Rainfall (24h): 87mm  |  ⚠️ At-Risk Villages: 23  |  🌾 Farmland Affected: 1,240 ha  |  🛣 Roads Flooded: 14 km  |  🕐 Last Updated: 2 mins ago
```

### Task 3.6 — API Integration (`frontend/src/hooks/`)

```javascript
// useWeatherData.js
const useWeatherData = (lat, lon) => {
  // Calls GET /api/weather
  // Returns: rainfall forecast array, current soil moisture, hourly precipitation
  // Refreshes every 30 minutes
}

// useFloodData.js
const useFloodData = (lat, lon, radiusKm, forecastHour) => {
  // Calls POST /api/simulate
  // Returns: GeoJSON FeatureCollection for current time step
  // Caches all time steps on first load
}
```

---

## 🔢 PHASE 4 — Model Training Notebook

### Task 4.1 — `notebooks/02_model_training.ipynb`

Steps to document and run:
1. Load historical flood extent rasters (NRSC data)
2. Load matched historical rainfall from Open-Meteo archive
3. Load DEM features (elevation, slope, flow accumulation per grid cell)
4. Join datasets by spatial coordinates → create feature table
5. Label each cell: flooded=1, not-flooded=0
6. Handle class imbalance (flooded cells << non-flooded) using `scale_pos_weight` in XGBoost
7. Train/test split: 80/20 by year (not random — avoid data leakage across time)
8. Train XGBoost model
9. Evaluate: classification report, ROC-AUC, confusion matrix
10. Plot feature importance — show which features matter most
11. Save model to `backend/models/xgb_flood_model.pkl`

---

## 🔢 PHASE 5 — Integration & Demo Prep

### Task 5.1 — End-to-End Test
- Start backend: `uvicorn backend.main:app --reload`
- Start frontend: `cd frontend && npm run dev`
- Test full flow: Load map → fetch terrain → run simulation for Kolhapur → display risk overlay → toggle timeline

### Task 5.2 — Demo Data Fallback
- Pre-compute simulation results for Kolhapur district for July 2021 (actual major flood year)
- Store as static GeoJSON files — use as fallback if live API is slow during demo
- This ensures a smooth demo even with poor internet at hackathon venue

### Task 5.3 — Deployment (optional but impressive)
- Backend: Deploy to Render.com or Railway.app (free tier)
- Frontend: Deploy to Vercel or Netlify (free tier)
- Share a live URL during the presentation

---

## 📦 Dependencies List

### `requirements.txt`
```
fastapi==0.111.0
uvicorn==0.30.1
rasterio==1.3.10
richdem==0.3.4
whitebox==2.3.4
geopandas==0.14.4
shapely==2.0.4
numpy==1.26.4
pandas==2.2.2
scikit-learn==1.5.0
xgboost==2.0.3
joblib==1.4.2
requests==2.32.3
python-dotenv==1.0.1
pyproj==3.6.1
fiona==1.9.6
scipy==1.13.1
```

### `package.json` (frontend dependencies)
```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-leaflet": "^4.2.1",
    "leaflet": "^1.9.4",
    "axios": "^1.7.2",
    "recharts": "^2.12.7",
    "lucide-react": "^0.383.0",
    "clsx": "^2.1.1"
  }
}
```

---

## ✅ Execution Order for Anti-Gravity Agent

```
1. Create full project folder structure as defined above
2. Setup Python environment, install all requirements.txt packages
3. Setup Node environment, install all package.json dependencies
4. PHASE 2: Build backend — dem_processor.py → weather_fetcher.py → flood_simulator.py → ml_predictor.py → FastAPI routes
5. PHASE 1: Download and place all datasets (or use placeholder/mock data if download not possible)
6. PHASE 4: Run model training notebook with available data (or use pre-trained weights if data unavailable)
7. PHASE 3: Build frontend — Map.jsx → Timeline.jsx → AlertPanel.jsx → StatsBar.jsx → Sidebar.jsx → API hooks
8. PHASE 5: Integration test end-to-end, fix any connection issues
9. Create demo fallback static GeoJSON files for Kolhapur 2021 flood data
10. Run full demo flow and verify all components work together
```

---

## 🔑 Key Design Decisions & Notes

- **No authentication needed** for hackathon demo — keep it open
- **Graceful degradation** — if ML model fails, fall back to physics-based simulation only
- **Mobile responsive** — judges may check on phones
- **Loading states** — show skeleton loaders while simulation runs (can take 3-5 seconds)
- **Error boundaries** — wrap map and API calls in try/catch with friendly error messages
- **Demo-first** — focus on Kolhapur district for the demo, but make the district selectable

---

*Generated for AIT Computer Science Team | Agro Pune Hackathon*
*Build target: FloodSense v1.0 — Terrain-Aware Flood Prediction Platform*
