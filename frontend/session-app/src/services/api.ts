import type { MeetingSession } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `API ${res.status}`);
  }

  return res.json() as Promise<T>;
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
