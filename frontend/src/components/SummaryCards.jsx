export default function SummaryCards({ state }) {
  if (!state) return null;

  const cards = [
    { label: 'Net Total', value: state.net_total, tone: 'primary' },
    { label: 'Processed', value: state.processed_events, tone: 'default' },
    { label: 'Pending Ack', value: state.pending_ack,
      tone: state.pending_ack > 0 ? 'warn' : 'ok' },
    { label: 'Unresolved', value: state.unresolved,
      tone: state.unresolved > 0 ? 'warn' : 'ok' },
    { label: 'Duplicates', value: state.duplicates, tone: 'default' },
    { label: 'Conflicts', value: state.conflicts,
      tone: state.conflicts > 0 ? 'danger' : 'ok' },
  ];

  return (
    <div className="summary-grid">
      {cards.map((c) => (
        <div key={c.label} className={`summary-card summary-card--${c.tone}`}>
          <div className="summary-label">{c.label}</div>
          <div className="summary-value">{c.value}</div>
        </div>
      ))}
    </div>
  );
}
