/**
 * useWeatherData.js — Weather API hook
 *
 * Calls GET /api/weather
 * Returns: rainfall forecast, cumulative values, soil moisture
 * Auto-refreshes every 30 minutes
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000';
const REFRESH_INTERVAL = 30 * 60 * 1000; // 30 minutes

const useWeatherData = (lat, lon, days = 3) => {
  const [weatherData, setWeatherData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const intervalRef = useRef(null);

  const fetchWeather = useCallback(async () => {
    if (!lat || !lon) return;
    try {
      setLoading(true);
      setError(null);
      const res = await axios.get(`${API_BASE}/api/weather`, {
        params: { lat, lon, days },
        timeout: 15000,
      });
      setWeatherData(res.data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Weather fetch error:', err);
      setError(err.message || 'Failed to fetch weather data');
    } finally {
      setLoading(false);
    }
  }, [lat, lon, days]);

  useEffect(() => {
    fetchWeather();

    // Auto-refresh
    intervalRef.current = setInterval(fetchWeather, REFRESH_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchWeather]);

  return { weatherData, loading, error, lastUpdated, refetch: fetchWeather };
};

export default useWeatherData;
