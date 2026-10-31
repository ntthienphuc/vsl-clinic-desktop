import * as THREE from 'three';
import { VRM, VRMExpression, VRMExpressionMorphTargetBind } from '@pixiv/three-vrm';
import type { Playback } from '../types';
import { elapsedPlayback, INTRO_MS, OUTRO_MS } from './motion';

/** A dedicated brow channel avoids the surprised preset's open mouth. */
export function installQuestionExpression(vrm: VRM): void {
  const expression = new VRMExpression('clinicQuestion');
  vrm.scene.traverse((object) => {
    if (!(object instanceof THREE.Mesh) || !object.morphTargetDictionary) {
      return;
    }
    for (const [name, index] of Object.entries(object.morphTargetDictionary)) {
      if (name.endsWith('Fcl_BRW_Surprised')) {
        expression.addBind(new VRMExpressionMorphTargetBind({ primitives: [object], index, weight: 0.65 }));
      }
    }
  });
  if (!expression.binds.length) {
    throw new Error('Avatar chưa có chuyển động chân mày để thể hiện câu hỏi.');
  }
  vrm.expressionManager?.registerExpression(expression);
}

export function questionWeight(playback: Playback | null, now = Date.now()): number {
  if (!playback || !['playing', 'paused'].includes(playback.status)) {
    return 0;
  }
  const elapsed = elapsedPlayback(playback, now);
  const clause = playback.clauses.find((item) => elapsed >= item.start_ms! && elapsed < item.end_ms!);
  if (!clause || clause.nonmanual !== 'question') {
    return 0;
  }
  const fade = Math.min((elapsed - clause.start_ms!) / INTRO_MS, (clause.end_ms! - elapsed) / OUTRO_MS);
  return THREE.MathUtils.smoothstep(fade, 0, 1);
}
