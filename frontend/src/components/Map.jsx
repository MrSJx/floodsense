/**
 * Map.jsx — Main Leaflet map with flood risk overlays
 *
 * Features:
 *   - Dark basemap (CartoDB Dark Matter)
 *   - Flood risk overlay (color-coded circles)
 *   - Terrain elevation visualization
 *   - Click → popup with details
 *   - Hover → tooltip with risk level
 */

import React, { useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Tooltip,
  useMap,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

/* ── Risk color mapping ────────────────────────────────────── */
const RISK_COLORS = {
  extreme: '#7f1d1d',
  high: '#ef4444',
  medium: '#f97316',
  low: '#eab308',
  none: '#22c55e',
};

const RISK_LABELS = {
  extreme: '🔴 EXTREME',
  high: '🟠 HIGH',
  medium: '🟡 MODERATE',
  low: '🟢 LOW',
  none: '✅ SAFE',
};

/* ── Fly-to helper ─────────────────────────────────────────── */
function FlyTo({ center, zoom }) {
  const map = useMap();
  React.useEffect(() => {
    if (center) map.flyTo(center, zoom, { duration: 1.2 });
  }, [center, zoom, map]);
  return null;
}

/* ── Flood risk layer ──────────────────────────────────────── */
function FloodLayer({ geojson }) {
  if (!geojson || !geojson.features) return null;

  return geojson.features.map((feature, idx) => {
    const [lon, lat] = feature.geometry.coordinates;
    const props = feature.properties;
    const risk = props.risk_level || 'none';
    const color = RISK_COLORS[risk] || RISK_COLORS.none;
    const radius = props.flooded ? 6 : 4;
    const opacity = Math.max(0.3, props.probability || 0.2);

    return (
      <CircleMarker
        key={`flood-${idx}`}
        center={[lat, lon]}
        radius={radius}
        pathOptions={{
          color: color,
          fillColor: color,
          fillOpacity: opacity,
          weight: props.flooded ? 2 : 0.5,
          opacity: opacity,
        }}
      >
        <Tooltip
          direction="top"
          offset={[0, -8]}
          className="risk-tooltip"
        >
          <span style={{ fontWeight: 600, color }}>
            {RISK_LABELS[risk]}
          </span>
        </Tooltip>
        <Popup>
          <div style={{ fontFamily: 'var(--font-ui)', minWidth: 180 }}>
            <h4 style={{ margin: '0 0 8px', color, fontSize: 14 }}>
              {RISK_LABELS[risk]}
            </h4>
            <table style={{ fontSize: 12, width: '100%' }}>
              <tbody>
                <tr>
                  <td style={{ color: '#8b949e', paddingRight: 12 }}>Elevation</td>
                  <td style={{ fontFamily: 'var(--font-data)' }}>
                    {props.elevation_m?.toFixed(1)} m
                  </td>
                </tr>
                <tr>
                  <td style={{ color: '#8b949e' }}>Flood Depth</td>
                  <td style={{ fontFamily: 'var(--font-data)' }}>
                    {props.depth_m?.toFixed(2)} m
                  </td>
                </tr>
                <tr>
                  <td style={{ color: '#8b949e' }}>Probability</td>
                  <td style={{ fontFamily: 'var(--font-data)' }}>
                    {(props.probability * 100)?.toFixed(1)}%
                  </td>
                </tr>
                <tr>
                  <td style={{ color: '#8b949e' }}>Coordinates</td>
                  <td style={{ fontFamily: 'var(--font-data)', fontSize: 10 }}>
                    {lat.toFixed(4)}, {lon.toFixed(4)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Popup>
      </CircleMarker>
    );
  });
}

/* ── Terrain layer (subtle elevation dots) ─────────────────── */
function TerrainLayer({ geojson }) {
  if (!geojson || !geojson.features) return null;

  const maxElev = useMemo(() => {
    let max = 0;
    for (const f of geojson.features) {
      if (f.properties.elevation > max) max = f.properties.elevation;
    }
    return max || 1;
  }, [geojson]);

  return geojson.features.map((feature, idx) => {
    const [lon, lat] = feature.geometry.coordinates;
    const elev = feature.properties.elevation;
    const norm = elev / maxElev;
    const r = Math.round(20 + norm * 40);
    const g = Math.round(60 + norm * 80);
    const b = Math.round(30 + norm * 50);
    const color = `rgb(${r}, ${g}, ${b})`;

    return (
      <CircleMarker
        key={`terrain-${idx}`}
        center={[lat, lon]}
        radius={3}
        pathOptions={{
          color: 'transparent',
          fillColor: color,
          fillOpacity: 0.35,
          weight: 0,
        }}
      />
    );
  });
}

/* ── Main Map Component ────────────────────────────────────── */
export default function FloodMap({
  floodGeojson,
  terrainGeojson,
  center = [16.7, 74.2],
  zoom = 10,
  showTerrain = true,
  showFlood = true,
  flyTo = null,
}) {
  return (
    <div className="map-wrapper">
      <MapContainer
        center={center}
        zoom={zoom}
        zoomControl={true}
        style={{ width: '100%', height: '100%' }}
        maxZoom={18}
        minZoom={6}
      >
        {/* Dark basemap tile layer */}
        <TileLayer
          attribution='&copy; <a href="https://carto.com">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* Fly to a specific location */}
        {flyTo && <FlyTo center={flyTo} zoom={13} />}

        {/* Terrain elevation layer (subtle) */}
        {showTerrain && terrainGeojson && (
          <TerrainLayer geojson={terrainGeojson} />
        )}

        {/* Flood risk overlay */}
        {showFlood && floodGeojson && (
          <FloodLayer geojson={floodGeojson} />
        )}
      </MapContainer>
    </div>
  );
}
