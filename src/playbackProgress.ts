import { elapsedPlayback } from './avatar/motion';
import type { Playback } from './types';

/** Read the same authoritative timeline used by the patient renderer. */
export function playbackProgress(playback: Playback, now = Date.now()) {
  const elapsed = playback.status === 'loading' ? 0 : playback.status === 'completed' ? playback.total_ms : elapsedPlayback(playback, now);
  const segment = playback.timeline.find(item => item.start_ms <= elapsed && elapsed < item.end_ms);
  const index = segment?.index ?? (elapsed >= playback.total_ms ? playback.glosses.length - 1 : 0);
  return {
    elapsed,
    percent: playback.total_ms > 0 ? Math.min(100, elapsed / playback.total_ms * 100) : 0,
    index,
    label: playback.glosses[index]?.label ?? '',
    phase: segment?.phase ?? 'outro',
    remainingSeconds: Math.max(0, Math.ceil((playback.total_ms - elapsed) / Math.max(.1, playback.rate) / 1000)),
  };
}
