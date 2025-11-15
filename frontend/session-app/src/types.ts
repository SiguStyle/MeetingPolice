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

export type PocTranscript = {
  index: number;
  speaker: string;
  text: string;
  timestamp: string;
};

export type PocJobDetail = {
  job_id: string;
  status: string;
  agenda_text: string;
  audio_filename: string;
  transcripts: PocTranscript[];
};

export type PocAnalysisResult = {
  job_id: string;
  agenda_text: string;
  summary: { meeting_id: string; summary: string };
  sentiment: Record<string, unknown>;
  transcript_sample: PocTranscript[];
  guidance: string[];
};
