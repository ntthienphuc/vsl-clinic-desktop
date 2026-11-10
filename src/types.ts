export type Role = 'doctor' | 'patient';
export type RecognitionMode = 'fusion' | 'sign_only';
export interface RecognitionInfo {
  mode: RecognitionMode;
  labels: number;
  status: string;
  switching: boolean;
  requested_mode?: RecognitionMode;
  name?: string;
}
export type Point = [number, number, number];

export interface Word {
  id: string;
  label: string;
  model_id: number | null;
  category: string;
  demo: string | null;
  source_kind?: 'local-consensus' | 'qipedc-single';
}

export interface Prediction {
  gloss: string;
  score: number;
  model_id: number | null;
  class_id?: string;
  class_index?: number;
  original_gloss?: string;
  canonical_concept_id?: string;
  legacy_label_candidate?: number | null;
  voice_key?: string;
  engine_family?: string;
}

export interface Message {
  id: string;
  role: Role;
  text: string;
  created_at_ms: number;
  status: string;
  mode?: 'sign' | 'text';
  confidence?: number;
  uncertain?: boolean;
  voice_key?: string;
  original_gloss?: string;
  recognition?: Record<string, unknown>;
  quality_warning?: string | null;
  predictions?: Prediction[];
  context_candidates?: (Prediction & { reason: string })[];
  metrics?: Record<string, number | string | null>;
  manual?: boolean;
  glosses?: Gloss[];
  kind?: 'patient_turn';
  words?: Message[];
  raw_text?: string;
  speech_repair?: { rule: string; raw_text: string; corrected_text: string };
  reading?: { text: string; rewritten: boolean; rule: string };
  updated_at_ms?: number;
}

export interface Gloss {
  id: string;
  label: string;
  start: number;
  tokens: number;
}

export interface Playback {
  nonmanual?: 'neutral' | 'question';
  act?: string;
  id: string;
  message_id: string;
  text: string;
  glosses: Gloss[];
  status: 'loading' | 'playing' | 'paused' | 'completed' | 'stopped';
  elapsed_ms: number;
  started_at_ms: number;
  total_ms: number;
  requested_at_ms: number;
  rate: number;
  iteration: number;
  pause_reason?: 'patient_disconnected' | 'patient_reply' | 'patient_activity';
  audio_cues?: { entry_id: string; text: string; file: string; start_ms: number; end_ms: number; duration_ms: number }[];
  timeline_schema: 'clinic-playback-v2';
  timeline: TimelineSegment[];
  clauses: SentenceClause[];
}

export interface TimelineSegment {
  phase: 'intro' | 'sign' | 'bridge' | 'outro' | 'hold';
  start_ms: number;
  end_ms: number;
  index: number;
  source_ms?: number;
  source_start_ms?: number;
  source_end_ms?: number;
  from_index?: number;
  from_ms?: number;
  to_ms?: number;
}

export interface SentenceClause {
  text: string;
  gloss_start: number;
  gloss_end: number;
  nonmanual: 'neutral' | 'question';
  act: string;
  phrase_id: string | null;
  supported: boolean;
  explanation: string;
  start_ms?: number;
  end_ms?: number;
}

export interface CaptureState {
  status: string;
  generation: number;
  source_kind?: string;
  message?: string;
  has_pose?: boolean;
  hand_count?: number;
  captured?: number;
  processed?: number;
  dropped?: number;
  processed_fps?: number;
  detect_ms?: number;
  frame_age_ms?: number;
  queued_segments?: number;
  inflight_segments?: number;
  motion_detected?: boolean;
  has_face?: boolean;
  quality_warning?: string;
}

export interface ConversationSettings {
  status: 'idle' | 'active';
  mode: 'auto' | 'manual';
  epoch: string;
  source: { kind: 'camera' | 'demo'; camera_index?: number; demo_id?: string };
}

export interface SpeechDraft {
  id: string;
  text: string;
  reason: string;
  reason_code?: 'manual' | 'unclear' | 'unsupported' | 'busy';
  unsupported?: string[];
  supported: boolean;
  created_at_ms: number;
}

export interface SessionState {
  recognition?: RecognitionInfo;
  avatar_voice_enabled?: boolean;
  session_id: string;
  revision: number;
  server_time_ms: number;
  messages: Message[];
  capture: CaptureState;
  current_result: Message | null;
  playback: Playback | null;
  pending_count: number;
  clients: Record<Role, number>;
  conversation: ConversationSettings;
  patient_turn: Message | null;
  speech_drafts: SpeechDraft[];
  temporary?: { id: string; saved_at_ms: number; message_count: number; draft_count: number } | null;
}

export interface TemporaryConversation {
  id: string;
  saved_at_ms: number;
  messages: Message[];
  speech_drafts: SpeechDraft[];
}

export interface Bootstrap {
  recognition_catalogs: Record<RecognitionMode, Word[]>;
  quick_phrases?: { id: string; text: string; category: string; supported: boolean }[];
  patient_sources?: Word[];
  phrases: { id: string; text: string; explanation: string }[];
  speech: { available: boolean; loaded: boolean; name: string; endpoint_ms: number };
  vocabulary: Word[];
  avatar_url: string;
  bank: { entries: { id: string; path: string; duration_ms: number; reference_count: number }[] };
  model: { name: string; labels: number; sha256: string; capture_profile: string; family?: string };
  state: SessionState;
  server_time_ms: number;
}

export interface Motion {
  schema: string;
  id: string;
  label: string;
  duration_ms: number;
  frames: Point[][];
  confidence: number[][];
  reference_ids: string[];
  review_status: string;
}

export interface SemanticPlan {
  rule_id: string;
  intent: string;
  canonical_text: string;
  confidence: number;
  risk: 'safe' | 'review';
  source: string;
  explanation: string;
  decision: 'auto' | 'review';
  applied: boolean;
  omitted: { text: string; reason: string; start: number; end: number }[];
  matched: { text: string; concept: string | null; start: number; end: number }[];
  candidate_projection?: string[];
  message: string;
}

export interface TextPlan {
  mode: 'phrase' | 'word';
  nonmanual: 'neutral' | 'question';
  suggestions: { text: string; reason: string }[];
  text: string;
  supported: boolean;
  glosses: Gloss[];
  unsupported: { text: string; index: number }[];
  coverage: number;
  message: string;
  grammar_supported: boolean;
  clauses: SentenceClause[];
  issues: { text: string; reason: string }[];
  semantic?: SemanticPlan;
}

declare global {
  interface Window {
    clinicDesktop?: {
      displays: () => Promise<{ id: number; label: string; primary: boolean }[]>;
      arrange: (swap?: boolean) => Promise<void>;
      openPatient: () => Promise<void>;
      fullscreen: () => Promise<void>;
      quit: () => Promise<void>;
    };
    clinicDiagnostics?: Record<string, unknown>;
  }
}
