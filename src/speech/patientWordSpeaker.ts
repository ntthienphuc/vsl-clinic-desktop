import type { Message, SessionState } from '../types';

export interface VoiceEntry { id: string; text: string; file: string; duration_ms: number }
export interface VoiceEvent { type: string; message_id?: string; text?: string; latency_ms?: number; recorded_at_ms?: number; detail?: string }
type AudioLike = Pick<HTMLAudioElement, 'onended' | 'onerror' | 'onplaying' | 'play' | 'pause'>;
interface QueuedWord { word: Message; clips: VoiceEntry[]; received: number }
const key = (text: string) => text.normalize('NFC').toLocaleLowerCase('vi').replace(/[.!?]+$/u, '').trim();

/** One voice on the doctor screen. Word IDs, not text, identify new results. */
export class PatientWordSpeaker {
  private seen = new Set<string>();
  private context = '';
  private baseline = true;
  private wasActive = false;
  private queue: QueuedWord[] = [];
  private audio: AudioLike | null = null;
  private timer?: ReturnType<typeof setTimeout>;
  private generation = 0;
  private byText: Map<string, VoiceEntry>;
  private byId: Map<string, VoiceEntry>;
  constructor(entries: VoiceEntry[],
    private makeAudio: (url: string) => AudioLike,
    private gate: (playing: boolean) => void,
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
      this.seen.clear();
      this.baseline = true;
      this.cancel();
    }
    if (!connected || !enabled || ended) this.cancel();
    if (!connected) this.baseline = true;
    const seed = this.baseline || !enabled || !connected || ended;
    for (const word of words) {
      if (this.seen.has(word.id)) continue;
      if (seed) { this.seen.add(word.id); continue; }
      // Keep uncertain words visible, but do not speak a guess. A later
      // confirmation of the same ID is eligible exactly once.
      if (word.uncertain && word.status !== 'confirmed') continue;
      this.seen.add(word.id);
      // A manually corrected word must never play the original prediction.
      const identified = word.voice_key ? this.byId.get(word.voice_key) : undefined;
      const entry = identified && key(identified.text) === key(word.text) ? identified : this.byText.get(key(word.text));
      if (!entry) {
        this.emit({ type: 'error', message_id: word.id, text: word.text, detail: 'Chưa có giọng đọc cho từ này. Nội dung chữ vẫn được giữ.' });
        continue;
      }
      if (this.queue.length >= 24) {
        this.cancel();
        this.emit({ type: 'error', detail: 'Giọng đọc đang chậm hơn ký hiệu. Bật lại giọng đọc để tiếp tục; các từ vẫn hiện đầy đủ.' });
        // Baseline the rest of this snapshot rather than reading a partial backlog.
        words.forEach((item) => this.seen.add(item.id));
        break;
      }
      const clips = [entry];
      this.queue.push({ word, clips, received: this.clock() });
      this.emit({ type: 'queued', message_id: word.id, text: word.text });
    }
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
      this.emit({ type: 'cancelled' });
    }
    this.gate(false);
  }

  private drain() {
    if (this.audio || !this.queue.length) return;
    const item = this.queue.shift()!;
    this.gate(true); // Subscribers stop microphone PCM synchronously, before play().
    this.playClip(item, 0, this.generation);
  }

  private playClip(item: QueuedWord, index: number, generation: number) {
    const clip = item.clips[index];
    const audio = this.makeAudio(`/assets/patient-voice/${encodeURIComponent(clip.file)}`);
    this.audio = audio;
    const valid = () => generation === this.generation && this.audio === audio;
    const fail = () => {
      if (!valid()) return;
      this.cancel();
      this.emit({ type: 'error', message_id: item.word.id, detail: 'Không phát được giọng đọc. Kiểm tra loa rồi bật lại giọng đọc.' });
    };
    audio.onplaying = () => {
      if (valid() && index === 0) this.emit({ type: 'playing', message_id: item.word.id, text: item.word.text, latency_ms: Math.round(this.clock() - item.received) });
    };
    audio.onerror = fail;
    audio.onended = () => {
      if (!valid()) return;
      clearTimeout(this.timer);
      audio.onended = audio.onerror = audio.onplaying = null;
      this.audio = null;
      if (index + 1 < item.clips.length) {
        this.playClip(item, index + 1, generation);
      } else {
        this.emit({ type: 'ended', message_id: item.word.id, text: item.word.text });
        if (this.queue.length) this.drain();
        else this.gate(false);
      }
    };
    this.timer = setTimeout(fail, clip.duration_ms + 5000);
    void audio.play().catch(fail);
  }
}
