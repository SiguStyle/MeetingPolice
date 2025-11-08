export type Participant = {
  id: string;
  name: string;
  role: 'host' | 'guest';
  isSpeaking: boolean;
};

export type MeetingSession = {
  meetingId: string;
  title: string;
  status: string;
  sessionId: string;
  token: string;
  participants: Participant[];
};

export type AnalyticsSample = {
  timestamp: string;
  sentiment: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL' | 'MIXED';
  energyScore: number;
  talkTimeSeconds: number;
};
