import { FormEvent, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  const navigate = useNavigate();
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
  const [realtimeClassifications, setRealtimeClassifications] = useState<Array<{ index: number; text: string; speaker: string; category: string; alignment: number; method: string; is_final?: boolean }>>([]);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [scheduledMinutes, setScheduledMinutes] = useState<number | null>(null);
  const [timerRunning, setTimerRunning] = useState<boolean>(false);
  const [showWarning, setShowWarning] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const timerRef = useRef<number | null>(null);
  const lastAlertTimeRef = useRef<number>(0);
  const speechSynthRef = useRef<SpeechSynthesisUtterance | null>(null);
  const alertIntervalRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  // タイマー管理
  useEffect(() => {
    if (status === 'streaming') {
      // タイマー開始
      setElapsedSeconds(0);
      timerRef.current = window.setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      // タイマー停止
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [status]);

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
        extractScheduledTime(detail.agenda_text);
      } catch (err) {
        console.error(err);
      }
    };
    fetchJob();
  }, [jobId, status]);

  // アジェンダから予定時間を抽出
  const extractScheduledTime = (agendaText: string) => {
    if (!agendaText) {
      setScheduledMinutes(null);
      return;
    }
    // 「30分」「1時間」「90分」などのパターンを検索
    const minuteMatch = agendaText.match(/(\d+)\s*分/);
    const hourMatch = agendaText.match(/(\d+)\s*時間/);

    if (minuteMatch) {
      setScheduledMinutes(parseInt(minuteMatch[1], 10));
      console.log(`⏰ 予定時間: ${minuteMatch[1]}分`);
    } else if (hourMatch) {
      setScheduledMinutes(parseInt(hourMatch[1], 10) * 60);
      console.log(`⏰ 予定時間: ${hourMatch[1]}時間`);
    } else {
      setScheduledMinutes(null);
    }
  };

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
    setScheduledMinutes(null);
    if (!audioFile) {
      setMessage('音声ファイルを選択してください。');
      return;
    }
    const formData = new FormData();
    if (agendaFile) {
      formData.append('agenda', agendaFile);
      // アジェンダファイルから予定時間を抽出
      const agendaText = await agendaFile.text();
      setJobAgenda(agendaText);
      extractScheduledTime(agendaText);
    }
    formData.append('audio', audioFile);
    try {
      const response = await startPocSatominRun(formData);
      setJobId(response.job_id);
      setTranscripts([]);
      setRealtimeClassifications([]);
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
    const wsUrl = buildWsUrl(`/poc_satomin/ws/${id}`);
    console.log('🔌 WebSocket接続開始:', wsUrl);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('✅ WebSocket接続成功！');
    };

    ws.onmessage = (event) => {
      console.log('📨 WebSocketメッセージ受信:', event.data);
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
      } else if (data.type === 'realtime_classification') {
        // リアルタイム分析結果を受信
        const { index, text, speaker, category, alignment, method, is_final } = data.payload;
        const action = (data.action as 'update' | undefined) ?? 'append';

        console.log(`🔍 リアルタイム分析: ${speaker} - ${text} → [${category}] ${alignment}% (${method}${is_final ? ' 確定' : ''})`);

        setRealtimeClassifications((prev) => {
          // indexで既存の項目を探す
          const existingIndex = prev.findIndex((item) => item.index === index);

          if (existingIndex >= 0) {
            // 既存の項目を更新
            const updated = [...prev];
            updated[existingIndex] = { index, text, speaker, category, alignment, method, is_final };
            return updated;
          }

          // 新規追加
          return [...prev, { index, text, speaker, category, alignment, method, is_final }];
        });
      } else if (data.type === 'complete') {
        setStatus('complete');
        setMessage('文字起こしが完了しました。');
        ws.close();
      } else if (data.type === 'error') {
        setMessage(data.message);
      }
    };
    ws.onerror = (error) => {
      console.error('❌ WebSocketエラー:', error);
      setMessage('WebSocket への接続に失敗しました。');
    };
    ws.onclose = (event) => {
      console.log('🔌 WebSocket切断:', event.code, event.reason);
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

  // 時間を「MM:SS」形式にフォーマット
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // タイマーの状態を判定（normal / warning / danger）
  const getTimerStatus = (): 'normal' | 'warning' | 'danger' => {
    if (!scheduledMinutes) return 'normal';
    const scheduledSeconds = scheduledMinutes * 60;
    const remainingSeconds = scheduledSeconds - elapsedSeconds;
    const remainingPercent = (remainingSeconds / scheduledSeconds) * 100;

    if (remainingSeconds <= 0) return 'danger'; // 超過
    if (remainingPercent <= 15) return 'warning'; // 残り15%以下
    return 'normal';
  };

  // 音声アラートを再生
  const playVoiceAlert = (message: string) => {
    // 既存の音声を停止
    if (speechSynthRef.current) {
      window.speechSynthesis.cancel();
    }

    // 新しい音声を作成
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.lang = 'ja-JP';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    speechSynthRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  };

  // 直近10件の平均一致度をチェック
  useEffect(() => {
    if (status !== 'streaming' || realtimeClassifications.length === 0) {
      // ストリーミング中でない場合はアラートをクリア
      if (alertIntervalRef.current) {
        clearInterval(alertIntervalRef.current);
        alertIntervalRef.current = null;
      }
      setShowWarning(false);
      return;
    }

    const validItems = realtimeClassifications.filter(item => item.text.length >= 10);
    if (validItems.length < 3) {
      // 最低3件のデータがないとチェックしない
      setShowWarning(false);
      return;
    }

    // 直近10件の平均一致度を計算
    const recentItems = validItems.slice(-10);
    const avgAlignment = Math.round(
      recentItems.reduce((sum, item) => sum + item.alignment, 0) / recentItems.length
    );

    // 40%以下で画面に警告表示
    if (avgAlignment <= 40) {
      setShowWarning(true);
    } else {
      setShowWarning(false);
    }

    // 60%以下で音声アラートを20秒ごとに流す
    const shouldAlert = avgAlignment <= 60;
    const isAlertActive = alertIntervalRef.current !== null;

    if (shouldAlert && !isAlertActive) {
      // アラートを開始
      playVoiceAlert('一致度が下がっています');
      alertIntervalRef.current = window.setInterval(() => {
        playVoiceAlert('一致度が下がっています');
      }, 20000);
    } else if (!shouldAlert && isAlertActive) {
      // アラートを停止
      clearInterval(alertIntervalRef.current);
      alertIntervalRef.current = null;
    }
  }, [realtimeClassifications, status]);

  // クリーンアップ
  useEffect(() => {
    return () => {
      if (alertIntervalRef.current) {
        clearInterval(alertIntervalRef.current);
        alertIntervalRef.current = null;
      }
    };
  }, []);

  // ミーティングを終了してリザルト画面へ遷移
  const handleStopMeeting = () => {
    // 音声を停止
    if (speechSynthRef.current) {
      window.speechSynthesis.cancel();
    }

    // アラートインターバルを停止
    if (alertIntervalRef.current) {
      clearInterval(alertIntervalRef.current);
      alertIntervalRef.current = null;
    }

    // 全ての一致度の平均を計算
    const validItems = realtimeClassifications.filter(item => item.text.length >= 10);
    const avgAlignment = validItems.length > 0
      ? Math.round(validItems.reduce((sum, item) => sum + item.alignment, 0) / validItems.length)
      : 0;

    navigate('/result', {
      state: {
        agendaText: jobAgenda,
        elapsedSeconds: elapsedSeconds,
        avgAlignment: avgAlignment,
        totalItems: validItems.length,
      },
    });
  };

  return (
    <Layout title="MeetingPolice PoC Satomin" subtitle="アジェンダと音声をアップロードし、リアルタイム文字起こしを確認できます。">
      {showWarning && (
        <div style={{
          position: 'fixed',
          top: '20px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 9999,
          padding: '20px 40px',
          backgroundColor: '#ff1744',
          color: 'white',
          borderRadius: '12px',
          fontSize: '1.5em',
          fontWeight: 'bold',
          boxShadow: '0 8px 24px rgba(255, 23, 68, 0.4)',
          animation: 'pulse 1.5s ease-in-out infinite',
          border: '4px solid #fff'
        }}>
          ⚠️ 一致度が落ちています！ ⚠️
        </div>
      )}
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
                {(status === 'streaming' || status === 'complete') && (
                  <>
                    <p className="label">経過時間</p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                      <span
                        className="pill"
                        style={{
                          fontSize: '1.2em',
                          backgroundColor: getTimerStatus() === 'danger' ? '#f44336' : getTimerStatus() === 'warning' ? '#ff9800' : '#4caf50',
                          color: 'white'
                        }}
                      >
                        ⏱️ {formatTime(elapsedSeconds)}
                      </span>
                      {scheduledMinutes && (
                        <span style={{ fontSize: '0.9em', color: '#666' }}>
                          / {scheduledMinutes}分
                          {getTimerStatus() === 'danger' && ' ⚠️ 超過！'}
                          {getTimerStatus() === 'warning' && ' ⚠️ まもなく終了'}
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={handleStopMeeting}
                      style={{
                        width: '100%',
                        padding: '12px',
                        backgroundColor: '#f44336',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '1em',
                        fontWeight: 'bold',
                        cursor: 'pointer'
                      }}
                    >
                      ⏹️ ミーティングを終了
                    </button>
                  </>
                )}
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
              <div className="history-preview" style={{ fontSize: '0.85em', maxHeight: '400px', overflow: 'auto' }}>
                <p className="label">選択中: {historyPreview.archive_name || historyPreview.job_id}</p>
                <p className="label">アジェンダ（全文）</p>
                <pre style={{ fontSize: '0.9em', maxHeight: '150px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                  {historyPreview.agenda_text || '（なし）'}
                </pre>
                <p className="label">文字起こし（全文）</p>
                <div className="history-transcripts" style={{ fontSize: '0.85em', maxHeight: '200px', overflow: 'auto' }}>
                  {historyPreview.transcripts.map((item) => (
                    <p key={item.index} style={{ margin: '4px 0' }}>
                      <strong>{item.speaker}:</strong> {item.text}
                    </p>
                  ))}
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

          <section className="panel">
            <div className="panel-header" style={{ flexWrap: 'nowrap', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'nowrap' }}>
                <p className="label" style={{ margin: 0, whiteSpace: 'nowrap' }}>🔍 リアルタイム分析</p>
                <h2 style={{ margin: 0, whiteSpace: 'nowrap' }}>{realtimeClassifications.length} 件</h2>
              </div>
            </div>

            {realtimeClassifications.length > 0 && (() => {
              // コメント（短い発言）を除外
              const validItems = realtimeClassifications.filter(item => item.text.length >= 10);
              if (validItems.length === 0) return null;

              // 直近10件の平均一致度を計算
              const recentItems = validItems.slice(-10);
              const avgAlignment = Math.round(
                recentItems.reduce((sum, item) => sum + item.alignment, 0) / recentItems.length
              );
              const avgColor = avgAlignment >= 50 ? '#4caf50' : avgAlignment >= 30 ? '#ff9800' : '#f44336';

              return (
                <div style={{
                  padding: '20px',
                  textAlign: 'center',
                  backgroundColor: '#f5f5f5',
                  borderRadius: '8px',
                  marginBottom: '16px'
                }}>
                  <p style={{ margin: '0 0 8px 0', fontSize: '0.9em', color: '#666' }}>
                    直近の平均一致度（最新10件）
                  </p>
                  <div style={{
                    fontSize: '3em',
                    fontWeight: 'bold',
                    color: avgColor,
                    lineHeight: '1'
                  }}>
                    {avgAlignment}%
                  </div>
                </div>
              );
            })()}

            <div className="transcript-feed" style={{ maxHeight: '500px', overflowY: 'auto' }}>
              {realtimeClassifications
                .filter(item => item.text.length >= 10)
                .map((item, index) => {
                  const isFinal = item.is_final === true;
                  const icon = isFinal ? '✅' : '📊';
                  const bgColor = item.alignment >= 50 ? '#4caf50' : item.alignment >= 20 ? '#ff9800' : '#f44336';

                  return (
                    <article key={index} className="transcript-item">
                      <header>
                        <strong>{item.speaker}</strong>
                        <span className="pill">{item.category}</span>
                        <span className="pill" style={{ backgroundColor: bgColor }}>
                          {icon} {item.alignment}%
                        </span>
                        {isFinal && <span className="pill" style={{ backgroundColor: '#2196f3', color: 'white' }}>AI確定</span>}
                      </header>
                      <p>{item.text}</p>
                    </article>
                  );
                })}
              {realtimeClassifications.filter(item => item.text.length >= 10).length === 0 && <p className="faded">文字起こし完了後にリアルタイム分析結果が表示されます。</p>}
            </div>
          </section>
        </div>
      </div>
    </Layout>
  );
}
