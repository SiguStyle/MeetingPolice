import { FormEvent, useState } from 'react';
import { useCreateMeeting } from '../hooks/useCreateMeeting';
import type { Meeting } from '../types';

type Props = {
  onCreated: (meeting: Meeting) => void;
};

export function MeetingForm({ onCreated }: Props) {
  const [title, setTitle] = useState('');
  const { submit, loading, error } = useCreateMeeting(onCreated);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await submit(title);
      setTitle('');
    } catch {
      // エラーメッセージは hook 側でセット済み
    }
  };

  return (
    <section className="panel">
      <h2>Schedule a meeting</h2>
      <p className="label">タイトル</p>
      <form onSubmit={handleSubmit} className="meeting-form">
        <input
          type="text"
          placeholder="Team sync"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Saving…' : 'Create'}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
