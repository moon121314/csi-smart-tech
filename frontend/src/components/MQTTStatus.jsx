export default function MQTTStatus({ status }) {
  if (!status) return null;

  const indicator = status.connected
    ? 'connected'
    : status.enabled
      ? 'disconnected'
      : 'disabled';

  return (
    <div className={`mqtt-widget mqtt-widget--${indicator}`}>
      <div className="mqtt-row">
        <span className={`mqtt-dot mqtt-dot--${indicator}`} />
        <strong>MQTT: {indicator}</strong>
      </div>
      <div className="mqtt-detail">Candidate: {status.candidate_id}</div>
      <div className="mqtt-detail">
        Broker: {status.broker_host}:{status.broker_port}
      </div>
      <div className="mqtt-detail">
        Challenges: {status.challenges_responded}/{status.challenges_received} responded
      </div>
      {status.last_message_topic && (
        <div className="mqtt-detail">Last: {status.last_message_topic}</div>
      )}
      {status.last_error && (
        <div className="mqtt-error">Error: {status.last_error}</div>
      )}
    </div>
  );
}
