import { useState } from 'react';
import type { Meeting } from '../types';
import { createMeeting } from '../services/api';

export function useCreateMeeting(onCreated: (meeting: Meeting) => void) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (title: string) => {
    if (!title.trim()) {
      setError('Title is required');
      throw new Error('Title is required');
    }

    setLoading(true);
    setError(null);
    try {
      const meeting = await createMeeting(title.trim());
      onCreated(meeting);
      return meeting;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unexpected error';
      setError(message);
      throw err instanceof Error ? err : new Error(message);
    } finally {
      setLoading(false);
    }
  };

  return { submit, loading, error };
}
