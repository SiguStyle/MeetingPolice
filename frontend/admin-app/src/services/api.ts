import type { Meeting } from '../types';

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

type MeetingDto = {
  meeting_id: string;
  title: string;
  status: Meeting['status'];
  scheduled_for: string;
  created_at: string;
  session_id?: string | null;
  summary_s3_key?: string | null;
};

function mapMeeting(item: MeetingDto): Meeting {
  return {
    meetingId: item.meeting_id,
    title: item.title,
    status: item.status,
    scheduledFor: item.scheduled_for,
    createdAt: item.created_at,
    sessionId: item.session_id,
    summaryKey: item.summary_s3_key,
  };
}

export async function fetchMeetings(): Promise<Meeting[]> {
  const raw = await request<MeetingDto[]>('/admin/meetings');
  return raw.map(mapMeeting);
}

export async function createMeeting(title: string, scheduledFor?: string): Promise<Meeting> {
  const payload: Record<string, string> = { title };
  if (scheduledFor) payload.scheduled_for = scheduledFor;
  const response = await request<MeetingDto>('/admin/meetings', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return mapMeeting(response);
}
