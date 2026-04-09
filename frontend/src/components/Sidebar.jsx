/**
 * Sidebar.jsx — Controls, legend, and layer toggles
 *
 * Features:
 *   - Layer toggles (terrain, flood risk)
 *   - District selector
 *   - Risk level legend
 *   - Coordinate display
 */

import React, { useState } from 'react';
import {
  Layers,
  Mountain,
  Waves,
  Info,
  ChevronDown,
  ChevronUp,
  Map as MapIcon,
  Compass,
} from 'lucide-react';

const DISTRICTS = ['Kolhapur', 'Raigad', 'Sangli', 'Satara'];

const LEGEND_ITEMS = [
  { color: '#7f1d1d', label: 'Extreme Risk', desc: '≥ 204mm' },
  { color: '#ef4444', label: 'High Risk', desc: '≥ 115mm' },
  { color: '#f97316', label: 'Medium Risk', desc: '≥ 65mm' },
  { color: '#eab308', label: 'Low Risk', desc: '≥ 30mm' },
  { color: '#22c55e', label: 'Safe', desc: '< 30mm' },
];

export default function Sidebar({
  showTerrain,
  showFlood,
  onToggleTerrain,
  onToggleFlood,
  district,
  onDistrictChange,
  center,
}) {
  const [legendOpen, setLegendOpen] = useState(true);
  const [layersOpen, setLayersOpen] = useState(true);

  return (
    <div className="sidebar">
      {/* Logo / Title */}
      <div className="sidebar-brand">
        <div className="sidebar-logo">
          <Waves size={22} className="logo-icon" />
          <div>
            <h2 className="sidebar-title">FloodSense</h2>
            <span className="sidebar-subtitle">Terrain-Aware Prediction</span>
          </div>
        </div>
      </div>

      {/* District selector */}
      <div className="sidebar-section">
        <label className="sidebar-label">
          <Compass size={14} />
          District
        </label>
        <select
          className="sidebar-select"
          value={district}
          onChange={(e) => onDistrictChange(e.target.value)}
        >
          {DISTRICTS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      {/* Layer toggles */}
      <div className="sidebar-section">
        <button
          className="sidebar-section-header"
          onClick={() => setLayersOpen(!layersOpen)}
        >
          <Layers size={14} />
          <span>Map Layers</span>
          {layersOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {layersOpen && (
          <div className="sidebar-toggles animate-fade-in">
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={showTerrain}
                onChange={onToggleTerrain}
              />
              <Mountain size={14} />
              <span>Terrain Elevation</span>
            </label>
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={showFlood}
                onChange={onToggleFlood}
              />
              <Waves size={14} />
              <span>Flood Risk Overlay</span>
            </label>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="sidebar-section">
        <button
          className="sidebar-section-header"
          onClick={() => setLegendOpen(!legendOpen)}
        >
          <Info size={14} />
          <span>Risk Legend</span>
          {legendOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {legendOpen && (
          <div className="legend-list animate-fade-in">
            {LEGEND_ITEMS.map((item) => (
              <div key={item.label} className="legend-item">
                <span
                  className="legend-dot"
                  style={{ background: item.color }}
                />
                <span className="legend-label">{item.label}</span>
                <span className="legend-desc">{item.desc}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Coordinates */}
      {center && (
        <div className="sidebar-section sidebar-coords">
          <MapIcon size={12} />
          <span className="data-value" style={{ fontSize: 11 }}>
            {center[0].toFixed(4)}°N, {center[1].toFixed(4)}°E
          </span>
        </div>
      )}

      {/* Footer */}
      <div className="sidebar-footer">
        <span>AKARI | Pune Agri Hackathon</span>
        <span>v1.0.0</span>
      </div>
    </div>
  );
}
