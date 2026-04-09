"""
flood_simulator.py — Core flood simulation logic

Algorithm:
  1. Load pre-processed DEM attributes (flow accumulation, slope, elevation)
  2. Get rainfall forecast from weather fetcher for region
  3. For each time step (6h, 12h, 24h, 72h):
     a. Compute cumulative rainfall for that window
     b. Adjust for soil moisture (saturated soil → faster runoff)
     c. Apply rainfall to flow accumulation grid
     d. Mark cells as flooded if estimated water depth > threshold (0.3m)
     e. Spread water to adjacent lower cells (cellular automata)
  4. Output: GeoJSON with flood probability + estimated depth per cell per time step

Thresholds (IMD classification):
  low:     rainfall_mm >= 30   (Yellow zone)
  medium:  rainfall_mm >= 65   (Orange zone)
  high:    rainfall_mm >= 115  (Red zone)
  extreme: rainfall_mm >= 204  (Dark red)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.ndimage import uniform_filter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# IMD Rainfall Thresholds (mm)
# ---------------------------------------------------------------------------
FLOOD_THRESHOLDS = {
    "low": 30,       # Yellow
    "medium": 65,    # Orange
    "high": 115,     # Red
    "extreme": 204,  # Dark red
}

# Flood depth threshold in metres — a cell is "flooded" above this
FLOOD_DEPTH_THRESHOLD = 0.3  # metres

# Time windows for simulation (hours)
DEFAULT_TIMESTEPS = [6, 12, 24, 72]


# =========================================================================
# Classify rainfall severity
# =========================================================================

def classify_rainfall(mm: float) -> str:
    """Return IMD severity label for a cumulative rainfall amount."""
    if mm >= FLOOD_THRESHOLDS["extreme"]:
        return "extreme"
    if mm >= FLOOD_THRESHOLDS["high"]:
        return "high"
    if mm >= FLOOD_THRESHOLDS["medium"]:
        return "medium"
    if mm >= FLOOD_THRESHOLDS["low"]:
        return "low"
    return "none"


# =========================================================================
# Water‑depth model (physics‑based heuristic)
# =========================================================================

def compute_water_depth(
    rainfall_mm: float,
    flow_accum: np.ndarray,
    slope: np.ndarray,
    elevation: np.ndarray,
    soil_moisture: float = 0.3,
    cell_size_m: float = 30.0,
) -> np.ndarray:
    """
    Estimate water depth (metres) per cell using a simplified physical
    model:

        depth ≈ (rainfall × runoff_coeff × upstream_area) / cell_area
               × (1 / (1 + slope))

    Parameters
    ----------
    rainfall_mm : cumulative rainfall in mm for the time window
    flow_accum  : number of upstream cells draining into each cell
    slope       : slope in degrees
    elevation   : raw DEM elevation in metres
    soil_moisture : 0-1, higher → more saturated → more runoff
    cell_size_m : cell resolution in metres
    """
    if rainfall_mm <= 0:
        return np.zeros_like(elevation, dtype=np.float32)

    # Runoff coefficient increases with soil saturation
    # Typical range: 0.2 (dry soil, vegetated) → 0.8 (saturated / urban)
    runoff_coeff = 0.2 + 0.6 * min(soil_moisture, 1.0)

    # Convert rainfall to metres
    rainfall_m = rainfall_mm / 1000.0

    # Upstream contributing area in m² (flow_accum counts cells)
    upstream_area = flow_accum * (cell_size_m ** 2)

    # Slope factor — flat areas collect water, steep areas drain
    slope_factor = 1.0 / (1.0 + np.tan(np.radians(np.clip(slope, 0.1, 89))))

    # Raw depth — how much water converges here
    cell_area = cell_size_m ** 2
    depth = (rainfall_m * runoff_coeff * upstream_area / cell_area) * slope_factor

    # Normalise so the max depth is physically plausible
    # (e.g. max ~3.0 m for extreme events)
    max_theoretical = max(3.0, rainfall_mm / 100.0)
    if depth.max() > 0:
        depth = depth / depth.max() * max_theoretical

    return depth.astype(np.float32)


# =========================================================================
# Cellular automata water spreading
# =========================================================================

def spread_water(
    depth: np.ndarray,
    elevation: np.ndarray,
    iterations: int = 5,
) -> np.ndarray:
    """
    Simple cellular automata: each iteration, water flows from higher
    (elevation + depth) cells to lower neighbours until equilibrium.
    """
    h = elevation + depth  # water surface
    spread = depth.copy()

    offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # 4-connected
    rows, cols = depth.shape

    for _ in range(iterations):
        new_spread = spread.copy()
        for dr, dc in offsets:
            # Shifted view of water surface
            sr = slice(max(0, -dr), rows + min(0, -dr))
            sc = slice(max(0, -dc), cols + min(0, -dc))
            tr = slice(max(0, dr), rows + min(0, dr))
            tc = slice(max(0, dc), cols + min(0, dc))

            # Water flows if neighbour surface is lower
            diff = h[sr, sc] - h[tr, tc]
            transfer = np.clip(diff * 0.25, 0, spread[sr, sc])  # 25 % per step
            new_spread[sr, sc] -= transfer
            new_spread[tr, tc] += transfer

        spread = np.maximum(new_spread, 0)
        h = elevation + spread

    return spread


# =========================================================================
# Flood risk probability (heuristic)
# =========================================================================

def compute_flood_probability(
    depth: np.ndarray,
    flow_accum: np.ndarray,
    slope: np.ndarray,
    rainfall_mm: float,
) -> np.ndarray:
    """
    Combine physical depth with statistical factors to produce a
    0-1 probability of flooding per cell.
    """
    # Depth component (sigmoid)
    depth_prob = 1.0 / (1.0 + np.exp(-5 * (depth - FLOOD_DEPTH_THRESHOLD)))

    # Flow accumulation component (log-normalised)
    fa_log = np.log1p(flow_accum)
    fa_norm = fa_log / (fa_log.max() + 1e-9)

    # Slope component (low slope → high risk)
    slope_norm = 1.0 - np.clip(slope / 45.0, 0, 1)

    # Rainfall severity multiplier
    severity = classify_rainfall(rainfall_mm)
    severity_weight = {
        "none": 0.1,
        "low": 0.4,
        "medium": 0.65,
        "high": 0.85,
        "extreme": 1.0,
    }[severity]

    prob = (
        0.50 * depth_prob
        + 0.25 * fa_norm
        + 0.15 * slope_norm
        + 0.10 * severity_weight
    )
    return np.clip(prob, 0, 1).astype(np.float32)


# =========================================================================
# Full simulation
# =========================================================================

def simulate_flood(
    elevation: np.ndarray,
    flow_accum: np.ndarray,
    slope: np.ndarray,
    meta: dict,
    hourly_rainfall: List[float],
    soil_moisture: float = 0.3,
    timesteps: Optional[List[int]] = None,
    cell_size_m: float = 30.0,
) -> Dict[int, Dict[str, Any]]:
    """
    Run the full flood simulation for multiple time windows.

    Parameters
    ----------
    elevation : 2D array of elevations (metres)
    flow_accum : 2D flow accumulation array
    slope : 2D slope array (degrees)
    meta : DEM metadata dict (must have lat/lon bounds)
    hourly_rainfall : list of hourly precipitation values (mm)
    soil_moisture : current soil moisture fraction (0-1)
    timesteps : list of forecast horizon hours
    cell_size_m : DEM cell resolution in metres

    Returns
    -------
    dict keyed by timestep (hours) → {
        "cumulative_rainfall_mm": float,
        "severity": str,
        "depth": 2D array,
        "probability": 2D array,
        "flooded_mask": 2D bool array,
        "geojson": GeoJSON FeatureCollection,
        "stats": summary statistics dict,
    }
    """
    if timesteps is None:
        timesteps = DEFAULT_TIMESTEPS

    results: Dict[int, Dict[str, Any]] = {}

    for hours in timesteps:
        # Cumulative rainfall for this time window
        cum_rain = sum(hourly_rainfall[: min(hours, len(hourly_rainfall))])
        severity = classify_rainfall(cum_rain)

        logger.info(
            "Simulating t+%dh — cumulative rain %.1f mm (%s)",
            hours, cum_rain, severity,
        )

        # Compute water depth
        depth = compute_water_depth(
            cum_rain, flow_accum, slope, elevation, soil_moisture, cell_size_m
        )

        # Spread water via cellular automata
        depth = spread_water(depth, elevation, iterations=8)

        # Flood probability
        probability = compute_flood_probability(depth, flow_accum, slope, cum_rain)

        # Boolean flood mask
        flooded = depth >= FLOOD_DEPTH_THRESHOLD

        # Stats
        total_cells = elevation.size
        flooded_cells = int(flooded.sum())
        flooded_pct = round(flooded_cells / total_cells * 100, 2)
        max_depth = round(float(depth.max()), 2)
        avg_depth_flooded = (
            round(float(depth[flooded].mean()), 2) if flooded_cells > 0 else 0.0
        )
        affected_area_km2 = round(
            flooded_cells * (cell_size_m ** 2) / 1e6, 2
        )

        stats = {
            "cumulative_rainfall_mm": round(cum_rain, 1),
            "severity": severity,
            "flooded_cells": flooded_cells,
            "flooded_pct": flooded_pct,
            "max_depth_m": max_depth,
            "avg_depth_flooded_m": avg_depth_flooded,
            "affected_area_km2": affected_area_km2,
        }

        # GeoJSON for this timestep
        geojson = _results_to_geojson(
            depth, probability, flooded, elevation, meta, step=5
        )

        results[hours] = {
            "cumulative_rainfall_mm": cum_rain,
            "severity": severity,
            "depth": depth,
            "probability": probability,
            "flooded_mask": flooded,
            "geojson": geojson,
            "stats": stats,
        }

    return results


# =========================================================================
# GeoJSON exporter
# =========================================================================

def _results_to_geojson(
    depth: np.ndarray,
    probability: np.ndarray,
    flooded: np.ndarray,
    elevation: np.ndarray,
    meta: dict,
    step: int = 5,
) -> dict:
    """
    Convert simulation results to a GeoJSON FeatureCollection.
    Only emits cells with non-trivial flood probability (>0.05) to
    keep the payload manageable.
    """
    rows, cols = depth.shape
    lat_min = meta.get("lat_min", 16.4)
    lat_max = meta.get("lat_max", 17.0)
    lon_min = meta.get("lon_min", 73.8)
    lon_max = meta.get("lon_max", 74.6)

    features = []
    for r in range(0, rows, step):
        for c in range(0, cols, step):
            prob = float(probability[r, c])
            if prob < 0.05:
                continue

            lat = lat_max - (r / rows) * (lat_max - lat_min)
            lon = lon_min + (c / cols) * (lon_max - lon_min)
            d = float(depth[r, c])

            risk = "none"
            if prob >= 0.8:
                risk = "extreme"
            elif prob >= 0.6:
                risk = "high"
            elif prob >= 0.35:
                risk = "medium"
            elif prob >= 0.15:
                risk = "low"

            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
                    "properties": {
                        "depth_m": round(d, 2),
                        "probability": round(prob, 3),
                        "risk_level": risk,
                        "elevation_m": round(float(elevation[r, c]), 1),
                        "flooded": bool(flooded[r, c]),
                    },
                }
            )

    return {"type": "FeatureCollection", "features": features}
