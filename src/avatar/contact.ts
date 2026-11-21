import { MathUtils } from 'three';

export interface HandContact {
  point: 'palm' | 'pairTip' | 'indexTip' | 'indexMiddle';
  target: 'abdomen' | 'leftPalm' | 'leftThumb' | 'leftIndex' | 'forehead' | 'foreheadCross' | 'rightCheek';
  weight: number;
}

const CONTACTS: Record<string, [HandContact['point'], HandContact['target'], number, number]> = {
  'qipedc-W00362': ['palm', 'abdomen', .22, .80],
  '391': ['pairTip', 'leftPalm', .25, .71],
  '285': ['palm', 'leftThumb', .23, .78],
  'qipedc-W03008': ['palm', 'forehead', .36, .59],
  '11': ['indexMiddle', 'foreheadCross', .25, .74],
  '201': ['palm', 'rightCheek', .35, .64],
};

/** Explicit source-observed contacts. Their blend follows source time rather
 * than wall time so pause, slow playback and scrubbing retain the same pose. */
export function handContact(id: string, fraction: number): HandContact | undefined {
  const row = CONTACTS[id]; if (!row) return;
  const weight = MathUtils.smoothstep(fraction, row[2] - .12, row[2]) * (1 - MathUtils.smoothstep(fraction, row[3], row[3] + .12));
  return weight > 0 ? { point: row[0], target: row[1], weight } : undefined;
}
