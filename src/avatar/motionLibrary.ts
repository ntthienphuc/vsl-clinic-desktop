import type { Motion } from '../types';
import { curateHands } from './curatedHands';
import { decodePackedMotion } from './packedMotion';

/** Load complete motions only when a sentence needs them. Never change samples. */
export class MotionLibrary {
  readonly motions = new Map<string, Motion>();
  private pending = new Map<string, Promise<void>>();
  private wanted = new Set<string>();
  private controller = new AbortController();
  private paths: Map<string, string>;
  constructor(entries: { id: string; path: string }[], private limit = 24) {
    this.paths = new Map(entries.map(entry => [entry.id, entry.path]));
  }
  async prepare(ids: string[]) {
    this.wanted = new Set(ids);
    // At most 24 glosses are accepted by the sentence planner.
    await Promise.all([...this.wanted].map(id => this.load(id)));
    this.trim();
  }
  private load(id: string): Promise<void> {
    const cached = this.motions.get(id);
    if (cached) {
      this.motions.delete(id);
      this.motions.set(id, cached);
      return Promise.resolve();
    }
    const active = this.pending.get(id);
    if (active) return active;
    const path = this.paths.get(id);
    if (!path) return Promise.reject(new Error(`Chưa tìm thấy chuyển động ${id}`));
    const task = fetch(path, { signal: this.controller.signal }).then(async response => {
      if (!response.ok) throw new Error(`Chưa tải được chuyển động ${id}`);
      const motion = path.endsWith('.vslm') ? decodePackedMotion(await response.arrayBuffer()) : await response.json() as Motion;
      if (motion.id !== id || !motion.frames?.length) throw new Error(`Chuyển động ${id} chưa hợp lệ`);
      if (!this.controller.signal.aborted) this.motions.set(id, curateHands(motion));
    }).finally(() => { this.pending.delete(id); this.trim(); });
    this.pending.set(id, task);
    return task;
  }
  private trim() {
    for (const id of this.motions.keys()) {
      if (this.motions.size <= this.limit) break;
      if (!this.wanted.has(id)) this.motions.delete(id);
    }
  }
  dispose() {
    this.controller.abort();
    this.motions.clear();
    this.wanted.clear();
  }
}
