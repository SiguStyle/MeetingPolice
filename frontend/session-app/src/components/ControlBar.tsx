type Props = {
  status: 'idle' | 'connecting' | 'connected' | 'error';
  isMuted: boolean;
  isVideoOff: boolean;
  handRaised: boolean;
  onToggleMute: () => void;
  onToggleVideo: () => void;
  onToggleHand: () => void;
  onLeave: () => void;
};

export function ControlBar({
  status,
  isMuted,
  isVideoOff,
  handRaised,
  onToggleMute,
  onToggleVideo,
  onToggleHand,
  onLeave,
}: Props) {
  return (
    <section className="panel control-bar">
      <div>
        <p className="label">Status</p>
        <strong>{status}</strong>
      </div>
      <div className="controls">
        <button type="button" onClick={onToggleMute} className={`control-btn ${isMuted ? 'off' : ''}`}>
          <span aria-hidden="true">{isMuted ? '🔇' : '🎙️'}</span>
          {isMuted ? 'ミュート解除' : 'ミュート'}
        </button>
        <button type="button" onClick={onToggleVideo} className={`control-btn ${isVideoOff ? 'off' : ''}`}>
          <span aria-hidden="true">{isVideoOff ? '📷' : '🎥'}</span>
          {isVideoOff ? 'ビデオ再開' : 'ビデオ停止'}
        </button>
        <button type="button" onClick={onToggleHand} className={`control-btn ${handRaised ? 'active' : ''}`}>
          <span aria-hidden="true">✋</span>
          {handRaised ? '手を下げる' : '手を挙げる'}
        </button>
        <button type="button" className="control-btn danger" onClick={onLeave}>
          <span aria-hidden="true">🚪</span>
          退出
        </button>
      </div>
    </section>
  );
}
