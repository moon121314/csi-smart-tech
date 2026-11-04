export default function ErrorBanner({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div className="error-banner">
      <span>⚠ {message}</span>
      {onDismiss && (
        <button className="btn btn--sm" onClick={onDismiss}>Dismiss</button>
      )}
    </div>
  );
}
