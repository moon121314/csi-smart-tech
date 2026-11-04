import { useEffect, useState, useCallback, useRef } from 'react';

export function usePolling(fetcher, intervalMs = 5000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const cancelledRef = useRef(false);

  const refresh = useCallback(async () => {
    try {
      const result = await fetcher();
      if (cancelledRef.current) return;
      setData(result);
      setError(null);
    } catch (err) {
      if (cancelledRef.current) return;
      setError(err.message || 'Unknown error');
    } finally {
      if (!cancelledRef.current) setLoading(false);
    }
  }, [fetcher]);

  useEffect(() => {
    cancelledRef.current = false;
    refresh();
    const id = setInterval(refresh, intervalMs);
    return () => {
      cancelledRef.current = true;
      clearInterval(id);
    };
  }, [refresh, intervalMs]);

  return { data, error, loading, refresh };
}
