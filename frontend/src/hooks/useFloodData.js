/**
 * useFloodData.js — Fetches flood prediction from backend
 *
 * Calls POST /api/simulate
 * Returns: GeoJSON FeatureCollection for current time step
 * Caches all time steps on first load
 */

import { useState, useEffect } from 'react';

const useFloodData = (lat, lon, radiusKm, forecastHour) => {
  const [floodData, setFloodData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // TODO: Implement flood data fetching from /api/simulate
    // Cache all time steps on first load
  }, [lat, lon, radiusKm, forecastHour]);

  return { floodData, loading, error };
};

export default useFloodData;
