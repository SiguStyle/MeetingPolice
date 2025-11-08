import type { Participant } from '../types';

type Props = {
  participants: Participant[];
};

export function ParticipantGrid({ participants }: Props) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Participants</h2>
        <span>{participants.length} joined</span>
      </div>
      <div className="participant-grid">
        {participants.map((participant) => (
          <div key={participant.id} className={`participant ${participant.isSpeaking ? 'speaking' : ''}`}>
            <div className="avatar">{participant.name.slice(0, 2).toUpperCase()}</div>
            <div>
              <p className="name">{participant.name}</p>
              <p className="role">{participant.role}</p>
            </div>
            {participant.isSpeaking && <span className="pill">Speaking</span>}
          </div>
        ))}
      </div>
    </section>
  );
}
