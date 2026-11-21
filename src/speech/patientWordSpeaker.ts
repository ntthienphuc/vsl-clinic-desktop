import type { Message, SessionState } from '../types';

export interface VoiceEntry { id: string; text: string; file: string; duration_ms: number; warning?: { file: string; prefix_ms: number; duration_ms: number } }
export interface VoiceEvent { type: string; message_id?: string; text?: string; uncertain?: boolean; latency_ms?: number; recorded_at_ms?: number; media_time_ms?: number; clip_file?: string; detail?: string }
type AudioLike = Pick<HTMLAudioElement, 'onended' | 'onerror' | 'onplaying' | 'play' | 'pause' | 'currentTime'>;
interface QueuedWord { word: Message; clip: VoiceEntry; received: number }
const key = (text: string) => text.normalize('NFC').toLocaleLowerCase('vi').replace(/[.!?]+$/u, '').trim();
/** One voice on the doctor screen. Word IDs, not text, identify new results. */
export class PatientWordSpeaker {
  private seen = new Map<string, string>();
  private previous = new Map<string, string>();
  private session = '';
  private context = '';
  private baseline = true;
  private wasActive = false;
  private queue: QueuedWord[] = [];
  private audio: AudioLike | null = null;
  private audioWord = '';
  private timer?: ReturnType<typeof setTimeout>;
  private generation = 0;
  private byText: Map<string, VoiceEntry>;
  private byId: Map<string, VoiceEntry>;
  constructor(entries: VoiceEntry[],
    private makeAudio: (url: string) => AudioLike,
    private emit: (event: VoiceEvent) => void,
    private clock: () => number = () => performance.now()) {
    this.byText = new Map(entries.filter((item) => item.id !== 'uncertain').map((item) => [key(item.text), item]));
    this.byId = new Map(entries.map((item) => [item.id, item]));
  }

  sync(state: SessionState, enabled: boolean, connected: boolean) {
    const words = state.messages.flatMap((turn) => turn.words ?? []).filter((word) => word.role === 'patient' && !word.manual);
    const context = `${state.session_id}:${state.capture.generation}`;
    const ended = this.wasActive && state.conversation.status !== 'active';
    this.wasActive = state.conversation.status === 'active';
    if (context !== this.context) {
      this.context = context;
      if (this.session !== state.session_id) {
        this.session = state.session_id;
        this.seen.clear();
        this.baseline = true;
      } else {
        // An entire source-start + first-result update may be batched into one
        // React render. Baseline only words actually seen before that update.
        this.previous.forEach((text, id) => this.seen.set(id, text));
      }
      this.cancel();
    }
    if (!connected || !enabled || ended) this.cancel();
    if (!connected) this.baseline = true;
    const seed = this.baseline || !enabled || !connected || ended;
    for (const word of words) {
      const spokenText = key(word.text);
      if (this.seen.get(word.id) === spokenText) continue;
      if (seed) { this.seen.set(word.id, spokenText); continue; }
      this.seen.set(word.id, spokenText);
      // Read each result immediately. Recognition ranks are not confirmation.
      // A changed correction is a new reading; identical text is not repeated.
      const identified = word.voice_key ? this.byId.get(word.voice_key) : undefined;
      const entry = identified && key(identified.text) === key(word.text) ? identified : this.byText.get(key(word.text));
      if (!entry) {
        this.emit({ type: 'error', message_id: word.id, text: word.text, detail: 'Chưa có giọng đọc cho từ này. Nội dung chữ vẫn được giữ.' });
        continue;
      }
      // Replace an outdated queued/current candidate when its text is corrected.
      this.queue = this.queue.filter(item => item.word.id !== word.id);
      if (this.audio && this.audioWord === word.id) {
        clearTimeout(this.timer);
        this.audio.onended = this.audio.onerror = this.audio.onplaying = null;
        this.audio.pause();
        this.audio = null;
        this.audioWord = '';
      }
      if (this.queue.length >= 24) {
        this.cancel();
        this.emit({ type: 'error', detail: 'Giọng đọc đang chậm hơn ký hiệu. Bật lại giọng đọc để tiếp tục; các từ vẫn hiện đầy đủ.' });
        // Baseline the rest of this snapshot rather than reading a partial backlog.
        words.forEach((item) => this.seen.set(item.id, key(item.text)));
        break;
      }
      this.queue.push({ word, clip: entry, received: this.clock() });
      this.emit({ type: 'queued', message_id: word.id, text: word.text, uncertain: word.uncertain });
    }
    this.previous = new Map(words.map(word => [word.id, key(word.text)]));
    this.baseline = !connected;
    this.drain();
  }

  cancel() {
    this.generation += 1;
    clearTimeout(this.timer);
    this.queue = [];
    if (this.audio) {
      this.audio.onended = this.audio.onerror = this.audio.onplaying = null;
      this.audio.pause();
      this.audio = null;
      this.audioWord = '';
      this.emit({ type: 'cancelled' });
    }
  }

  private drain() {
    if (this.audio || !this.queue.length) return;
    const item = this.queue.shift()!;
    this.playClip(item, this.generation);
  }

  private playClip(item: QueuedWord, generation: number) {
    const clip = item.clip;
    const file = clip.file;
    const audio = this.makeAudio(`/assets/patient-voice/${encodeURIComponent(file)}`);
    this.audio = audio;
    this.audioWord = item.word.id;
    const valid = () => generation === this.generation && this.audio === audio;
    let started = false, announced = false;
    const event = (type: string) => this.emit({ type, message_id: item.word.id, text: item.word.text,
      uncertain: item.word.uncertain, latency_ms: Math.round(this.clock() - item.received),
      media_time_ms: audio.currentTime * 1000, clip_file: file });
    const markWord = () => {
      if (!valid() || !started || announced) return;
      announced = true;
      event('playing');
    };
    const fail = () => {
      if (!valid()) return;
      this.cancel();
      this.emit({ type: 'error', message_id: item.word.id, detail: 'Không phát được giọng đọc. Kiểm tra loa rồi bật lại giọng đọc.' });
    };
    audio.onplaying = () => {
      if (!valid() || started) return;
      started = true;
      markWord();
    };
    audio.onerror = fail;
    audio.onended = () => {
      if (!valid()) return;
      markWord();
      clearTimeout(this.timer);
      audio.onended = audio.onerror = audio.onplaying = null;
      this.audio = null;
      this.audioWord = '';
      this.emit({ type: 'ended', message_id: item.word.id, text: item.word.text });
      if (this.queue.length) this.drain();
    };
    this.timer = setTimeout(fail, clip.duration_ms + 5000);
    void audio.play().catch(fail);
  }
}
