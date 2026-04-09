/**
 * RiskOverlay.jsx — Color-coded flood risk layer
 *
 * This component adds the risk heatmap overlay on the map.
 * It's integrated into Map.jsx as the FloodLayer.
 * This file provides additional utility functions for risk assessment.
 */

import React from 'react';

/* ── Risk classification ───────────────────────────────────── */
export const RISK_LEVELS = {
  extreme: {
    color: '#7f1d1d',
    label: 'EXTREME',
    emoji: '🔴',
    threshold: 0.8,
    description: 'Immediate evacuation recommended',
  },
  high: {
    color: '#ef4444',
    label: 'HIGH',
    emoji: '🟠',
    threshold: 0.6,
    description: 'Prepare for possible evacuation',
  },
  medium: {
    color: '#f97316',
    label: 'MODERATE',
    emoji: '🟡',
    threshold: 0.35,
    description: 'Stay alert and monitor conditions',
  },
  low: {
    color: '#eab308',
    label: 'LOW',
    emoji: '🟢',
    threshold: 0.15,
    description: 'Be aware of rising water levels',
  },
  none: {
    color: '#22c55e',
    label: 'SAFE',
    emoji: '✅',
    threshold: 0,
    description: 'No significant flood risk',
  },
};

/**
 * Get risk level info from a probability value
 */
export function getRiskLevel(probability) {
  if (probability >= 0.8) return RISK_LEVELS.extreme;
  if (probability >= 0.6) return RISK_LEVELS.high;
  if (probability >= 0.35) return RISK_LEVELS.medium;
  if (probability >= 0.15) return RISK_LEVELS.low;
  return RISK_LEVELS.none;
}

/**
 * Get a color for a given probability (gradient)
 */
export function getRiskColor(probability) {
  return getRiskLevel(probability).color;
}

/**
 * Calculate summary stats from a GeoJSON flood result
 */
export function summarizeFloodRisk(geojson) {
  if (!geojson || !geojson.features) {
    return { total: 0, extreme: 0, high: 0, medium: 0, low: 0, safe: 0 };
  }

  const counts = { total: geojson.features.length, extreme: 0, high: 0, medium: 0, low: 0, safe: 0 };

  for (const f of geojson.features) {
    const risk = f.properties.risk_level || 'none';
    if (risk === 'extreme') counts.extreme++;
    else if (risk === 'high') counts.high++;
    else if (risk === 'medium') counts.medium++;
    else if (risk === 'low') counts.low++;
    else counts.safe++;
  }

  return counts;
}

/**
 * RiskOverlay indicator — small visual badge for current risk status
 */
export default function RiskOverlay({ severity }) {
  const level = RISK_LEVELS[severity] || RISK_LEVELS.none;

  return (
    <div
      className="risk-overlay-badge"
      style={{
        background: `${level.color}20`,
        borderColor: level.color,
      }}
    >
      <span className="risk-overlay-emoji">{level.emoji}</span>
      <span className="risk-overlay-label" style={{ color: level.color }}>
        {level.label}
      </span>
    </div>
  );
}
