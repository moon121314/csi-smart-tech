const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

export const api = {
  getState: () => request('/state'),
  getEvents: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/events${qs ? '?' + qs : ''}`);
  },
  getMQTTStatus: () => request('/mqtt/status'),
  acknowledge: (eventIds, acknowledgedBy) =>
    request('/ack', {
      method: 'POST',
      body: JSON.stringify({
        event_ids: eventIds,
        acknowledged_by: acknowledgedBy,
      }),
    }),
};
