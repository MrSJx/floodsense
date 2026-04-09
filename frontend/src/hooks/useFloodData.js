/**
 * useFloodData.js — Flood simulation API hook
 *
 * Calls POST /api/simulate
 * Returns: GeoJSON FeatureCollection for selected time step
 * Caches all time steps on first load
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000';

const useFloodData = (lat, lon, radiusKm = 25, forecastHour = 24) => {
  const [allTimesteps, setAllTimesteps] = useState(null);
  const [currentData, setCurrentData] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const cacheRef = useRef(null);

  const fetchSimulation = useCallback(async () => {
    if (!lat || !lon) return;
    try {
      setLoading(true);
      setError(null);

      const res = await axios.post(
        `${API_BASE}/api/simulate`,
        {
          lat,
          lon,
          radius_km: radiusKm,
          forecast_hours: [6, 12, 24, 72],
        },
        { timeout: 30000 }
      );

      const timesteps = res.data.timesteps || {};
      cacheRef.current = timesteps;
      setAllTimesteps(timesteps);

      // Set current data based on selected forecast hour
      const key = String(forecastHour);
      if (timesteps[key]) {
        setCurrentData(timesteps[key].geojson);
        setStats(timesteps[key].stats);
      }
    } catch (err) {
      console.error('Flood simulation error:', err);
      setError(err.message || 'Failed to run flood simulation');
    } finally {
      setLoading(false);
    }
  }, [lat, lon, radiusKm]);

  // Fetch on mount or when location changes
  useEffect(() => {
    fetchSimulation();
  }, [fetchSimulation]);

  // Switch timestep from cache without re-fetching
  useEffect(() => {
    if (cacheRef.current) {
      const key = String(forecastHour);
      const ts = cacheRef.current[key];
      if (ts) {
        setCurrentData(ts.geojson);
        setStats(ts.stats);
      }
    }
  }, [forecastHour]);

  return {
    floodData: currentData,
    allTimesteps,
    stats,
    loading,
    error,
    refetch: fetchSimulation,
  };
};

export default useFloodData;
