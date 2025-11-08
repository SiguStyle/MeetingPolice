export type Meeting = {
  meetingId: string;
  title: string;
  status: 'scheduled' | 'live' | 'completed';
  scheduledFor: string;
  createdAt: string;
  sessionId?: string | null;
  summaryKey?: string | null;
};
