import { FormEvent, useState } from 'react';
import { useCreateMeeting } from '../hooks/useCreateMeeting';
import type { Meeting } from '../types';

type Props = {
  onCreated: (meeting: Meeting) => void;
};

export function MeetingForm({ onCreated }: Props) {
  const [title, setTitle] = useState('');
  const { submit, loading, error } = useCreateMeeting(onCreated);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await submit(title);
      setTitle('');
    } catch {
      // エラーメッセージは hook 側でセット済み
    }
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">ステップ 1</p>
          <h2>新しいセッションを作成</h2>
        </div>
        <span className="pill scheduled">準備中</span>
      </div>
      <p className="label">ミーティングタイトル</p>
      <form onSubmit={handleSubmit} className="meeting-form">
        <input
          type="text"
          placeholder="例）月次レビュー"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? '作成中…' : 'ミーティングを作成'}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      <p className="help-text">ボタンを押すと数秒後に Meeting ID が自動採番されます。</p>
    </section>
  );
}
