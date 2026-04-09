/**
 * AlertPanel.jsx — Flood alert sidebar panel
 *
 * Shows high-risk villages/areas sorted by severity.
 * Each alert includes risk level, expected depth, ETA, and a "zoom to" button.
 * Extreme alerts have pulsing red border.
 */

import React from 'react';
import {
  AlertTriangle,
  MapPin,
  Clock,
  Waves,
  Users,
  ChevronRight,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';

const RISK_ICONS = {
  extreme: '🔴',
  high: '🟠',
  medium: '🟡',
  low: '🟢',
};

const RISK_BADGE_COLORS = {
  extreme: { bg: 'rgba(127, 29, 29, 0.4)', border: '#ef4444', text: '#fca5a5' },
  high: { bg: 'rgba(239, 68, 68, 0.15)', border: '#f97316', text: '#fdba74' },
  medium: { bg: 'rgba(234, 179, 8, 0.12)', border: '#eab308', text: '#fde047' },
  low: { bg: 'rgba(34, 197, 94, 0.1)', border: '#22c55e', text: '#86efac' },
};

export default function AlertPanel({ alerts, loading, onZoomTo }) {
  if (loading) {
    return (
      <div className="alert-panel">
        <div className="alert-panel-header">
          <ShieldAlert size={18} />
          <h3>Flood Alerts</h3>
        </div>
        <div className="alert-panel-body">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton alert-skeleton" />
          ))}
        </div>
      </div>
    );
  }

  if (!alerts || alerts.length === 0) {
    return (
      <div className="alert-panel">
        <div className="alert-panel-header">
          <ShieldCheck size={18} style={{ color: 'var(--color-safe)' }} />
          <h3>Flood Alerts</h3>
        </div>
        <div className="alert-panel-body alert-empty">
          <ShieldCheck size={40} style={{ color: 'var(--color-safe)', opacity: 0.5 }} />
          <p>No active flood alerts</p>
          <span>All monitored areas are currently safe</span>
        </div>
      </div>
    );
  }

  return (
    <div className="alert-panel">
      <div className="alert-panel-header">
        <ShieldAlert size={18} style={{ color: 'var(--color-high)' }} />
        <h3>Flood Alerts</h3>
        <span className="alert-count-badge">{alerts.length}</span>
      </div>

      <div className="alert-panel-body">
        {alerts.map((alert, idx) => {
          const colors = RISK_BADGE_COLORS[alert.risk_level] || RISK_BADGE_COLORS.low;
          const isExtreme = alert.risk_level === 'extreme';

          return (
            <div
              key={idx}
              className={`alert-card ${isExtreme ? 'alert-extreme' : ''}`}
              style={{
                animationDelay: `${idx * 80}ms`,
                borderLeftColor: colors.border,
              }}
            >
              <div className="alert-card-top">
                <span className="alert-risk-icon">
                  {RISK_ICONS[alert.risk_level]}
                </span>
                <span
                  className="alert-risk-badge"
                  style={{
                    background: colors.bg,
                    borderColor: colors.border,
                    color: colors.text,
                  }}
                >
                  {alert.risk_level?.toUpperCase()} RISK
                </span>
              </div>

              <h4 className="alert-location">
                <MapPin size={13} />
                {alert.location}
                {alert.district && (
                  <span className="alert-district">, {alert.district}</span>
                )}
              </h4>

              <div className="alert-metrics">
                {alert.expected_depth_m > 0 && (
                  <div className="alert-metric">
                    <Waves size={12} />
                    <span>Depth: <strong>{alert.expected_depth_m}m</strong></span>
                  </div>
                )}
                {alert.eta_hours && (
                  <div className="alert-metric">
                    <Clock size={12} />
                    <span>ETA: <strong>{alert.eta_hours}h</strong></span>
                  </div>
                )}
                {alert.rainfall_24h_mm > 0 && (
                  <div className="alert-metric">
                    <span>🌧 Rain 24h: <strong>{alert.rainfall_24h_mm}mm</strong></span>
                  </div>
                )}
                {alert.population && (
                  <div className="alert-metric">
                    <Users size={12} />
                    <span>{alert.population.toLocaleString()} people</span>
                  </div>
                )}
              </div>

              {alert.recommendations && alert.recommendations.length > 0 && (
                <div className="alert-recs">
                  {alert.recommendations.slice(0, 2).map((rec, i) => (
                    <span key={i} className="alert-rec">
                      <AlertTriangle size={10} />
                      {rec}
                    </span>
                  ))}
                </div>
              )}

              <button
                className="alert-zoom-btn"
                onClick={() => onZoomTo && onZoomTo([alert.lat, alert.lon])}
              >
                Zoom to location <ChevronRight size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
