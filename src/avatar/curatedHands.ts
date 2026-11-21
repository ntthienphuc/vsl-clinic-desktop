import * as THREE from 'three';
import type { Motion, Point } from '../types';
import { palmBasis } from './kinematics';
import curation from '../../assets/motions/hand-curation.json';

type Shape = 'flat' | 'open' | 'relaxed' | 'fist' | 'index' | 'pair' | 'v' | 'three' | 'four' | 'thumb' | 'cup' | 'claw' | 'pinch' | 'ring' | 'l' | 'phone';
interface Key { at: number; shape: Shape; weight?: number }
interface Rule { left?: Key[]; right?: Key[]; source_sha256: string[] }
const rules = curation.words as unknown as Record<string, Rule>;
const bend = (a: number, b: number, c: number) => [a, b, c];
const straight = bend(1, 4, 2), curled = bend(72, 100, 55), loose = bend(18, 28, 12);

function fingers(shape: Shape): number[][] {
  const out = Array.from({ length: 4 }, () => [...straight]);
  if (['fist', 'thumb', 'index', 'pair', 'v', 'three', 'l', 'phone', 'pinch'].includes(shape)) out.forEach((_, i) => { out[i] = [...curled]; });
  if (['index', 'l', 'pair', 'v'].includes(shape)) out[0] = [...straight];
  if (['pair', 'v'].includes(shape)) out[1] = [...straight];
  if (shape === 'three') for (let i = 0; i < 3; i++) out[i] = [...straight];
  if (shape === 'phone') out[3] = [...straight];
  if (shape === 'relaxed') out.forEach((_, i) => { out[i] = [...loose]; });
  if (shape === 'cup' || shape === 'claw') out.forEach((_, i) => { out[i] = bend(24, 48, 24); });
  if (shape === 'pinch' || shape === 'ring') out[0] = bend(42, 78, 40);
  return out;
}

function targetHand(points: Point[], side: 'left' | 'right', shape: Shape): Point[] | null {
  const world = points.map(p => new THREE.Vector3(...p));
  const frame = palmBasis(world);
  if (!frame) return null;
  const local = world.map(p => p.clone().sub(world[0]).applyQuaternion(frame.clone().invert()));
  const height = local[9].length();
  if (height < .04) return null;
  const palmar = side === 'left' ? -1 : 1;
  const bends = fingers(shape);
  for (let finger = 0; finger < 4; finger++) {
    const base = 5 + finger * 4;
    // Keep the source palm and its location/orientation. Reconstruct only the
    // phalanges in the palm frame, with one hinge plane per finger.
    let flex = 0;
    const spread = shape === 'v' ? [12, -12, 0, 0][finger]
      : ['open', 'claw', 'three', 'four'].includes(shape) ? [12, 0, -9, -18][finger] : 0;
    const yaw = THREE.MathUtils.degToRad(spread);
    for (let j = 0; j < 3; j++) {
      const length = THREE.MathUtils.clamp(world[base + j + 1].distanceTo(world[base + j]), height * .16, height * .64);
      flex += THREE.MathUtils.degToRad(bends[finger][j]);
      const direction = new THREE.Vector3(Math.sin(yaw) * Math.cos(flex), Math.cos(yaw) * Math.cos(flex), palmar * Math.sin(flex));
      local[base + j + 1] = local[base + j].clone().addScaledVector(direction, length);
    }
  }
  const thumbTargets: Record<string, number[][]> = {
    flat: [[.50,.32,.03],[.59,.69,.04],[.56,.98,.05],[.48,1.21,.05]],
    fist: [[.62,.32,.04],[.80,.57,.20],[.49,.78,.40],[.13,.73,.46]],
    thumb: [[.59,.35,.02],[.92,.61,.05],[1.14,.89,.05],[1.29,1.17,.05]],
    l: [[.59,.35,.02],[.92,.55,.05],[1.21,.69,.05],[1.50,.79,.05]],
    pinch: [[.56,.35,.03],[.76,.65,.17],[.53,.97,.37],[.27,1.10,.46]],
    cup: [[.61,.33,.03],[.93,.60,.16],[1.06,.90,.32],[1.00,1.12,.43]],
  };
  const thumbShape = ['fist', 'index', 'pair', 'v', 'three', 'four'].includes(shape) ? 'fist'
    : ['ring', 'pinch'].includes(shape) ? 'pinch' : shape === 'phone' ? 'thumb'
    : ['open', 'claw', 'relaxed'].includes(shape) ? 'cup' : shape;
  const thumb = thumbTargets[thumbShape] ?? thumbTargets.flat;
  thumb.forEach((p, i) => { local[i + 1] = new THREE.Vector3(p[0] * height, p[1] * height, p[2] * height * palmar); });
  return local.map(p => p.applyQuaternion(frame).add(world[0]).toArray() as Point);
}

/** Apply reviewed presentation data once when a motion enters the bounded LRU.
 * Originals and provenance remain byte-identical. Temporal blend happens before
 * playlist interpolation, so bridges use the same corrected endpoint poses. */
export function curateHands(motion: Motion): Motion {
  const rule = rules[motion.id];
  const hashes = (motion as Motion & { source_hashes?: string[] }).source_hashes ?? [];
  if (!rule || rule.source_sha256.length !== hashes.length || !rule.source_sha256.every((h, i) => h === hashes[i])) return motion;
  const frames = motion.frames.map((frame, index) => {
    const result = frame.map(p => [...p] as Point);
    const phase = index / Math.max(1, motion.frames.length - 1);
    for (const [side, start] of [['left', 33], ['right', 54]] as const) {
      const track = rule[side];
      if (!track?.length) continue;
      const lower = [...track].reverse().find(k => k.at <= phase) ?? track[0];
      const upper = track.find(k => k.at > phase) ?? track[track.length - 1];
      const x = lower === upper ? 0 : (phase - lower.at) / (upper.at - lower.at);
      const mix = THREE.MathUtils.smoothstep(x, 0, 1);
      const a = targetHand(frame.slice(start, start + 21), side, lower.shape);
      const b = targetHand(frame.slice(start, start + 21), side, upper.shape);
      if (!a || !b) continue;
      const weight = THREE.MathUtils.lerp(lower.weight ?? 1, upper.weight ?? 1, mix);
      for (let point = 1; point < 21; point++) for (let axis = 0; axis < 3; axis++) {
        const target = THREE.MathUtils.lerp(a[point][axis], b[point][axis], mix);
        result[start + point][axis] += (target - result[start + point][axis]) * weight;
      }
    }
    return result;
  });
  return { ...motion, frames };
}
