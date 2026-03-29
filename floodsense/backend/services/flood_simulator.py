"""
flood_simulator.py — Core flood simulation logic

Algorithm:
  1. Load pre-processed DEM attributes (flow accumulation, slope, elevation)
  2. Get rainfall forecast from weather fetcher for region
  3. For each time step (6h, 12h, 24h, 72h):
     a. Compute cumulative rainfall for that window
     b. Adjust for soil moisture (saturated soil = faster runoff)
     c. Apply rainfall to flow accumulation grid
     d. Mark cells as flooded if estimated water depth > threshold (0.3m)
     e. Spread water to adjacent lower cells (cellular automata)
  4. Output: GeoJSON with flood probability + estimated depth per cell per time step

Thresholds:
  low:     rainfall_mm >= 30   (Yellow zone)
  medium:  rainfall_mm >= 65   (Orange zone)
  high:    rainfall_mm >= 115  (Red zone — IMD heavy rain)
  extreme: rainfall_mm >= 204  (Dark red — IMD extremely heavy rain)
"""

# TODO: Implement in Phase 2 (Execution Order Step 4)
# See flood_project_build.md Task 2.3 for detailed implementation steps
