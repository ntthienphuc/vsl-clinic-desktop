import type { Playback } from '../types';

export interface NarrationEntry {
  id: string; text: string; file: string; duration_ms: number;
  envelope_step_ms: number; envelope: number[];
  words: { text: string; start_ms: number; end_ms: number }[];
}
export type Mouth = Record<'aa' | 'ee' | 'ih' | 'oh' | 'ou', number>;
export const closedMouth = (): Mouth => ({ aa: 0, ee: 0, ih: 0, oh: 0, ou: 0 });

/** Approximate voiced vowel shapes, driven by actual audio time and energy.
 * This is not a phoneme aligner or a replacement for sign-language mouth grammar.
 */
export function mouthAt(entry: NarrationEntry, ms: number): Mouth {
  const mouth = closedMouth();
  if (ms < 0 || ms >= entry.duration_ms) return mouth;
  const position = ms / entry.envelope_step_ms;
  const index = Math.floor(position), fraction = position - index;
  const energy = ((entry.envelope[index] ?? 0) * (1 - fraction) + (entry.envelope[index + 1] ?? 0) * fraction) / 255;
  if (energy < .035) return mouth;
  const word = entry.words.find(w => ms >= w.start_ms && ms < w.end_ms);
  const vowels = word?.text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().match(/[aeiouy]/g) ?? ['a'];
  const ratio = word ? (ms - word.start_ms) / Math.max(1, word.end_ms - word.start_ms) : 0;
  const vowel = vowels[Math.min(vowels.length - 1, Math.floor(ratio * vowels.length))];
  const shape = ({ a: 'aa', e: 'ee', i: 'ih', y: 'ih', o: 'oh', u: 'ou' } as const)[vowel as 'a'] ?? 'aa';
  mouth[shape] = Math.min(.48, energy * .48);
  return mouth;
}

export class AvatarNarrator {
  private cycle = '';
  private bank: Map<string, NarrationEntry>;
  private clips = new Map<string, { audio: HTMLAudioElement; ready: boolean; failed: boolean }>();
  private current: HTMLAudioElement | null = null;
  private pending: HTMLAudioElement | null = null;
  private audible = false;
  private allowed = false;
  private finished = new Set<string>();
  private timers: ReturnType<typeof setTimeout>[] = [];
  private events: Record<string, unknown>[] = [];
  private smooth = closedMouth();
  constructor(entries: NarrationEntry[],
    private report: (event: Record<string, unknown>) => void,
    private makeAudio = (url: string) => new Audio(url)) {
    this.bank = new Map(entries.map(e => [e.id, e]));
  }
  private emit(event: Record<string, unknown>) {
    this.events = [...this.events.slice(-59), { ...event, at_ms: Date.now() }];
    this.report(event);
  }
  prepare(playback: Playback | null) {
    const cycle = playback ? playback.id + ':' + playback.iteration : '';
    if (cycle === this.cycle) return;
    this.dispose();
    this.cycle = cycle;
    for (const cue of playback?.audio_cues ?? []) {
      if (this.clips.has(cue.entry_id)) continue;
      const audio = this.makeAudio('/assets/avatar-voice/' + encodeURIComponent(cue.file));
      const slot = { audio, ready: false, failed: false };
      this.clips.set(cue.entry_id, slot);
      audio.preload = 'auto';
      audio.preservesPitch = true;
      const valid = () => this.cycle === cycle && this.clips.get(cue.entry_id) === slot;
      const fail = () => {
        if (!valid() || slot.failed) return;
        slot.ready = true; slot.failed = true;
        audio.pause();
        this.emit({ type: 'error', text: 'Chưa phát được giọng avatar. Ký hiệu và chữ vẫn tiếp tục.' });
      };
      audio.oncanplay = () => { if (valid()) slot.ready = true; };
      audio.onerror = fail;
      audio.onplaying = () => {
        if (!valid() || this.current !== audio || !this.allowed) { audio.pause(); return; }
        this.audible = true;
        this.emit({ type: 'playing', entry_id: cue.entry_id, text: cue.text });
      };
      audio.onpause = () => { if (this.current === audio) this.audible = false; };
      audio.onended = () => {
        if (!valid() || this.current !== audio) return;
        this.audible = false;
        this.emit({ type: 'ended', entry_id: cue.entry_id });
      };
      this.timers.push(setTimeout(() => { if (!slot.ready) fail(); }, 5000));
      audio.load();
    }
  }
  ready() { return [...this.clips.values()].every(slot => slot.ready); }
  tick(playback: Playback | null, enabled: boolean, connected: boolean, elapsed: number, dt: number) {
    this.prepare(playback);
    const cueIndex = playback?.audio_cues?.findIndex(cue => elapsed >= cue.start_ms && elapsed < cue.end_ms) ?? -1;
    const cue = playback?.audio_cues?.[cueIndex];
    const slot = cue ? this.clips.get(cue.entry_id) : undefined;
    const active = enabled && connected && playback?.status === 'playing' && cue && slot?.ready && !slot.failed;
    let target = closedMouth();
    let drift = 0;
    if (!active) {
      this.pause();
    } else {
      const audio = slot.audio;
      const key = this.cycle + ':' + cueIndex;
      if (this.current !== audio) { this.pause(); this.current = audio; }
      this.allowed = true;
      const expected = (elapsed - cue.start_ms) / 1000;
      drift = audio.currentTime - expected;
      if (!this.finished.has(key)) {
        if (audio.ended && expected > cue.duration_ms / 1000 - .2) this.finished.add(key);
        else {
          if (Math.abs(drift) > .18 || (audio.paused && this.pending !== audio)) audio.currentTime = expected;
          audio.playbackRate = playback.rate;
          if (audio.paused && this.pending !== audio) {
            this.pending = audio;
            const cycle = this.cycle;
            void audio.play().catch(() => {
              if (cycle === this.cycle) { slot.failed = true; this.emit({ type: 'error', text: 'Bật giọng avatar để thử phát lại âm thanh.' }); }
            }).finally(() => { if (this.pending === audio) this.pending = null; });
          }
          if (this.audible && !audio.paused && !audio.ended) {
            const entry = this.bank.get(cue.entry_id);
            if (entry) target = mouthAt(entry, audio.currentTime * 1000);
          }
        }
      }
    }
    // Close immediately on pause/mute/disconnect; soften only voiced motion.
    const alpha = Object.values(target).some(v => v > 0) ? 1 - Math.exp(-25 * dt) : 1;
    for (const shape of Object.keys(target) as (keyof Mouth)[]) this.smooth[shape] += (target[shape] - this.smooth[shape]) * alpha;
    return { mouth: { ...this.smooth }, speaking: this.audible && !!active, audioTimeMs: (this.current?.currentTime ?? 0) * 1000,
      driftMs: drift * 1000, cueIndex, events: this.events };
  }
  pause() {
    this.allowed = false;
    if (this.current && !this.current.paused) this.current.pause();
    this.audible = false;
  }
  dispose() {
    this.pause();
    for (const timer of this.timers) clearTimeout(timer);
    this.timers = [];
    for (const { audio } of this.clips.values()) {
      audio.oncanplay = audio.onerror = audio.onplaying = audio.onended = audio.onpause = null;
      audio.pause(); audio.removeAttribute('src'); audio.load();
    }
    this.clips.clear(); this.finished.clear(); this.current = this.pending = null;
    this.smooth = closedMouth(); this.cycle = '';
  }
}
