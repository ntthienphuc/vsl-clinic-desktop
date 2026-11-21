import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import ts from 'typescript';
import * as THREE from 'three';
import { avatarRig } from './avatar_rig.mjs';

const root = path.resolve(import.meta.dirname, '..');
const output = path.join(root, 'build', 'audit-modules');
await fs.mkdir(output, { recursive: true });
for (const name of ['motion', 'kinematics', 'retarget', 'curatedHands', 'packedMotion', 'contact']) {
  let source = await fs.readFile(path.join(root, 'src/avatar', `${name}.ts`), 'utf8');
  source = source.replace("import curation from '../../assets/motions/hand-curation.json';", 'const curation = ' + await fs.readFile(path.join(root, 'assets/motions/hand-curation.json'), 'utf8') + ';');
  const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } });
  await fs.writeFile(path.join(output, `${name}.mjs`), compiled.outputText.replace("'./kinematics'", "'./kinematics.mjs'"));
}
const { HumanoidRetargeter } = await import(pathToFileURL(path.join(output, 'retarget.mjs')));
const { samplePlaylist, sampleMotion, neutralPose } = await import(pathToFileURL(path.join(output, 'motion.mjs')));
const { RULES } = await import(pathToFileURL(path.join(output, 'kinematics.mjs')));
const { curateHands } = await import(pathToFileURL(path.join(output, 'curatedHands.mjs')));
const { decodePackedMotion } = await import(pathToFileURL(path.join(output, 'packedMotion.mjs')));
const { handContact } = await import(pathToFileURL(path.join(output, 'contact.mjs')));
const avatarBytes = await fs.readFile(path.join(root, 'assets/avatar/ClinicMale.vrm'));
function stats(values) {
  const sorted = [...values].sort((a, b) => a - b);
  return { median: sorted[Math.floor(sorted.length * .5)] ?? 0, p95: sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * .95))] ?? 0, max: sorted.at(-1) ?? 0 };
}

const manifest = JSON.parse(await fs.readFile(path.join(root, 'assets/motions/manifest.json'), 'utf8'));
const fixtures = JSON.parse(execFileSync(path.join(root, '.venv/Scripts/python.exe'), ['-X', 'utf8', 'tools/playback_fixtures.py'], { cwd: root, encoding: 'utf8' }));
const allMotions = new Map(await Promise.all(manifest.entries.map(async entry => {
  const bytes = await fs.readFile(path.join(root, entry.path));
  const motion = entry.path.endsWith('.vslm') ? decodePackedMotion(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)) : JSON.parse(bytes);
  return [entry.id, curateHands(motion)];
})));
const cases = [...manifest.entries, ...fixtures.sentences.map((playback, index) => ({ id: `sentence-${index}`, label: playback.text, playback }))];
const rows = [];
let failures = 0;
for (const entry of cases) {
  const bytes = entry.playback ? Buffer.from(JSON.stringify(entry.playback)) : await fs.readFile(path.join(root, 'assets/motions', `${entry.id}.json`));
  const motion = entry.playback ? { id: entry.id, label: entry.label, medoid_id: null } : JSON.parse(bytes);
  const avatar = avatarRig(avatarBytes);
  const retargeter = new HumanoidRetargeter(avatar);
  for (let warmup = 0; warmup < 20; warmup += 1) {
    retargeter.apply(neutralPose(), 1 / 30, warmup / 30);
  }
  const playback = entry.playback ?? fixtures.single[entry.id];
  const motions = allMotions;
  const fingerCorrections = [];
  const contactErrors = [];
  const stableContactErrors = [];
  const wristCorrections = [];
  const wristSpeeds = [];
  const wristAccelerations = [];
  const elbowAngles = [];
  const nearHead = [];
  const nearHands = [];
  const angularSpeeds = { arms: [], wrists: [], fingers: [] };
  const boneNames = Object.keys(avatar.humanoid.humanBones);
  const previousRotations = new Map();
  let angularDiscontinuities = 0;
  const discontinuities = [];
  let previousWrists;
  let previousVelocity;
  let reachError = 0;
  let worst = { correction: 0, time_ms: 0 };
  let sampleCount = 0;
  for (let elapsed = 0; elapsed < playback.total_ms; elapsed += 1000 / 30) {
    const sample = samplePlaylist(playback, motions, 1000 + elapsed);
    const contact = handContact(sample.motionId, sample.sourceFraction);
    const diagnostic = structuredClone(retargeter.apply(sample.pose, 1 / 30, elapsed / 1000, 0, contact));
    const positions = diagnostic.wristPositions;
    if (diagnostic.contactTarget) contactErrors.push(diagnostic.contactErrorM);
    if (contact?.weight >= .99) stableContactErrors.push(diagnostic.contactErrorM);
    for (const name of boneNames) {
      const node = avatar.humanoid.getNormalizedBoneNode(name);
      if (!node || ![...node.position.toArray(), ...node.quaternion.toArray()].every(Number.isFinite)) {
        failures += 1;
        continue;
      }
      const previous = previousRotations.get(name);
      if (previous) {
        const angle = previous.angleTo(node.quaternion);
        const group = /UpperArm|LowerArm/.test(name) ? 'arms' : /Hand$/.test(name) ? 'wrists' : /Thumb|Index|Middle|Ring|Little/.test(name) ? 'fingers' : null;
        if (group) {
          angularSpeeds[group].push(angle * 30);
          if (angle > Math.PI / 2) {
            angularDiscontinuities += 1;
            discontinuities.push({ bone: name, elapsed_ms: elapsed, degrees: THREE.MathUtils.radToDeg(angle) });
          }
        }
      }
      previousRotations.set(name, node.quaternion.clone());
    }
    if (!positions.every(Number.isFinite)) {
      failures += 1;
    }
    for (const hand of diagnostic.jointAngles) {
      for (const angles of hand.slice(1)) {
        for (const [index, limit] of [RULES.mcpSpread, RULES.mcpFlex, RULES.pipFlex, RULES.dipFlex].entries()) {
          if (angles[index] < limit[0] - 1e-5 || angles[index] > limit[1] + 1e-5) {
            failures += 1;
          }
        }
      }
    }
    elbowAngles.push(...diagnostic.elbowFlexDegrees);
    reachError = Math.max(reachError, diagnostic.currentReachError);
    fingerCorrections.push(...diagnostic.fingerCorrectionDegrees);
    wristCorrections.push(...diagnostic.wristCorrectionDegrees);
    const correction = Math.max(...diagnostic.fingerCorrectionDegrees);
    if (correction > worst.correction) {
      worst = { correction, time_ms: Math.round(elapsed - 350) };
    }
    if (previousWrists) {
      const velocity = positions.map((value, index) => (value - previousWrists[index]) * 30);
      wristSpeeds.push(Math.hypot(...velocity.slice(0, 3)), Math.hypot(...velocity.slice(3)));
      if (previousVelocity) {
        const acceleration = velocity.map((value, index) => (value - previousVelocity[index]) * 30);
        wristAccelerations.push(Math.hypot(...acceleration.slice(0, 3)), Math.hypot(...acceleration.slice(3)));
      }
      previousVelocity = velocity;
    }
    previousWrists = positions;
    const head = avatar.humanoid.getNormalizedBoneNode('head').getWorldPosition(new THREE.Vector3());
    const left = new THREE.Vector3(...positions.slice(0, 3));
    const right = new THREE.Vector3(...positions.slice(3));
    if (Math.min(left.distanceTo(head), right.distanceTo(head)) < .16) {
      nearHead.push(Math.round(elapsed - 350));
    }
    if (left.distanceTo(right) < .10) {
      nearHands.push(Math.round(elapsed - 350));
    }
    sampleCount += 1;
  }
  const report = {
    id: motion.id, label: motion.label, input_sha256: crypto.createHash('sha256').update(bytes).digest('hex'), medoid_id: motion.medoid_id,
    samples: sampleCount, reach_error_m: reachError,
    contact_error_m: stats(contactErrors), stable_contact_error_m: stats(stableContactErrors), stable_contact_samples: stableContactErrors.length, runtime_sha256: entry.sha256 ?? null,
    elbow_flex_deg: { min: Math.min(...elbowAngles), max: Math.max(...elbowAngles) },
    mean_finger_correction_deg_per_hand: stats(fingerCorrections), wrist_correction_deg: stats(wristCorrections),
    wrist_speed_m_s: stats(wristSpeeds), wrist_acceleration_m_s2: stats(wristAccelerations),
    local_bone_angular_speed_rad_s: Object.fromEntries(Object.entries(angularSpeeds).map(([group, values]) => [group, stats(values)])),
    frame_turns_over_90_degrees: angularDiscontinuities,
    discontinuities,
    worst_finger_correction: worst, head_proximity_frames: nearHead.length, hand_proximity_frames: nearHands.length,
    review_required: ['Fluent VSL intelligibility and nonmanual cues', ...(stats(fingerCorrections).p95 > 25 ? ['Large finger correction: compare medoid and consensus'] : []), ...(angularDiscontinuities ? ['Joint turn exceeds 90 degrees in one frame'] : []), ...(nearHead.length ? ['Hand/head contact'] : []), ...(nearHands.length ? ['Two-hand contact'] : [])],
  };
  failures += angularDiscontinuities;
  rows.push(report);
  console.log(`${motion.label}: finger p95=${report.mean_finger_correction_deg_per_hand.p95.toFixed(1)}deg wrist p95=${report.wrist_correction_deg.p95.toFixed(1)}deg reach=${(reachError * 1000).toFixed(3)}mm`);
}
// The per-clip audit above resets the rig. Also reuse one rig through the whole
// bank to expose history-dependent roll drift that isolated clips cannot catch.
const sequenceAvatar = avatarRig(avatarBytes), sequenceRig = new HumanoidRetargeter(sequenceAvatar);
const armNames = ['leftUpperArm', 'leftLowerArm', 'rightUpperArm', 'rightLowerArm'];
const settle = () => { for (let i = 0; i < 90; i++) sequenceRig.apply(neutralPose(), 1 / 30, 0); };
settle();
const neutralRotations = armNames.map(name => sequenceAvatar.humanoid.getNormalizedBoneNode(name).quaternion.clone());
const sequenceDrifts = [];
for (const entry of manifest.entries) {
  const motion = allMotions.get(entry.id);
  for (let i = 0; i < 24; i++) sequenceRig.apply(sampleMotion(motion, motion.duration_ms * i / 23), 1 / 30, 0, 0, handContact(entry.id, i / 23));
  settle();
  const degrees = armNames.map((name, i) => THREE.MathUtils.radToDeg(neutralRotations[i].angleTo(sequenceAvatar.humanoid.getNormalizedBoneNode(name).quaternion)));
  sequenceDrifts.push({ id: entry.id, max_neutral_drift_degrees: Math.max(...degrees) });
}
const sequence = { method: 'One persistent actual rig; 24 sampled poses per word, with contact correction, then 90 neutral settling frames at a fixed breathing phase. This checks accumulated roll, not realtime visual smoothness.', words: sequenceDrifts, max_neutral_drift_degrees: Math.max(...sequenceDrifts.map(row => row.max_neutral_drift_degrees)) };
if (sequence.max_neutral_drift_degrees > .001) failures++;
const report = {
  schema: 'clinic-motion-audit-v1', created_at: new Date().toISOString(), rules: RULES,
  method: 'Actual VRM bone hierarchy + normalized humanoid, 30 Hz full clips including neutral transitions. Texture/skin collisions are not certified by this numerical check.',
  avatar_sha256: crypto.createHash('sha256').update(avatarBytes).digest('hex'), failures, words: rows, sequence,
  code_sha256: Object.fromEntries(await Promise.all(['motion', 'kinematics', 'retarget'].map(async (name) => [name, crypto.createHash('sha256').update(await fs.readFile(path.join(root, 'src/avatar', `${name}.ts`))).digest('hex')]))),
};
await fs.mkdir(path.join(root, 'docs/evidence'), { recursive: true });
const reportPath = process.argv.find(value => value.startsWith('--output='))?.slice(9)
  ?? path.join(root, 'docs/evidence/motion-audit.json');
await fs.mkdir(path.dirname(reportPath), { recursive: true });
await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
if (failures) {
  process.exitCode = 1;
}
