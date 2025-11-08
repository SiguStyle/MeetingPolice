import type { Meeting } from '../types';
import { formatDateTime } from '../utils/time';

type Props = {
  meeting: Meeting | null;
};

export function SummaryPanel({ meeting }: Props) {
  if (!meeting) {
    return (
      <section className="panel">
        <p>会議を選択すると詳細を表示します。</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>{meeting.title}</h2>
        <span className={`pill ${meeting.status}`}>{meeting.status}</span>
      </div>
      <p className="label">Meeting ID</p>
      <p>{meeting.meetingId}</p>
      <p className="label">Scheduled for</p>
      <p>{formatDateTime(meeting.scheduledFor)}</p>
      <p className="label">Session ID</p>
      <p>{meeting.sessionId ?? '—'}</p>
      <p className="label">Summary object</p>
      <p>{meeting.summaryKey ?? '未生成'}</p>
    </section>
  );
}
