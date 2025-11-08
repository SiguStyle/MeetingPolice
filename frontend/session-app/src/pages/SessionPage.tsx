import { FormEvent, useState } from 'react';
import { ControlBar } from '../components/ControlBar';
import { Layout } from '../components/Layout';
import { MetricsPanel } from '../components/MetricsPanel';
import { ParticipantGrid } from '../components/ParticipantGrid';
import { useAnalyticsStream } from '../hooks/useAnalyticsStream';
import { useMeetingSession } from '../hooks/useMeetingSession';

export function SessionPage() {
  const { session, status, error, joinMeeting, leaveMeeting, isMuted, toggleMute } =
    useMeetingSession();
  const { samples } = useAnalyticsStream(session?.meetingId);
  const [meetingCode, setMeetingCode] = useState('');
  const [joining, setJoining] = useState(false);

  const handleJoin = async (event: FormEvent) => {
    event.preventDefault();
    if (!meetingCode.trim()) return;
    setJoining(true);
    try {
      await joinMeeting(meetingCode);
    } finally {
      setJoining(false);
    }
  };

  if (!session) {
    return (
      <Layout>
        <section className="panel">
          <h2>ミーティングに参加</h2>
          <form className="meeting-form" onSubmit={handleJoin}>
            <input
              type="text"
              placeholder="meeting ID を入力"
              value={meetingCode}
              onChange={(event) => setMeetingCode(event.target.value)}
            />
            <button type="submit" disabled={joining}>
              {joining ? '接続中…' : '参加する'}
            </button>
          </form>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
        </section>
      </Layout>
    );
  }

  return (
    <Layout>
      <section className="panel">
        <h2>{session.title}</h2>
        <p className="label">Meeting ID</p>
        <p>{session.meetingId}</p>
        <p className="label">Vonage Session</p>
        <p>{session.sessionId}</p>
      </section>
      <ParticipantGrid participants={session.participants} />
      <MetricsPanel samples={samples} />
      <ControlBar
        status={status}
        isMuted={isMuted}
        onToggleMute={toggleMute}
        onLeave={leaveMeeting}
      />
    </Layout>
  );
}
