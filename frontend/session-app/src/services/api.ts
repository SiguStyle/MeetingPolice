import type { MeetingSession } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';

const fallbackMessages: Record<number, string> = {
  404: '入力されたIDのミーティングは開催されていません',
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });

  if (!response.ok) {
    const contentType = response.headers.get('content-type') ?? '';
    let message: string | undefined;
    if (contentType.includes('application/json')) {
      try {
        const body = await response.json();
        if (typeof body?.detail === 'string') {
          message = body.detail;
        } else if (typeof body?.message === 'string') {
          message = body.message;
        } else {
          message = JSON.stringify(body);
        }
      } catch {
        /* fall back to text below */
      }
    }
    if (!message) {
      const text = await response.text();
      message = text || `${response.status} ${response.statusText || 'Error'}`;
    }
    if (response.status in fallbackMessages) {
      const fallback = fallbackMessages[response.status];
      if (!message || /not\s+found/i.test(message)) {
        message = fallback;
      }
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export async function joinMeeting(meetingId: string): Promise<MeetingSession> {
  const response = await request<{
    meeting_id: string;
    title: string;
    status: string;
    session_id: string;
    token: string;
  }>(`/session/meetings/${meetingId}/join`, { method: 'POST' });

  return {
    meetingId: response.meeting_id,
    title: response.title,
    status: response.status,
    sessionId: response.session_id,
    token: response.token,
    participants: [
      { id: 'me', name: 'You', role: 'host', isSpeaking: false },
      { id: 'cohost', name: 'Co-host', role: 'guest', isSpeaking: true },
    ],
  };
}
