/**
 * StatsBar.jsx — Top metrics bar showing live statistics
 *
 * Displays: Rainfall, at-risk villages, farmland affected,
 * roads flooded, last updated time.
 */

import React from 'react';
import {
  CloudRain,
  AlertTriangle,
  Wheat,
  Route,
  Clock,
  Droplets,
  Activity,
} from 'lucide-react';

export default function StatsBar({
  weatherData,
  floodStats,
  alertCount,
  lastUpdated,
  loading,
}) {
  const cumRain = weatherData?.cumulative_rainfall || {};
  const rain24 = cumRain['24h_mm'] || 0;
  const soil = weatherData?.current_soil_moisture;
  const floodedPct = floodStats?.flooded_pct || 0;
  const affectedArea = floodStats?.affected_area_km2 || 0;
  const maxDepth = floodStats?.max_depth_m || 0;
  const severity = floodStats?.severity || 'none';

  const severityColor = {
    none: 'var(--color-safe)',
    low: 'var(--color-low)',
    medium: 'var(--color-medium)',
    high: 'var(--color-high)',
    extreme: 'var(--color-extreme)',
  }[severity];

  const stats = [
    {
      icon: <CloudRain size={16} />,
      label: 'Rainfall (24h)',
      value: `${rain24}mm`,
      color: rain24 > 65 ? 'var(--color-high)' : 'var(--color-accent)',
    },
    {
      icon: <Droplets size={16} />,
      label: 'Soil Moisture',
      value: soil != null ? `${(soil * 100).toFixed(0)}%` : '—',
      color: 'var(--color-water)',
    },
    {
      icon: <AlertTriangle size={16} />,
      label: 'Active Alerts',
      value: alertCount || 0,
      color: alertCount > 0 ? 'var(--color-high)' : 'var(--color-safe)',
    },
    {
      icon: <Activity size={16} />,
      label: 'Severity',
      value: severity.toUpperCase(),
      color: severityColor,
    },
    {
      icon: <Wheat size={16} />,
      label: 'Area Affected',
      value: `${affectedArea} km²`,
      color: affectedArea > 10 ? 'var(--color-medium)' : 'var(--text-secondary)',
    },
    {
      icon: <Route size={16} />,
      label: 'Max Depth',
      value: `${maxDepth}m`,
      color: maxDepth > 0.5 ? 'var(--color-high)' : 'var(--text-secondary)',
    },
  ];

  return (
    <div className="stats-bar">
      <div className="stats-items">
        {stats.map((stat, idx) => (
          <div key={idx} className="stat-item">
            <span className="stat-icon" style={{ color: stat.color }}>
              {stat.icon}
            </span>
            <div className="stat-content">
              <span className="stat-label">{stat.label}</span>
              <span
                className="stat-value data-value"
                style={{ color: stat.color }}
              >
                {loading ? '—' : stat.value}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="stats-updated">
        <Clock size={12} />
        <span>
          {lastUpdated ? formatTimeAgo(lastUpdated) : 'Loading…'}
        </span>
      </div>
    </div>
  );
}

function formatTimeAgo(date) {
  if (!date) return '';
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}
