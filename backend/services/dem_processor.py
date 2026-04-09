"""
dem_processor.py — DEM loading, flow direction, and flow accumulation

Steps:
  A. Load and clip DEM to Maharashtra boundary
  B. Sink filling using RichDEM
  C. Flow Direction (D8 method)
  D. Flow Accumulation
  E. Slope Calculation
  F. Export to GeoJSON grid

Handles graceful fallback to synthetic DEM when real data or RichDEM
is unavailable (common on Windows / hackathon setups).
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEM_PATH = DATA_DIR / "maharashtra_dem.tif"
BOUNDARY_PATH = DATA_DIR / "maharashtra_boundary.geojson"
PROCESSED_DIR = DATA_DIR / "processed"

# Ensure processed output directory exists
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Attempt optional heavy imports — fall back gracefully
# ---------------------------------------------------------------------------
try:
    import rasterio
    from rasterio.mask import mask as rasterio_mask
    from rasterio.transform import from_bounds
    from rasterio.warp import calculate_default_transform, reproject, Resampling

    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False
    logger.warning("rasterio not available — will use synthetic DEM")

try:
    import geopandas as gpd

    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False

try:
    import richdem as rd

    HAS_RICHDEM = True
except ImportError:
    HAS_RICHDEM = False
    logger.warning("richdem not available — will use numpy-based fallback")

from scipy.ndimage import uniform_filter


# =========================================================================
# A. Load and clip DEM
# =========================================================================

def load_and_clip_dem(
    dem_path: Optional[str] = None,
    boundary_path: Optional[str] = None,
    target_crs: str = "EPSG:32643",
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Load a GeoTIFF DEM, clip to boundary, reproject to UTM 43N,
    and fill NoData.  Returns (elevation_array, metadata_dict).

    If the real DEM is missing, generates a synthetic terrain that
    looks like western Maharashtra (coastal plain rising to Sahyadri
    escarpment then Deccan plateau).
    """
    dem_path = Path(dem_path) if dem_path else DEM_PATH
    boundary_path = Path(boundary_path) if boundary_path else BOUNDARY_PATH

    if HAS_RASTERIO and dem_path.exists():
        return _load_real_dem(dem_path, boundary_path, target_crs)

    logger.info("Real DEM not found — generating synthetic terrain for demo")
    return _generate_synthetic_dem()


def _load_real_dem(
    dem_path: Path, boundary_path: Path, target_crs: str
) -> Tuple[np.ndarray, dict]:
    """Load, clip, and reproject a real GeoTIFF DEM."""
    with rasterio.open(dem_path) as src:
        # ---- Clip to boundary if available ---------------------------------
        if HAS_GEOPANDAS and boundary_path.exists():
            boundary = gpd.read_file(boundary_path)
            boundary = boundary.to_crs(src.crs)
            shapes = boundary.geometry.values
            out_image, out_transform = rasterio_mask(src, shapes, crop=True)
            out_image = out_image[0]  # single band
            meta = src.meta.copy()
            meta.update(
                {
                    "height": out_image.shape[0],
                    "width": out_image.shape[1],
                    "transform": out_transform,
                }
            )
        else:
            out_image = src.read(1)
            meta = src.meta.copy()

        # ---- Reproject to target CRS (UTM 43N) ----------------------------
        dst_crs = target_crs
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, meta["width"], meta["height"],
            *rasterio.transform.array_bounds(
                meta["height"], meta["width"], meta["transform"]
            ),
        )
        reprojected = np.empty((height, width), dtype=np.float32)
        reproject(
            source=out_image,
            destination=reprojected,
            src_transform=meta["transform"],
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear,
        )
        meta.update(
            {
                "crs": dst_crs,
                "transform": transform,
                "width": width,
                "height": height,
            }
        )

    # ---- Fill NoData -------------------------------------------------------
    nodata = meta.get("nodata", -9999)
    mask = (reprojected == nodata) | np.isnan(reprojected)
    if mask.any():
        reprojected[mask] = np.nanmedian(reprojected[~mask])

    return reprojected, meta


def _generate_synthetic_dem(
    rows: int = 200, cols: int = 200
) -> Tuple[np.ndarray, dict]:
    """
    Create a plausible synthetic DEM centered on Kolhapur district
    (lat ≈ 16.7°N, lon ≈ 74.2°E).

    The terrain models:
      • Western Ghats escarpment (high elevations in the west)
      • Panchganga / Krishna river valley (low trough running E-W)
      • Random hills and micro-topography
    """
    np.random.seed(42)

    # Bounding box — roughly Kolhapur district
    lat_min, lat_max = 16.4, 17.0
    lon_min, lon_max = 73.8, 74.6

    y = np.linspace(0, 1, rows)
    x = np.linspace(0, 1, cols)
    xx, yy = np.meshgrid(x, y)

    # Base: elevation rises from east to west (Western Ghats on western edge)
    base = 500 + 600 * (1 - xx)  # 500 m east → 1100 m west

    # River valley — sinusoidal trough running roughly east-west at y ≈ 0.45
    valley = -120 * np.exp(-((yy - 0.45) ** 2) / 0.01)

    # Some rounded hills
    hill1 = 80 * np.exp(-(((xx - 0.3) ** 2 + (yy - 0.7) ** 2) / 0.02))
    hill2 = 60 * np.exp(-(((xx - 0.6) ** 2 + (yy - 0.3) ** 2) / 0.015))

    # Random micro-topography (smoothed noise)
    noise = uniform_filter(np.random.randn(rows, cols) * 15, size=8)

    dem = (base + valley + hill1 + hill2 + noise).astype(np.float32)

    meta = {
        "rows": rows,
        "cols": cols,
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max,
        "crs": "EPSG:4326",
        "pixel_size_lat": (lat_max - lat_min) / rows,
        "pixel_size_lon": (lon_max - lon_min) / cols,
        "synthetic": True,
    }
    return dem, meta


# =========================================================================
# B. Sink Filling
# =========================================================================

def fill_sinks(dem: np.ndarray) -> np.ndarray:
    """
    Fill sinks / depressions so water doesn't pool in artificial pits.
    Uses RichDEM when available, otherwise a simple iterative fill.
    """
    if HAS_RICHDEM:
        rda = rd.rdarray(dem, no_data=-9999)
        filled = rd.FillDepressions(rda)
        return np.array(filled, dtype=np.float32)

    # Fallback — priority-flood-like iterative fill (simplified)
    return _simple_fill(dem)


def _simple_fill(dem: np.ndarray, max_iter: int = 50) -> np.ndarray:
    """Iterative sink-fill approximation using a 3×3 max filter approach."""
    from scipy.ndimage import maximum_filter

    filled = dem.copy()
    for _ in range(max_iter):
        local_max = maximum_filter(filled, size=3)
        pits = filled < local_max - 0.5  # cells >0.5 m below neighbours
        if not pits.any():
            break
        filled[pits] = local_max[pits] - 0.01
    return filled


# =========================================================================
# C. Flow Direction (D8)
# =========================================================================

_D8_OFFSETS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]
_D8_DIST = [
    np.sqrt(2), 1.0, np.sqrt(2),
    1.0,              1.0,
    np.sqrt(2), 1.0, np.sqrt(2),
]


def flow_direction_d8(dem: np.ndarray) -> np.ndarray:
    """
    Compute D8 flow direction for every cell.
    Returns an array where the value 0-7 indicates which of the 8
    neighbours the cell drains to (steepest descent). -1 = flat/pit.
    """
    if HAS_RICHDEM:
        rda = rd.rdarray(dem, no_data=-9999)
        fd = rd.FlowDirectionD8(rda)
        return np.array(fd, dtype=np.int8)

    rows, cols = dem.shape
    flow_dir = np.full((rows, cols), -1, dtype=np.int8)

    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            max_slope = 0.0
            max_dir = -1
            for idx, (dr, dc) in enumerate(_D8_OFFSETS):
                drop = dem[r, c] - dem[r + dr, c + dc]
                slope = drop / _D8_DIST[idx]
                if slope > max_slope:
                    max_slope = slope
                    max_dir = idx
            flow_dir[r, c] = max_dir

    return flow_dir


# =========================================================================
# D. Flow Accumulation
# =========================================================================

def flow_accumulation(dem: np.ndarray, flow_dir: np.ndarray) -> np.ndarray:
    """
    Compute flow accumulation: each cell's value = number of upstream
    cells draining into it.
    High accumulation = natural drainage channels = flood risk corridors.
    """
    if HAS_RICHDEM:
        rda = rd.rdarray(dem, no_data=-9999)
        accum = rd.FlowAccumulation(rda, method="D8")
        return np.array(accum, dtype=np.float32)

    rows, cols = dem.shape
    accum = np.ones((rows, cols), dtype=np.float32)  # each cell counts itself

    # Topological sort by descending elevation
    indices = np.argsort(dem, axis=None)[::-1]

    for flat_idx in indices:
        r, c = divmod(int(flat_idx), cols)
        d = flow_dir[r, c]
        if d < 0:
            continue
        dr, dc = _D8_OFFSETS[d]
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            accum[nr, nc] += accum[r, c]

    return accum


# =========================================================================
# E. Slope Calculation
# =========================================================================

def calculate_slope(dem: np.ndarray, cell_size: float = 30.0) -> np.ndarray:
    """
    Calculate slope in degrees from DEM.
    Flat areas (low slope) accumulate water → higher flood risk.

    Parameters
    ----------
    dem : 2-D elevation array
    cell_size : pixel resolution in metres (default 30 m ≈ SRTM)
    """
    if HAS_RICHDEM:
        rda = rd.rdarray(dem, no_data=-9999)
        slope = rd.TerrainAttribute(rda, attrib="slope_degrees")
        return np.array(slope, dtype=np.float32)

    # NumPy gradient fallback
    dy, dx = np.gradient(dem, cell_size)
    slope_rad = np.arctan(np.sqrt(dx ** 2 + dy ** 2))
    return np.degrees(slope_rad).astype(np.float32)


# =========================================================================
# F. Export to GeoJSON Grid
# =========================================================================

def dem_to_geojson(
    dem: np.ndarray,
    flow_accum: np.ndarray,
    slope: np.ndarray,
    meta: dict,
    step: int = 5,
) -> dict:
    """
    Convert raster results to a GeoJSON FeatureCollection of point features.

    Each feature contains:
      • elevation, flow_accumulation, slope
      • lat / lon coordinates

    Parameters
    ----------
    step : int
        Sample every `step`-th cell to keep the GeoJSON manageable.
    """
    rows, cols = dem.shape
    lat_min = meta.get("lat_min", 16.4)
    lat_max = meta.get("lat_max", 17.0)
    lon_min = meta.get("lon_min", 73.8)
    lon_max = meta.get("lon_max", 74.6)

    features = []
    for r in range(0, rows, step):
        for c in range(0, cols, step):
            lat = lat_max - (r / rows) * (lat_max - lat_min)
            lon = lon_min + (c / cols) * (lon_max - lon_min)
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "elevation": round(float(dem[r, c]), 1),
                        "flow_accumulation": round(float(flow_accum[r, c]), 1),
                        "slope": round(float(slope[r, c]), 2),
                    },
                }
            )

    return {"type": "FeatureCollection", "features": features}


# =========================================================================
# High-level pipeline
# =========================================================================

def process_dem(
    dem_path: Optional[str] = None,
    boundary_path: Optional[str] = None,
    export_geojson: bool = True,
) -> Dict[str, Any]:
    """
    Run the full DEM processing pipeline and return all products.

    Returns dict with keys:
        dem, filled_dem, flow_dir, flow_accum, slope, meta, geojson
    """
    logger.info("Step A — Loading DEM …")
    dem, meta = load_and_clip_dem(dem_path, boundary_path)

    logger.info("Step B — Filling sinks …")
    filled = fill_sinks(dem)

    logger.info("Step C — Computing flow direction …")
    fd = flow_direction_d8(filled)

    logger.info("Step D — Computing flow accumulation …")
    fa = flow_accumulation(filled, fd)

    logger.info("Step E — Computing slope …")
    slp = calculate_slope(filled)

    result = {
        "dem": dem,
        "filled_dem": filled,
        "flow_dir": fd,
        "flow_accum": fa,
        "slope": slp,
        "meta": meta,
    }

    if export_geojson:
        logger.info("Step F — Exporting to GeoJSON …")
        geojson = dem_to_geojson(filled, fa, slp, meta)
        result["geojson"] = geojson

        out_path = PROCESSED_DIR / "terrain.geojson"
        with open(out_path, "w") as f:
            json.dump(geojson, f)
        logger.info(f"Saved terrain GeoJSON → {out_path}")

    logger.info("DEM processing complete ✓")
    return result


# ---------------------------------------------------------------------------
# CLI entry point for stand-alone testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    products = process_dem()
    print(f"DEM shape : {products['dem'].shape}")
    print(f"Features  : {len(products['geojson']['features'])}")
