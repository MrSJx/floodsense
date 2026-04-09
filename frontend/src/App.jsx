/**
 * App.jsx — Root component for FloodSense
 *
 * Assembles the full dashboard:
 *   - StatsBar (top metrics)
 *   - Sidebar (left — controls, legend)
 *   - Map (centre — Leaflet map with overlays)
 *   - Timeline (bottom — forecast time selector)
 *   - AlertPanel (right — flood alerts)
 */

import React, { useState, useEffect, useCallback } from 'react';
import FloodMap from './components/Map';
import Timeline from './components/Timeline';
import AlertPanel from './components/AlertPanel';
import StatsBar from './components/StatsBar';
import Sidebar from './components/Sidebar';
import RiskOverlay from './components/RiskOverlay';
import useWeatherData from './hooks/useWeatherData';
import useFloodData from './hooks/useFloodData';
import useAlerts from './hooks/useAlerts';
import './App.css';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000';

/* District centre coordinates */
const DISTRICT_CENTERS = {
  Kolhapur: [16.7, 74.2],
  Raigad: [18.52, 73.18],
  Sangli: [16.85, 74.56],
  Satara: [17.68, 74.0],
};

function App() {
  /* ── State ──────────────────────────────────────────────── */
  const [district, setDistrict] = useState('Kolhapur');
  const [selectedHour, setSelectedHour] = useState(24);
  const [showTerrain, setShowTerrain] = useState(true);
  const [showFlood, setShowFlood] = useState(true);
  const [terrainGeojson, setTerrainGeojson] = useState(null);
  const [flyTo, setFlyTo] = useState(null);

  const center = DISTRICT_CENTERS[district] || DISTRICT_CENTERS.Kolhapur;

  /* ── API hooks ──────────────────────────────────────────── */
  const {
    weatherData,
    loading: weatherLoading,
    lastUpdated: weatherUpdated,
  } = useWeatherData(center[0], center[1]);

  const {
    floodData,
    stats: floodStats,
    loading: floodLoading,
  } = useFloodData(center[0], center[1], 25, selectedHour);

  const {
    alerts,
    alertCount,
    loading: alertsLoading,
  } = useAlerts(district);

  /* ── Fetch terrain on mount ─────────────────────────────── */
  useEffect(() => {
    const fetchTerrain = async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/terrain`, {
          params: { lat: center[0], lon: center[1], radius_km: 50 },
        });
        setTerrainGeojson(res.data?.terrain || null);
      } catch (err) {
        console.error('Terrain fetch error:', err);
      }
    };
    fetchTerrain();
  }, [center]);

  /* ── Handlers ───────────────────────────────────────────── */
  const handleZoomTo = useCallback((coords) => {
    setFlyTo(coords);
    // Reset after fly animation
    setTimeout(() => setFlyTo(null), 2000);
  }, []);

  const handleDistrictChange = useCallback((d) => {
    setDistrict(d);
    setFlyTo(DISTRICT_CENTERS[d]);
    setTimeout(() => setFlyTo(null), 2000);
  }, []);

  /* ── Loading state ──────────────────────────────────────── */
  const isLoading = weatherLoading && floodLoading;

  /* ── Render ─────────────────────────────────────────────── */
  return (
    <div className="app">
      {/* Top stats bar */}
      <StatsBar
        weatherData={weatherData}
        floodStats={floodStats}
        alertCount={alertCount}
        lastUpdated={weatherUpdated}
        loading={isLoading}
      />

      {/* Main content area */}
      <div className="app-main">
        {/* Left sidebar */}
        <Sidebar
          showTerrain={showTerrain}
          showFlood={showFlood}
          onToggleTerrain={() => setShowTerrain(!showTerrain)}
          onToggleFlood={() => setShowFlood(!showFlood)}
          district={district}
          onDistrictChange={handleDistrictChange}
          center={center}
        />

        {/* Map area */}
        <div className="app-map-area">
          <FloodMap
            floodGeojson={floodData}
            terrainGeojson={terrainGeojson}
            center={center}
            zoom={10}
            showTerrain={showTerrain}
            showFlood={showFlood}
            flyTo={flyTo}
          />

          {/* Risk badge overlay */}
          <div className="map-risk-badge">
            <RiskOverlay severity={floodStats?.severity || 'none'} />
          </div>

          {/* Loading indicator */}
          {floodLoading && (
            <div className="map-loading">
              <div className="map-loading-spinner" />
              <span>Running simulation…</span>
            </div>
          )}

          {/* Timeline at bottom of map */}
          <div className="map-timeline">
            <Timeline
              selectedHour={selectedHour}
              onSelect={setSelectedHour}
              lastUpdated={weatherUpdated}
            />
          </div>
        </div>

        {/* Right alert panel */}
        <AlertPanel
          alerts={alerts}
          loading={alertsLoading}
          onZoomTo={handleZoomTo}
        />
      </div>
    </div>
  );
}

export default App;
