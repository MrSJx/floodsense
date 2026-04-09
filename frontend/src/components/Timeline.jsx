/**
 * Timeline.jsx — Forecast time step selector
 *
 * Toggle: NOW | +6h | +12h | +24h | +72h
 * Animated transitions between time steps
 */

import React from 'react';
import { Clock, ChevronRight } from 'lucide-react';

const TIMESTEPS = [
  { value: 0, label: 'NOW', short: 'Now' },
  { value: 6, label: '+6h', short: '6h' },
  { value: 12, label: '+12h', short: '12h' },
  { value: 24, label: '+24h', short: '24h' },
  { value: 72, label: '+72h', short: '72h' },
];

export default function Timeline({ selectedHour, onSelect, lastUpdated }) {
  return (
    <div className="timeline-container">
      <div className="timeline-header">
        <Clock size={14} className="timeline-icon" />
        <span className="timeline-title">Forecast Timeline</span>
        {lastUpdated && (
          <span className="timeline-updated">
            Updated {formatTimeAgo(lastUpdated)}
          </span>
        )}
      </div>

      <div className="timeline-buttons">
        {TIMESTEPS.map((ts, idx) => (
          <React.Fragment key={ts.value}>
            <button
              className={`timeline-btn ${selectedHour === ts.value ? 'active' : ''}`}
              onClick={() => onSelect(ts.value)}
              title={`Show forecast for ${ts.label}`}
            >
              <span className="timeline-btn-label">{ts.label}</span>
              {selectedHour === ts.value && (
                <span className="timeline-indicator" />
              )}
            </button>
            {idx < TIMESTEPS.length - 1 && (
              <ChevronRight size={12} className="timeline-arrow" />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Progress bar */}
      <div className="timeline-progress">
        <div
          className="timeline-progress-fill"
          style={{
            width: `${(TIMESTEPS.findIndex((t) => t.value === selectedHour) / (TIMESTEPS.length - 1)) * 100}%`,
          }}
        />
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
