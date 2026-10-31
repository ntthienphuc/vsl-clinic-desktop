import type { Motion, Playback, Point } from '../types';

export const INTRO_MS = 350;
export const TRANSITION_MS = 280;
export const OUTRO_MS = 350;

export function neutralPose(): Point[] {
  const points: Point[] = Array.from({ length: 75 }, () => [0, 0, 0]);
  points[0] = [0, 0.6, 0.12];
  for (const side of [0, 1]) {
    const sign = side === 0 ? 1 : -1;
    points[11 + side] = [sign * 0.5, 0, 0];
    points[13 + side] = [sign * 0.68, -0.86, 0.08];
    points[15 + side] = [sign * 0.90, -1.70, 0.25];
    points[23 + side] = [sign * 0.35, -1.2, 0];
    const start = 33 + side * 21;
    const wrist = points[15 + side];
    const hand: Point[] = [
      [0, 0, 0], [0.05, -0.03, 0.01], [0.10, -0.08, 0.02], [0.13, -0.13, 0.03], [0.15, -0.18, 0.04],
      [0.06, -0.16, 0], [0.07, -0.25, 0.01], [0.07, -0.31, 0.02], [0.07, -0.36, 0.03],
      [0, -0.18, 0], [0, -0.28, 0.01], [0, -0.35, 0.02], [0, -0.40, 0.03],
      [-0.05, -0.17, 0], [-0.06, -0.26, 0.01], [-0.06, -0.32, 0.02], [-0.06, -0.37, 0.03],
      [-0.10, -0.14, 0], [-0.12, -0.21, 0.01], [-0.12, -0.26, 0.02], [-0.12, -0.30, 0.03],
    ];
    for (let index = 0; index < hand.length; index += 1) {
      points[start + index] = [wrist[0] + sign * hand[index][0], wrist[1] + hand[index][1], wrist[2] + hand[index][2]];
    }
  }
  return points;
}

export function blendPose(a: Point[], b: Point[], t: number): Point[] {
  const amount = Math.max(0, Math.min(1, t));
  return a.map((point, index) => [
    point[0] + (b[index][0] - point[0]) * amount,
    point[1] + (b[index][1] - point[1]) * amount,
    point[2] + (b[index][2] - point[2]) * amount,
  ]);
}

export function sampleMotion(motion: Motion, timeMs: number): Point[] {
  const frame = Math.min(motion.frames.length - 1, Math.max(0, timeMs / motion.duration_ms * (motion.frames.length - 1)));
  const lower = Math.floor(frame);
  const upper = Math.min(motion.frames.length - 1, lower + 1);
  const t = frame - lower;
  const before = motion.frames[Math.max(0, lower - 1)];
  const after = motion.frames[Math.min(motion.frames.length - 1, upper + 1)];
  // Monotone cubic Hermite interpolation keeps each coordinate within its two
  // measured endpoints. It removes framewise velocity corners without ringing
  // beyond a recorded fingertip/contact or flattening deliberate direction changes.
  const tangent = (a: number, b: number) => a * b <= 0 ? 0 : 2 * a * b / (a + b);
  return motion.frames[lower].map((point, index) => point.map((a, axis) => {
    const b = motion.frames[upper][index][axis];
    const slope = b - a;
    const m0 = tangent(a - before[index][axis], slope);
    const m1 = tangent(slope, after[index][axis] - b);
    return (2 * t ** 3 - 3 * t ** 2 + 1) * a + (t ** 3 - 2 * t ** 2 + t) * m0
      + (-2 * t ** 3 + 3 * t ** 2) * b + (t ** 3 - t ** 2) * m1;
  }) as Point);
}

function eased(value: number): number {
  const x = Math.max(0, Math.min(1, value));
  return x * x * (3 - 2 * x);
}

export function elapsedPlayback(playback: Playback, now = Date.now()): number {
  const delta = playback.status === 'playing' ? (now - playback.started_at_ms) * playback.rate : 0;
  return Math.max(0, Math.min(playback.total_ms, playback.elapsed_ms + delta));
}

export function samplePlaylist(playback: Playback | null, motions: Map<string, Motion>, now = Date.now()) {
  const neutral = neutralPose();
  const idle = { pose: neutral, label: '', progress: 0, complete: false, index: -1, phase: 'idle' };
  if (!playback || ['completed', 'stopped', 'loading'].includes(playback.status)) {
    return idle;
  }
  const elapsed = elapsedPlayback(playback, now);
  const progress = elapsed / playback.total_ms;
  const list = playback.glosses.map((item) => motions.get(item.id));
  if (list.some((item) => !item)) {
    return idle;
  }
  const clips = list as Motion[];
  if (elapsed >= playback.total_ms) {
    return { ...idle, progress: 1, complete: true };
  }
  const segment = playback.timeline.find((item) => elapsed >= item.start_ms && elapsed < item.end_ms);
  if (!segment || !clips[segment.index]) {
    return idle;
  }
  const clip = clips[segment.index];
  const ratio = (elapsed - segment.start_ms) / (segment.end_ms - segment.start_ms);
  let pose = neutral;
  if (segment.phase === 'sign') {
    pose = sampleMotion(clip, segment.source_start_ms! + elapsed - segment.start_ms);
  } else if (segment.phase === 'intro') {
    pose = blendPose(neutral, sampleMotion(clip, segment.source_ms!), eased(ratio));
  } else if (segment.phase === 'outro') {
    pose = blendPose(sampleMotion(clip, segment.source_ms!), neutral, eased(ratio));
  } else if (segment.phase === 'bridge') {
    pose = blendPose(sampleMotion(clips[segment.from_index!], segment.from_ms!), sampleMotion(clip, segment.to_ms!), eased(ratio));
  }
  const showWord = segment.phase !== 'outro' && segment.phase !== 'hold';
  return { pose, label: showWord ? clip.label : '', progress, complete: false, index: showWord ? segment.index : -1, phase: segment.phase };
}
