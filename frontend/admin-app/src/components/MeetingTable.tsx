import type { Meeting } from '../types';
import { formatDateTime } from '../utils/time';

type Props = {
  meetings: Meeting[];
  onSelect: (meeting: Meeting) => void;
};

export function MeetingTable({ meetings, onSelect }: Props) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Meetings</h2>
        <span>{meetings.length} total</span>
      </div>
      <p className="label">参加者共有用 Meeting ID</p>
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Status</th>
            <th>Scheduled for</th>
          </tr>
        </thead>
        <tbody>
          {meetings.map((meeting) => (
            <tr key={meeting.meetingId} onClick={() => onSelect(meeting)}>
              <td>{meeting.meetingId}</td>
              <td>{meeting.title}</td>
              <td>
                <span className={`pill ${meeting.status}`}>{meeting.status}</span>
              </td>
              <td>{formatDateTime(meeting.scheduledFor)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
