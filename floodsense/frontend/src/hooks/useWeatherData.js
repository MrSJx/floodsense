/**
 * useWeatherData.js — Fetches Open-Meteo API
 *
 * Calls GET /api/weather
 * Returns: rainfall forecast array, current soil moisture, hourly precipitation
 * Refreshes every 30 minutes
 */

import { useState, useEffect } from 'react';

const useWeatherData = (lat, lon) => {
  const [weatherData, setWeatherData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // TODO: Implement weather data fetching from /api/weather
    // Refresh every 30 minutes
  }, [lat, lon]);

  return { weatherData, loading, error };
};

export default useWeatherData;
