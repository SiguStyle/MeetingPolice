import type { Meeting } from '../types';
import { formatDateTime } from '../utils/time';

type Props = {
  meetings: Meeting[];
  onSelect: (meeting: Meeting) => void;
};

export function MeetingTable({ meetings, onSelect }: Props) {
  if (meetings.length === 0) {
    return (
      <section className="panel empty-state">
        <h2>まだミーティングがありません</h2>
        <p>左のフォームからミーティングを作成すると、ここに共有用の Meeting ID が並びます。</p>
        <ul>
          <li>作成後すぐにステータスが <strong>scheduled</strong> になります。</li>
          <li>参加者には Session ページで ID を入力してもらいます。</li>
        </ul>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">ステップ 2</p>
          <h2>共有用ミーティング一覧</h2>
        </div>
        <span>{meetings.length} 件</span>
      </div>
      <p className="label">参加者に伝える Meeting ID</p>
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
      <p className="help-text">行をクリックすると右側で詳細・共有メモを確認できます。</p>
    </section>
  );
}
