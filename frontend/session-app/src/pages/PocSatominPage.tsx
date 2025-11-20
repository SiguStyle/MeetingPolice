import { FormEvent, useEffect, useRef, useState } from 'react';
import { Layout } from '../components/Layout';
import type {
  PocTranscript,
  PocArchivedJob,
  PocHistoryItem,
} from '../types';
import {
  fetchArchivedSatominJob,
  fetchPocSatominHistory,
  fetchPocSatominJob,
  startPocSatominRun,
} from '../services/api';

const buildWsUrl = (path: string) => {
  const apiBase = import.meta.env.VITE_API_BASE ?? '/api';
  if (apiBase.startsWith('http')) {
    const url = new URL(apiBase);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    const basePath = url.pathname.endsWith('/') ? url.pathname.slice(0, -1) : url.pathname;
    return `${url.origin}${basePath}${path}`;
  }
  const origin = window.location.origin.replace(/^http/, 'ws');
  const base = apiBase.endsWith('/') ? apiBase.slice(0, -1) : apiBase;
  return `${origin}${base}${path}`;
};

export function PocSatominPage() {
  const [agendaFile, setAgendaFile] = useState<File | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [transcripts, setTranscripts] = useState<PocTranscript[]>([]);
  const [status, setStatus] = useState<'idle' | 'streaming' | 'complete'>('idle');
  const [message, setMessage] = useState<string | null>(null);
  const [jobAgenda, setJobAgenda] = useState<string>('');
  const [history, setHistory] = useState<PocHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyPreview, setHistoryPreview] = useState<PocArchivedJob | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    if (!audioFile) {
      setAudioPreviewUrl((prev) => {
        if (prev) {
          URL.revokeObjectURL(prev);
        }
        return null;
      });
      return;
    }
    const url = URL.createObjectURL(audioFile);
    setAudioPreviewUrl(url);
    return () => {
      URL.revokeObjectURL(url);
    };
  }, [audioFile]);

  useEffect(() => {
    const fetchJob = async () => {
      if (status !== 'complete' || !jobId) return;
      try {
        const detail = await fetchPocSatominJob(jobId);
        setJobAgenda(detail.agenda_text);
      } catch (err) {
        console.error(err);
      }
    };
    fetchJob();
  }, [jobId, status]);

  useEffect(() => {
    const loadHistory = async () => {
      setHistoryLoading(true);
      try {
        const items = await fetchPocSatominHistory();
        setHistory(items);
      } catch (err) {
        console.error(err);
      } finally {
        setHistoryLoading(false);
      }
    };
    loadHistory();
  }, []);

  const handleStart = async (event: FormEvent) => {
    event.preventDefault();
    setMessage(null);
    setJobAgenda('');
    if (!audioFile) {
      setMessage('音声ファイルを選択してください。');
      return;
    }
    const formData = new FormData();
    if (agendaFile) {
      formData.append('agenda', agendaFile);
    }
    formData.append('audio', audioFile);
    try {
      const response = await startPocSatominRun(formData);
      setJobId(response.job_id);
      setTranscripts([]);
      setStatus('streaming');
      connectWebSocket(response.job_id);
      if (audioRef.current && audioPreviewUrl) {
        audioRef.current.currentTime = 0;
        const playPromise = audioRef.current.play();
        if (playPromise) {
          playPromise.catch((err) => console.warn('Audio autoplay blocked', err));
        }
      }
    } catch (err) {
      const text = err instanceof Error ? err.message : 'アップロードに失敗しました';
      setMessage(text);
    }
  };

  const connectWebSocket = (id: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    const ws = new WebSocket(buildWsUrl(`/poc_satomin/ws/${id}`));
    wsRef.current = ws;
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'transcript') {
        const payload = data.payload as PocTranscript;
        const action = (data.action as 'append' | 'update' | undefined) ?? 'append';
        setTranscripts((prev) => {
          const key = payload.result_id ?? `idx-${payload.index}`;
          const updateExisting = (items: PocTranscript[]) =>
            items.map((item) => {
              const itemKey = item.result_id ?? `idx-${item.index}`;
              if (itemKey !== key) return item;
              return { ...item, ...payload };
            });
          const exists = prev.some((item) => (item.result_id ?? `idx-${item.index}`) === key);
          if (action === 'append') {
            if (exists) {
              return updateExisting(prev);
            }
            return [...prev, payload];
          }
          if (action === 'update' && exists) {
            return updateExisting(prev);
          }
          return prev;
        });
      } else if (data.type === 'complete') {
        setStatus('complete');
        setMessage('文字起こしが完了しました。');
        ws.close();
      } else if (data.type === 'error') {
        setMessage(data.message);
      }
    };
    ws.onerror = () => setMessage('WebSocket への接続に失敗しました。');
    ws.onclose = () => {
      wsRef.current = null;
    };
  };

  const refreshHistory = async () => {
    setHistoryLoading(true);
    try {
      const items = await fetchPocSatominHistory();
      setHistory(items);
    } catch (err) {
      console.error(err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const loadHistoryPreview = async (id: string) => {
    try {
      const data = await fetchArchivedSatominJob(id);
      setHistoryPreview(data);
      setMessage(`過去ジョブ ${id} を読み込みました。`);
    } catch (err) {
      const text = err instanceof Error ? err.message : '過去の文字起こし取得に失敗しました';
      setMessage(text);
    }
  };

  return (
    <Layout title="MeetingPolice PoC Satomin" subtitle="アジェンダと音声をアップロードし、リアルタイム文字起こしを確認できます。">
      <div className="poc-columns">
        <div className="poc-left">
          <section className="panel poc-upload">
            <h2>PoC Satomin: アジェンダ &amp; 音声のアップロード</h2>
            <p>音声は Transcribe Streaming で処理され、結果が右のパネルにリアルタイムで届きます。</p>
            <form className="poc-form" onSubmit={handleStart}>
              <label className="upload-field">
                <span>アジェンダファイル（任意）</span>
                <input type="file" accept=".txt,.md,.doc,.docx,.pdf" onChange={(event) => setAgendaFile(event.target.files?.[0] ?? null)} />
                {agendaFile && <small>{agendaFile.name}</small>}
              </label>
              <label className="upload-field">
                <span>音声ファイル（必須）</span>
                <input type="file" accept="audio/*" onChange={(event) => setAudioFile(event.target.files?.[0] ?? null)} required />
                {audioFile && <small>{audioFile.name}</small>}
              </label>
              <button type="submit" disabled={status === 'streaming'}>
                {status === 'streaming' ? '文字起こし中…' : '文字起こしを開始'}
              </button>
            </form>
            {message && <p className="info-text">{message}</p>}
            {jobId && (
              <div className="job-meta">
                <p className="label">Job ID</p>
                <code>{jobId}</code>
                <p className="label">ステータス</p>
                <span className={`pill ${status}`}>{status}</span>
              </div>
            )}
            {audioPreviewUrl && (
              <div className="audio-preview">
                <p className="label">アップロード音声</p>
                <audio ref={audioRef} src={audioPreviewUrl} controls />
              </div>
            )}
          </section>

          {jobAgenda && (
            <section className="panel">
              <h2>アジェンダ</h2>
              <div className="agenda-preview">
                <pre>{jobAgenda || '（未指定）'}</pre>
              </div>
            </section>
          )}

          <section className="panel history-panel">
            <div className="panel-header">
              <div>
                <p className="label">過去の文字起こし</p>
                <h2>{history.length} 件</h2>
              </div>
              <button type="button" className="ghost" onClick={refreshHistory} disabled={historyLoading}>
                {historyLoading ? '更新中…' : '履歴を更新'}
              </button>
            </div>
            {history.length === 0 && <p className="faded">これまでのアーカイブはまだありません。</p>}
            {history.length > 0 && (
              <div className="history-list">
                {history.map((item) => (
                  <article key={item.job_id} className="history-item">
                    <div>
                      <strong>{item.archive_name || item.job_id}</strong>
                      <p className="label">{item.completed_at || item.job_id}</p>
                      {item.archive_name && <p className="faded mono">{item.job_id}</p>}
                      <p className="agenda-preview-text">{item.agenda_preview || '（アジェンダなし）'}</p>
                    </div>
                    <div className="history-actions">
                      <button type="button" className="ghost" onClick={() => loadHistoryPreview(item.job_id)}>
                        表示
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
            {historyPreview && (
              <div className="history-preview">
                <p className="label">選択中のアジェンダ</p>
                {historyPreview.archive_name && (
                  <p>
                    <strong>{historyPreview.archive_name}</strong>
                  </p>
                )}
                <pre>{historyPreview.agenda_text || '（なし）'}</pre>
                <p className="label">文字起こし（抜粋）</p>
                <div className="history-transcripts">
                  {historyPreview.transcripts.slice(0, 5).map((item) => (
                    <p key={item.index}>
                      <strong>{item.speaker}:</strong> {item.text}
                    </p>
                  ))}
                  {historyPreview.transcripts.length > 5 && <p>…ほか {historyPreview.transcripts.length - 5} 行</p>}
                </div>
              </div>
            )}
          </section>
        </div>

        <div className="poc-right">
          <section className="panel transcript-panel">
            <div className="panel-header">
              <div>
                <p className="label">リアルタイム文字起こし</p>
                <h2>{transcripts.length} 行</h2>
              </div>
            </div>
            <div className="transcript-feed">
              {transcripts.map((item) => (
                <article key={item.timestamp + item.index} className="transcript-item">
                  <header>
                    <strong>{item.speaker}</strong>
                    {item.raw_speaker && <span className="pill mono">{item.raw_speaker}</span>}
                    <span>{item.timestamp}</span>
                  </header>
                  <p>{item.text}</p>
                </article>
              ))}
              {transcripts.length === 0 && <p className="faded">アップロード後に文字起こしが表示されます。</p>}
            </div>
          </section>
        </div>
      </div>
    </Layout>
  );
}
