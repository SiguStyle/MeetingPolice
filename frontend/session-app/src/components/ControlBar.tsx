type Props = {
  status: 'idle' | 'connecting' | 'connected' | 'error';
  isMuted: boolean;
  onToggleMute: () => void;
  onLeave: () => void;
};

export function ControlBar({ status, isMuted, onToggleMute, onLeave }: Props) {
  return (
    <section className="panel control-bar">
      <div>
        <p className="label">Status</p>
        <strong>{status}</strong>
      </div>
      <div className="controls">
        <button type="button" onClick={onToggleMute} className="secondary">
          {isMuted ? 'Unmute' : 'Mute'}
        </button>
        <button type="button" className="danger" onClick={onLeave}>
          Leave
        </button>
      </div>
    </section>
  );
}
