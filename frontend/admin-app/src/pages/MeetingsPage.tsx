import { useEffect, useState } from 'react';
import { MeetingForm } from '../components/MeetingForm';
import { MeetingTable } from '../components/MeetingTable';
import { SummaryPanel } from '../components/SummaryPanel';
import { useMeetings } from '../hooks/useMeetings';
import type { Meeting } from '../types';

export function MeetingsPage() {
  const { meetings, loading, error, refetch } = useMeetings();
  const [selected, setSelected] = useState<Meeting | null>(null);

  useEffect(() => {
    if (!selected && meetings.length > 0) {
      setSelected(meetings[0]);
    }
  }, [meetings, selected]);

  const handleCreated = (meeting: Meeting) => {
    setSelected(meeting);
    refetch();
  };

  if (loading) {
    return <p className="page">Loading meetings…</p>;
  }

  if (error) {
    return (
      <div className="page">
        <p role="alert">Could not load meetings: {error}</p>
        <button type="button" onClick={refetch}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="grid">
        <div>
          <MeetingForm onCreated={handleCreated} />
          <MeetingTable meetings={meetings} onSelect={setSelected} />
        </div>
        <SummaryPanel meeting={selected} />
      </div>
    </div>
  );
}
