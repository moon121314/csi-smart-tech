export default function EventTable({ events, onAck, busy }) {
  if (!events || events.length === 0) {
    return (
      <div className="empty-state">
        <p>No pending or exception events.</p>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table className="event-table">
        <thead>
          <tr>
            <th>Event ID</th>
            <th>Source</th>
            <th>Type</th>
            <th>Qty</th>
            <th>Status</th>
            <th>Event Time</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {events.map((ev) => (
            <tr key={ev.id}>
              <td>{ev.event_id}</td>
              <td>{ev.source_id}</td>
              <td>{ev.event_type}</td>
              <td>{ev.quantity}</td>
              <td>
                <span className={`status status--${ev.status.toLowerCase()}`}>
                  {ev.status}
                </span>
              </td>
              <td>{new Date(ev.event_time).toLocaleString()}</td>
              <td>
                {ev.status === 'ACCEPTED' && !ev.acknowledged && (
                  <button
                    className="btn btn--primary btn--sm"
                    onClick={() => onAck(ev.event_id)}
                    disabled={busy}
                  >
                    Acknowledge
                  </button>
                )}
                {ev.acknowledged && (
                  <span className="ack-badge" title={`By ${ev.acknowledged_by}`}>
                    ✓ Acked
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
