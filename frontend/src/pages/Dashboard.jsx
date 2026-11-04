import { useCallback, useState } from 'react';
import { api } from '../services/api.js';
import { usePolling } from '../hooks/usePolling.js';
import SummaryCards from '../components/SummaryCards.jsx';
import EventTable from '../components/EventTable.jsx';
import MQTTStatus from '../components/MQTTStatus.jsx';
import Loading from '../components/Loading.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';

const fetchAll = async () => {
  const [state, eventsResp, mqtt] = await Promise.all([
    api.getState(),
    api.getEvents({ limit: 50, include_voided: false }),
    api.getMQTTStatus(),
  ]);
  return { state, events: eventsResp.events, mqtt };
};

export default function Dashboard() {
  const { data, error, loading, refresh } = usePolling(fetchAll, 5000);
  const [acking, setAcking] = useState(null);
  const [ackError, setAckError] = useState(null);

  const handleAck = useCallback(
    async (eventId) => {
      if (!window.confirm(`Acknowledge event ${eventId}?`)) return;
      const supervisor = window.prompt('Supervisor ID:', 'SUP-01');
      if (!supervisor) return;

      setAcking(eventId);
      setAckError(null);
      try {
        const resp = await api.acknowledge([eventId], supervisor);
        const result = resp.results[0];
        if (
          result.status === 'ACKNOWLEDGED' ||
          result.status === 'ALREADY_ACKNOWLEDGED'
        ) {
          await refresh();
        } else {
          setAckError(`${result.status}: ${result.message}`);
        }
      } catch (err) {
        setAckError(err.message || 'Ack failed');
      } finally {
        setAcking(null);
      }
    },
    [refresh]
  );

  if (loading && !data) return <Loading label="Loading dashboard..." />;

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <h1>CSI Smart Tech</h1>
          <p className="subtitle">Production Dashboard</p>
        </div>
        <button
          className="btn btn--ghost"
          onClick={refresh}
          disabled={loading}
        >
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </header>

      <ErrorBanner
        message={error || ackError}
        onDismiss={() => setAckError(null)}
      />

      <section className="section">
        <h2>Production Summary</h2>
        <SummaryCards state={data?.state} />
      </section>

      <section className="section">
        <h2>Pending &amp; Exception Events</h2>
        <EventTable
          events={data?.events}
          onAck={handleAck}
          busy={acking !== null}
        />
      </section>

      <section className="section">
        <h2>MQTT Status</h2>
        <MQTTStatus status={data?.mqtt} />
      </section>

      <footer className="dashboard-footer">
        Auto-refreshes every 5s · <a href="/docs" target="_blank" rel="noreferrer">API docs</a>
      </footer>
    </div>
  );
}
