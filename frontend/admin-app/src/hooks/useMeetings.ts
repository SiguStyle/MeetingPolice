import { useCallback, useEffect, useState } from 'react';
import { fetchMeetings } from '../services/api';
import type { Meeting } from '../types';

type UseMeetingsResult = {
  meetings: Meeting[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
};

export function useMeetings(): UseMeetingsResult {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMeetings();
      setMeetings(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load meetings';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { meetings, loading, error, refetch: load };
}
