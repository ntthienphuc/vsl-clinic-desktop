import type { Motion, Point } from '../types';

/** Small, bounded int16 motion payload. Model/recognizer inputs are unrelated. */
export function decodePackedMotion(buffer: ArrayBuffer): Motion {
  const data = new DataView(buffer), bytes = new Uint8Array(buffer), text = new TextDecoder();
  if (buffer.byteLength < 16 || text.decode(bytes.subarray(0, 8)) !== 'VSLM1\0\0\0') throw Error('Chuyển động chưa hợp lệ');
  const size = data.getUint32(8, true), offset = 12 + size;
  if (size < 2 || size > 64_000 || offset > bytes.length) throw Error('Chuyển động chưa hợp lệ');
  const header = JSON.parse(text.decode(bytes.subarray(12, offset)));
  const count = header.frame_count;
  if (!Number.isInteger(count) || count < 2 || count > 2048 || !Number.isFinite(header.scale) || header.scale <= 0 || header.scale > 100_000
    || header.joint_count !== 75 || typeof header.id !== 'string' || typeof header.label !== 'string'
    || !Number.isFinite(header.duration_ms) || header.duration_ms <= 0 || header.duration_ms > 120_000
    || offset + count * 75 * 3 * 2 !== bytes.length) throw Error('Chuyển động chưa hợp lệ');
  let cursor = offset;
  const frames: Point[][] = Array.from({ length: count }, () => Array.from({ length: 75 }, () => {
    const p = [data.getInt16(cursor, true), data.getInt16(cursor + 2, true), data.getInt16(cursor + 4, true)].map(n => n / header.scale) as Point;
    cursor += 6; return p;
  }));
  return { ...header, frames } as Motion;
}
