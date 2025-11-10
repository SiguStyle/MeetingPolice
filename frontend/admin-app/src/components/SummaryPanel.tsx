import { useState } from 'react';
import type { Meeting } from '../types';
import { formatDateTime } from '../utils/time';

type Props = {
  meeting: Meeting | null;
};

export function SummaryPanel({ meeting }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!meeting) return;
    try {
      await navigator.clipboard.writeText(meeting.meetingId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  if (!meeting) {
    return (
      <section className="panel">
        <p>会議を選択すると詳細を表示します。</p>
        <p className="help-text">Meeting ID をコピーして参加者に共有してください。</p>
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
      <div className="id-row">
        <code>{meeting.meetingId}</code>
        <button type="button" className="ghost" onClick={handleCopy}>
          {copied ? 'コピー済み' : 'ID をコピー'}
        </button>
      </div>
      <p className="label">Scheduled for</p>
      <p>{formatDateTime(meeting.scheduledFor)}</p>
      <p className="label">Session ID</p>
      <p>{meeting.sessionId ?? '—'}</p>
      <p className="label">Summary object</p>
      <p>{meeting.summaryKey ?? '未生成'}</p>
      <div className="summary-tip">
        <p>参加者への案内:</p>
        <ol>
          <li>Session ページでこの Meeting ID を入力してもらいます。</li>
          <li>開始後にステータスが <strong>live</strong> へ切り替わります。</li>
          <li>会議後は「要約を生成」で S3 に保存できます（今後実装予定）。</li>
        </ol>
      </div>
    </section>
  );
}
