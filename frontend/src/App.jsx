/**
 * App.jsx — Root component for FloodSense
 * 
 * Assembles:
 *   - Map (main Leaflet/MapLibre map)
 *   - RiskOverlay (color-coded flood risk layer)
 *   - Timeline (6h/12h/24h/72h forecast toggle)
 *   - AlertPanel (high-risk zone alerts)
 *   - StatsBar (rainfall, risk %, affected area)
 *   - Sidebar (controls and legend)
 */

import React from 'react';

function App() {
  return (
    <div className="app">
      <h1>FloodSense</h1>
      <p>Terrain-Aware Flood Prediction &amp; Simulation Platform</p>
      {/* Components will be assembled here */}
    </div>
  );
}

export default App;
