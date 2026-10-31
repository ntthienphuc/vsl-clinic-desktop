import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
import { execFileSync } from 'node:child_process';
import ts from 'typescript';
import * as THREE from 'three';

const root = path.resolve(import.meta.dirname, '..');
const output = path.join(root, 'build', 'test-modules');
await fs.mkdir(output, { recursive: true });
for (const name of ['motion', 'kinematics', 'retarget']) {
  const source = await fs.readFile(path.join(root, 'src', 'avatar', `${name}.ts`), 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } });
  await fs.writeFile(path.join(output, `${name}.mjs`), compiled.outputText.replace("'./kinematics'", "'./kinematics.mjs'"));
}
const { solveArm, transportAim } = await import(pathToFileURL(path.join(output, 'retarget.mjs')));
const { HandArticulation, RULES, constrainWrist, RotationFollower } = await import(pathToFileURL(path.join(output, 'kinematics.mjs')));
const { samplePlaylist, sampleMotion, neutralPose, elapsedPlayback } = await import(pathToFileURL(path.join(output, 'motion.mjs')));

test('arm frames cross the antipodal T-pose direction without a roll flip or endpoint drift', () => {
  const axis = new THREE.Vector3(1, 0, 0);
  let frame = new THREE.Quaternion();
  for (let index = 0; index <= 720; index += 1) {
    const angle = index * Math.PI / 180;
    const direction = new THREE.Vector3(Math.cos(angle), Math.sin(angle), .015 * Math.sin(angle * 3)).normalize();
    const next = transportAim(axis, frame, direction);
    assert.ok(axis.clone().applyQuaternion(next).distanceTo(direction) < 1e-8);
    assert.ok(frame.angleTo(next) < .025, `Arm roll discontinuity at ${index} degrees`);
    frame = next;
  }
});

test('cubic motion sampling preserves measured poses and never overshoots contact coordinates', () => {
  const values = [0, .05, 1, .9, -.1, -.1, .2];
  const motion = { duration_ms: 600, frames: values.map((value) => [[value, -value, value * .5]]) };
  for (let index = 0; index < values.length; index += 1) {
    const sampled = sampleMotion(motion, index * 100)[0];
    assert.ok(sampled.every((value, axis) => Math.abs(value - motion.frames[index][0][axis]) < 1e-12));
  }
  for (let time = 0; time <= 600; time += 1) {
    const index = Math.min(5, Math.floor(time / 100));
    const value = sampleMotion(motion, time)[0][0];
    assert.ok(value >= Math.min(values[index], values[index + 1]) - 1e-9);
    assert.ok(value <= Math.max(values[index], values[index + 1]) + 1e-9);
  }
});

test('two-bone IK keeps both lengths, finite even at singular/parallel targets', () => {
  const shoulder = new THREE.Vector3(0.15, 1.4, 0);
  const targets = [shoulder.clone(), new THREE.Vector3(0.15, 1.4, 0.2), new THREE.Vector3(0, 1.4, 1), new THREE.Vector3(-0.15, 1.1, .2)];
  for (const wrist of targets) {
    for (const pole of [shoulder, wrist, new THREE.Vector3(.4, 1.2, 0)]) {
      const solved = solveArm(shoulder, wrist, pole, .28, .24);
      assert.ok([...solved.elbow.toArray(), ...solved.wrist.toArray()].every(Number.isFinite));
      assert.ok(Math.abs(solved.elbow.distanceTo(shoulder) - .28) < 1e-8);
      assert.ok(Math.abs(solved.elbow.distanceTo(solved.wrist) - .24) < 1e-8);
      const flex = THREE.MathUtils.radToDeg(solved.elbow.clone().sub(shoulder).angleTo(solved.wrist.clone().sub(solved.elbow)));
      assert.ok(flex >= RULES.elbowFlex[0] - 1e-6 && flex <= RULES.elbowFlex[1] + 1e-6);
      if (shoulder.distanceTo(wrist) > .13 && shoulder.distanceTo(wrist) < .519) {
        assert.ok(solved.wrist.distanceTo(wrist) < 1e-8);
      }
    }
  }
});

test('palm-local hinge limits survive folds, mirrored hands, and adversarial point noise', () => {
  for (const [side, offset] of [['left', 33], ['right', 54]]) {
    const solver = new HandArticulation(side);
    const initial = neutralPose().slice(offset, offset + 21).map((p) => new THREE.Vector3(...p));
    for (let frame = 0; frame < 300; frame += 1) {
      const points = initial.map((p) => p.clone());
      for (const start of [5, 9, 13, 17]) {
        points[start + 1].add(new THREE.Vector3(Math.sin(frame) * .4, Math.cos(frame) * .3, .2));
        points[start + 2].add(new THREE.Vector3(-.3, .3, Math.sin(frame) * .5));
      }
      const hand = solver.solve(points, 1 / 30);
      assert.ok(hand.directions.flat().every((d) => d.toArray().every(Number.isFinite) && Math.abs(d.length() - 1) < 1e-6));
      for (const angles of hand.angles.slice(1)) {
        for (const [index, limit] of [RULES.mcpSpread, RULES.mcpFlex, RULES.pipFlex, RULES.dipFlex].entries()) {
          assert.ok(angles[index] >= limit[0] - 1e-6 && angles[index] <= limit[1] + 1e-6);
        }
      }
      for (const directions of hand.directions.slice(1)) {
        // All phalanges must lie in one plane, independently of source noise.
        assert.ok(Math.abs(directions[0].clone().cross(directions[1]).dot(directions[2])) < 1e-6);
      }
    }
  }
});

test('wrist swing bounds and shortest-arc palm speed limit', () => {
  const follower = new RotationFollower();
  const forearm = new THREE.Vector3(0, 1, 0);
  let previous;
  for (let frame = 0; frame < 180; frame += 1) {
    const target = new THREE.Quaternion().setFromEuler(new THREE.Euler(frame * .8, frame * .3, frame * .4));
    const bounded = constrainWrist(target, forearm).frame;
    const local = forearm.clone().applyQuaternion(bounded.clone().invert());
    const flex = THREE.MathUtils.radToDeg(Math.atan2(local.z, local.y));
    const deviation = THREE.MathUtils.radToDeg(Math.atan2(local.x, Math.hypot(local.y, local.z)));
    assert.ok(Math.abs(flex) <= 80 + 1e-6 && Math.abs(deviation) <= 35 + 1e-6);
    const next = follower.step(bounded, 1 / 30);
    if (previous) {
      assert.ok(previous.angleTo(next) <= RULES.palmSpeed / 30 + 1e-6);
    }
    previous = next.clone();
  }
});

test('every bank word and supported sentence uses a continuous server timeline and stable pause', async () => {
  const bank = JSON.parse(await fs.readFile(path.join(root, 'assets/motions/manifest.json'), 'utf8'));
  const motions = new Map();
  for (const entry of bank.entries) {
    const motion = JSON.parse(await fs.readFile(path.join(root, 'assets/motions', `${entry.id}.json`), 'utf8'));
    motions.set(entry.id, motion);
  }
  const fixtures = JSON.parse(execFileSync(path.join(root, '.venv/Scripts/python.exe'), ['-X', 'utf8', 'tools/playback_fixtures.py'], { cwd: root, encoding: 'utf8' }));
  for (const playback of [...Object.values(fixtures.single), ...fixtures.sentences]) {
  const total = playback.total_ms;
  let previous = neutralPose();
  for (let elapsed = 0; elapsed <= total; elapsed += 1000 / 30) {
    const sample = samplePlaylist(playback, motions, 1000 + elapsed);
    assert.equal(sample.pose.length, 75);
    assert.ok(sample.pose.flat().every(Number.isFinite));
    assert.ok(sample.progress >= 0 && sample.progress <= 1);
    // A coordinate discontinuity larger than two shoulder spans in 33 ms
    // would be visibly invalid regardless of the rig used to render it.
    const jump = Math.max(...sample.pose.map((point, index) => Math.hypot(...point.map((value, axis) => value - previous[index][axis]))));
    assert.ok(jump < 2, `discontinuity ${jump} at ${elapsed}`);
    previous = sample.pose;
  }
  assert.equal(samplePlaylist(playback, motions, 1000 + total).complete, true);
  const paused = { ...playback, status: 'paused', elapsed_ms: 700 };
  assert.deepEqual(samplePlaylist(paused, motions, 2000), samplePlaylist(paused, motions, 9000));
  assert.equal(elapsedPlayback({ ...playback, rate: .5 }, 2000), 500);
  for (const segment of playback.timeline.slice(1)) {
    const before = samplePlaylist(playback, motions, 1000 + segment.start_ms - .001).pose;
    const after = samplePlaylist(playback, motions, 1000 + segment.start_ms + .001).pose;
    assert.ok(Math.max(...after.map((p, i) => Math.hypot(...p.map((v, a) => v - before[i][a])))) < .01, playback.text);
  }
  }
});
