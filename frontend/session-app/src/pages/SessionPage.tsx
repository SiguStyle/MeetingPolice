import { FormEvent, useState } from 'react';
import { ControlBar } from '../components/ControlBar';
import { Layout } from '../components/Layout';
import { MetricsPanel } from '../components/MetricsPanel';
import { ParticipantGrid } from '../components/ParticipantGrid';
import { useAnalyticsStream } from '../hooks/useAnalyticsStream';
import { useMeetingSession } from '../hooks/useMeetingSession';

export function SessionPage() {
  const {
    session,
    status,
    error,
    joinMeeting,
    leaveMeeting,
    isMuted,
    isVideoOff,
    handRaised,
    toggleMute,
    toggleVideo,
    toggleHand,
  } = useMeetingSession();
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
        <section className="panel hero-session">
          <h2>参加者画面</h2>
          <p>管理者から共有された Meeting ID を入力すると、仮想会議室に入ることができます。</p>
          <ul className="instructions">
            <li>マイクとカメラの状態は下部のコントロールバーで切り替え可能です。</li>
            <li>接続後は音声解析のメトリクスがリアルタイムに表示されます。</li>
          </ul>
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
      <section className="panel meeting-overview">
        <div>
          <p className="label">現在のセッション</p>
          <h2>{session.title}</h2>
          <p className="label">Meeting ID</p>
          <code>{session.meetingId}</code>
        </div>
        <div className="session-meta">
          <div>
            <p className="label">Vonage Session</p>
            <p>{session.sessionId}</p>
          </div>
          <div>
            <p className="label">参加者数</p>
            <p>{session.participants.length} 名</p>
          </div>
        </div>
      </section>
      <ParticipantGrid participants={session.participants} />
      <MetricsPanel samples={samples} />
      <ControlBar
        status={status}
        isMuted={isMuted}
        isVideoOff={isVideoOff}
        handRaised={handRaised}
        onToggleMute={toggleMute}
        onToggleVideo={toggleVideo}
        onToggleHand={toggleHand}
        onLeave={leaveMeeting}
      />
    </Layout>
  );
}
