/**
 * useAlerts.js — Alerts API hook
 *
 * Calls GET /api/alerts
 * Returns: list of flood alerts for a district
 */

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000';

const useAlerts = (district = 'Kolhapur') => {
  const [alerts, setAlerts] = useState([]);
  const [alertCount, setAlertCount] = useState(0);
  const [highRiskCount, setHighRiskCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await axios.get(`${API_BASE}/api/alerts`, {
        params: { district },
        timeout: 30000,
      });
      setAlerts(res.data.alerts || []);
      setAlertCount(res.data.alert_count || 0);
      setHighRiskCount(res.data.high_risk_count || 0);
    } catch (err) {
      console.error('Alerts fetch error:', err);
      setError(err.message || 'Failed to fetch alerts');
    } finally {
      setLoading(false);
    }
  }, [district]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  return { alerts, alertCount, highRiskCount, loading, error, refetch: fetchAlerts };
};

export default useAlerts;
