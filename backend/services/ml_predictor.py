"""
ml_predictor.py — XGBoost risk score model

Feature Vector per grid cell:
  - elevation_m
  - slope_degrees
  - flow_accumulation
  - distance_to_river_m
  - soil_moisture
  - rainfall_24h_mm
  - rainfall_72h_mm
  - land_cover_type (0=water, 1=urban, 2=cropland, 3=forest)
  - antecedent_rainfall_7d

Target: binary classification (flooded=1, not-flooded=0)
Model: XGBoost with >85% recall on flood class
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "xgb_flood_model.pkl"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLUMNS = [
    "elevation_m",
    "slope_degrees",
    "flow_accumulation",
    "distance_to_river_m",
    "soil_moisture",
    "rainfall_24h_mm",
    "rainfall_72h_mm",
    "land_cover_type",
    "antecedent_rainfall_7d",
]

# ---------------------------------------------------------------------------
# Optional imports
# ---------------------------------------------------------------------------
try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    logger.warning("xgboost not installed — ML predictions will use heuristic fallback")

try:
    import joblib
    HAS_JOBLIB = True
except ImportError:
    HAS_JOBLIB = False
    try:
        import pickle as joblib  # noqa: F811
        HAS_JOBLIB = True
    except Exception:
        pass


# =========================================================================
# Training
# =========================================================================

def train_model(
    X: pd.DataFrame,
    y: np.ndarray,
    save_path: Optional[str] = None,
    **xgb_kwargs,
) -> Any:
    """
    Train an XGBoost binary classifier for flood prediction.

    Parameters
    ----------
    X : DataFrame with columns matching FEATURE_COLUMNS
    y : 1-D array with labels (1 = flooded, 0 = not flooded)
    save_path : where to persist the model (default: MODEL_PATH)

    Returns the fitted model.
    """
    if not HAS_XGBOOST:
        raise ImportError("xgboost is required for training")

    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, roc_auc_score

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Handle class imbalance — flooded cells are rare
    pos = int(y_train.sum())
    neg = len(y_train) - pos
    scale_pos_weight = neg / max(pos, 1)

    defaults = dict(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
    )
    defaults.update(xgb_kwargs)

    model = XGBClassifier(**defaults)
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # Evaluation
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    report = classification_report(y_test, y_pred, target_names=["safe", "flooded"])
    auc = roc_auc_score(y_test, y_prob)
    logger.info("Classification Report:\n%s", report)
    logger.info("ROC-AUC: %.4f", auc)

    # Persist
    save_path = Path(save_path) if save_path else MODEL_PATH
    save_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, save_path)
    logger.info("Model saved → %s", save_path)

    return model


# =========================================================================
# Inference
# =========================================================================

_cached_model = None


def _load_model(model_path: Optional[str] = None) -> Any:
    """Load the XGBoost model, caching it for repeated calls."""
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    path = Path(model_path) if model_path else MODEL_PATH
    if not path.exists():
        logger.warning("No trained model at %s — will train on synthetic data", path)
        _train_on_synthetic()
        if not path.exists():
            return None

    _cached_model = joblib.load(path)
    logger.info("Model loaded from %s", path)
    return _cached_model


def predict_flood_risk(
    feature_grid: pd.DataFrame,
    model_path: Optional[str] = None,
) -> np.ndarray:
    """
    Predict flood probability (0-1) for every row in feature_grid.

    Falls back to a heuristic score if XGBoost is unavailable.
    """
    model = _load_model(model_path)

    if model is not None and HAS_XGBOOST:
        # Ensure correct column order
        X = feature_grid[FEATURE_COLUMNS].copy()
        probabilities = model.predict_proba(X)[:, 1]
        return probabilities.astype(np.float32)

    # ---- Heuristic fallback -----------------------------------------------
    return _heuristic_flood_risk(feature_grid)


def _heuristic_flood_risk(df: pd.DataFrame) -> np.ndarray:
    """
    Rule-based flood risk estimator used when no trained model exists.
    Returns probability 0-1 per row.
    """
    prob = np.zeros(len(df), dtype=np.float32)

    # Normalise features to 0-1 range safely
    def _norm(col):
        s = df[col] if col in df.columns else pd.Series(0, index=df.index)
        mn, mx = s.min(), s.max()
        if mx - mn < 1e-9:
            return np.zeros(len(s))
        return ((s - mn) / (mx - mn)).values

    fa = _norm("flow_accumulation")
    slp = 1.0 - _norm("slope_degrees")  # low slope → high risk
    elev = 1.0 - _norm("elevation_m")   # low elevation → high risk

    rain_24 = df.get("rainfall_24h_mm", pd.Series(0, index=df.index)).values / 200.0
    rain_72 = df.get("rainfall_72h_mm", pd.Series(0, index=df.index)).values / 500.0
    soil = df.get("soil_moisture", pd.Series(0.3, index=df.index)).values

    prob = (
        0.25 * np.clip(fa, 0, 1)
        + 0.15 * np.clip(slp, 0, 1)
        + 0.10 * np.clip(elev, 0, 1)
        + 0.20 * np.clip(rain_24, 0, 1)
        + 0.15 * np.clip(rain_72, 0, 1)
        + 0.15 * np.clip(soil, 0, 1)
    )
    return np.clip(prob, 0, 1).astype(np.float32)


# =========================================================================
# Feature engineering helper
# =========================================================================

def build_feature_grid(
    elevation: np.ndarray,
    slope: np.ndarray,
    flow_accum: np.ndarray,
    rainfall_24h: float,
    rainfall_72h: float,
    soil_moisture: float = 0.3,
    antecedent_rain_7d: float = 50.0,
    distance_to_river: Optional[np.ndarray] = None,
    land_cover: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """
    Flatten 2-D raster arrays into a DataFrame with the expected
    feature columns so it can be fed straight to predict_flood_risk().
    """
    rows, cols = elevation.shape
    n = rows * cols

    if distance_to_river is None:
        # Proxy: cells with high flow accumulation are close to rivers
        fa_log = np.log1p(flow_accum)
        distance_to_river = np.clip(5000 - fa_log / fa_log.max() * 5000, 100, 10000)

    if land_cover is None:
        land_cover = np.full_like(elevation, 2, dtype=np.int8)  # default: cropland

    df = pd.DataFrame(
        {
            "elevation_m": elevation.ravel(),
            "slope_degrees": slope.ravel(),
            "flow_accumulation": flow_accum.ravel(),
            "distance_to_river_m": distance_to_river.ravel(),
            "soil_moisture": np.full(n, soil_moisture),
            "rainfall_24h_mm": np.full(n, rainfall_24h),
            "rainfall_72h_mm": np.full(n, rainfall_72h),
            "land_cover_type": land_cover.ravel(),
            "antecedent_rainfall_7d": np.full(n, antecedent_rain_7d),
        }
    )
    return df


# =========================================================================
# Synthetic training data (for demo when real flood data is unavailable)
# =========================================================================

def _train_on_synthetic(n_samples: int = 10_000) -> None:
    """Generate synthetic labelled data and train a model for demo."""
    if not HAS_XGBOOST:
        logger.warning("Cannot train synthetic model — xgboost not installed")
        return

    logger.info("Generating %d synthetic training samples …", n_samples)
    np.random.seed(42)

    df = pd.DataFrame(
        {
            "elevation_m": np.random.uniform(50, 1200, n_samples),
            "slope_degrees": np.random.exponential(5, n_samples),
            "flow_accumulation": np.random.exponential(500, n_samples),
            "distance_to_river_m": np.random.exponential(3000, n_samples),
            "soil_moisture": np.random.uniform(0.1, 0.6, n_samples),
            "rainfall_24h_mm": np.random.exponential(40, n_samples),
            "rainfall_72h_mm": np.random.exponential(100, n_samples),
            "land_cover_type": np.random.choice([0, 1, 2, 3], n_samples, p=[0.05, 0.15, 0.6, 0.2]),
            "antecedent_rainfall_7d": np.random.exponential(60, n_samples),
        }
    )

    # Synthetic label: flood if low elevation + high rain + high flow accum + low slope
    flood_score = (
        - 0.003 * df["elevation_m"]
        - 0.05 * df["slope_degrees"]
        + 0.001 * df["flow_accumulation"]
        - 0.0002 * df["distance_to_river_m"]
        + 2.0 * df["soil_moisture"]
        + 0.01 * df["rainfall_24h_mm"]
        + 0.005 * df["rainfall_72h_mm"]
        + 0.005 * df["antecedent_rainfall_7d"]
    )
    threshold = np.percentile(flood_score, 80)  # ~20% flood rate
    y = (flood_score >= threshold).astype(int).values

    train_model(df, y)
    logger.info("Synthetic model training complete ✓")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _train_on_synthetic()
    print(f"Model saved at: {MODEL_PATH}")
