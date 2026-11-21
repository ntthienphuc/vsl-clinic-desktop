import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
import { execFileSync } from 'node:child_process';
import ts from 'typescript';
import * as THREE from 'three';
import { avatarRig } from '../tools/avatar_rig.mjs';

const root = path.resolve(import.meta.dirname, '..');
const output = path.join(root, 'build', 'test-modules');
await fs.mkdir(output, { recursive: true });
for (const name of ['motion', 'kinematics', 'retarget', 'contact', 'curatedHands']) {
  let source = await fs.readFile(path.join(root, 'src', 'avatar', `${name}.ts`), 'utf8');
  source = source.replace("import curation from '../../assets/motions/hand-curation.json';", 'const curation = ' + await fs.readFile(path.join(root, 'assets/motions/hand-curation.json'), 'utf8') + ';');
  const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } });
  await fs.writeFile(path.join(output, `${name}.mjs`), compiled.outputText.replace("'./kinematics'", "'./kinematics.mjs'"));
}
const { solveArm, transportAim, HumanoidRetargeter } = await import(pathToFileURL(path.join(output, 'retarget.mjs')));
const { HandArticulation, RULES, constrainWrist, RotationFollower, WristFollower } = await import(pathToFileURL(path.join(output, 'kinematics.mjs')));
const { samplePlaylist, sampleMotion, neutralPose, elapsedPlayback, transitionPose } = await import(pathToFileURL(path.join(output, 'motion.mjs')));
const { handContact } = await import(pathToFileURL(path.join(output, 'contact.mjs')));
const { curateHands } = await import(pathToFileURL(path.join(output, 'curatedHands.mjs')));

test('reviewed weekday counts retain extended digits while other fingers fold, with provenance lock', async () => {
  for (const [id, offset, extended] of [['320', 33, 2], ['318', 54, 3], ['323', 54, 4]]) {
    const raw = JSON.parse(await fs.readFile(path.join(root, 'assets/motions', id + '.json'), 'utf8'));
    const before = JSON.stringify(raw), corrected = curateHands(raw);
    assert.equal(JSON.stringify(raw), before, 'source coordinates must remain unchanged');
    const frame = corrected.frames[Math.floor(corrected.frames.length / 2)];
    assert.deepEqual(frame[offset], raw.frames[Math.floor(raw.frames.length / 2)][offset], 'wrist path retained');
    for (let finger = 0; finger < 4; finger++) {
      const base = offset + 5 + 4 * finger;
      const p = i => new THREE.Vector3(...frame[i]);
      const bend = THREE.MathUtils.radToDeg(p(base + 1).sub(p(base)).angleTo(p(base + 2).sub(p(base + 1))));
      assert.ok(finger < extended ? bend < 10 : bend > 65, `${id}: digit ${finger} bend ${bend}`);
    }
    const changedSource = { ...raw, source_hashes: ['unreviewed-source'] };
    assert.equal(curateHands(changedSource), changedSource, 'unreviewed variants must not inherit this correction');
  }
});

test('source-reviewed face contacts stay aligned and preserve the crossed indices', async () => {
  for (const id of ['11', 'qipedc-W03008', '201']) {
    const avatar = avatarRig(await fs.readFile(path.join(root, 'assets/avatar/ClinicMale.vrm')));
    const retargeter = new HumanoidRetargeter(avatar);
    const motion = curateHands(JSON.parse(await fs.readFile(path.join(root, 'assets/motions', id + '.json'), 'utf8')));
    const contact = handContact(id, .5), pose = sampleMotion(motion, motion.duration_ms * .5);
    for (let i = 0; i < 90; i++) retargeter.apply(neutralPose(), 1 / 30, 0);
    let diagnostic;
    for (let i = 0; i < 90; i++) diagnostic = retargeter.apply(pose, 1 / 30, 0, 0, contact);
    assert.ok(diagnostic.contactErrorM < .002, `${id}: stable contact misses target`);
    const p = name => avatar.humanoid.getNormalizedBoneNode(name).getWorldPosition(new THREE.Vector3());
    const eyes = p('leftEye').add(p('rightEye')).multiplyScalar(.5);
    if (id === '11') {
      const left = p('leftIndexIntermediate'), right = p('rightIndexIntermediate');
      assert.ok(left.y > eyes.y + .025 && right.y > eyes.y + .025);
      assert.ok(left.z > eyes.z + .08 && right.z > left.z + .008, 'indices must be in front of the visible forehead surface');
      assert.ok(left.distanceTo(right) < .02, 'middle phalanges must meet at the crossing');
      const angle = THREE.MathUtils.radToDeg(p('leftIndexDistal').sub(left).angleTo(p('rightIndexDistal').sub(right)));
      assert.ok(angle > 60 && angle < 120, `indices do not form a cross: ${angle}`);
    } else if (id === '201') {
      const palm = p('rightHand').lerp(p('rightMiddleProximal'), .68);
      assert.ok(palm.x < eyes.x - .08 && palm.x > eyes.x - .13, 'mother palm belongs beside the right cheek');
      assert.ok(palm.y < eyes.y - .05 && palm.y > eyes.y - .10, 'mother palm must be lower than the eyes');
      assert.ok(palm.z > eyes.z + .04 && palm.z < eyes.z + .09, 'cheek contact must not float in the frontal signing space');
    } else {
      const palm = p('rightHand').lerp(p('rightMiddleProximal'), .68);
      assert.ok(palm.y > eyes.y + .025 && palm.z > eyes.z + .08, 'fever palm must be above the eyes and clear of the face');
    }
  }
});

test('bridges preserve endpoint velocity when feasible and bound conflicting contact trajectories', () => {
  const a = [[0, 1, -.5]], b = [[1, -1, -.5]];
  const va = [[.001, -.001, 0]], vb = [[.0015, -.002, 0]];
  const duration = 500, epsilon = 1e-5;
  const first = transitionPose(a, b, va, vb, duration, epsilon)[0];
  const last = transitionPose(a, b, va, vb, duration, 1 - epsilon)[0];
  for (let axis = 0; axis < 3; axis++) {
    assert.ok(Math.abs((first[axis] - a[0][axis]) / (duration * epsilon) - va[0][axis]) < 1e-6);
    assert.ok(Math.abs((b[0][axis] - last[axis]) / (duration * epsilon) - vb[0][axis]) < 1e-6);
  }
  for (const [start, end] of [[va, vb], [[[200, 99, 999]], [[-99, -200, -999]]]]) {
    for (let tick = 0; tick <= 100; tick++) {
      const point = transitionPose(a, b, start, end, duration, tick / 100)[0];
      assert.ok(point.every((value, axis) => Number.isFinite(value) && value >= Math.min(a[0][axis], b[0][axis]) - 1e-9 && value <= Math.max(a[0][axis], b[0][axis]) + 1e-9));
    }
  }
});

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

test('successive signs return to the same arm roll and never twist the elbow hinge', async () => {
  const avatar = avatarRig(await fs.readFile(path.join(root, 'assets/avatar/ClinicMale.vrm')));
  const retargeter = new HumanoidRetargeter(avatar);
  const arms = ['leftUpperArm', 'leftLowerArm', 'rightUpperArm', 'rightLowerArm'];
  const hingeRest = ['left', 'right'].map(side => {
    const upper = avatar.humanoid.getNormalizedBoneNode(side + 'UpperArm');
    const lower = avatar.humanoid.getNormalizedBoneNode(side + 'LowerArm');
    const hand = avatar.humanoid.getNormalizedBoneNode(side + 'Hand');
    const upperRotation = upper.getWorldQuaternion(new THREE.Quaternion()), lowerRotation = lower.getWorldQuaternion(new THREE.Quaternion());
    return { upperRotation, lowerRotation, axis: hand.getWorldPosition(new THREE.Vector3()).sub(lower.getWorldPosition(new THREE.Vector3())).normalize().applyQuaternion(lowerRotation.clone().invert()) };
  });
  const neutral = neutralPose();
  const settle = () => { for (let i = 0; i < 90; i++) retargeter.apply(neutral, 1 / 30, 0); };
  settle();
  const original = arms.map(name => avatar.humanoid.getNormalizedBoneNode(name).quaternion.clone());
  const originalWrists = ['leftHand', 'rightHand'].map(name => avatar.humanoid.getNormalizedBoneNode(name).getWorldPosition(new THREE.Vector3()));
  const motions = await Promise.all(['qipedc-W00362', 'qipedc-W03008', 'qipedc-W01227', 'qipedc-W01298', '11', '368', '32', '145', '379'].map(async id => JSON.parse(await fs.readFile(path.join(root, 'assets/motions', id + '.json'), 'utf8'))));
  for (let pass = 0; pass < 3; pass++) {
    for (const motion of motions) for (let i = 0; i < 36; i++) {
      retargeter.apply(sampleMotion(motion, motion.duration_ms * i / 35), 1 / 30, 0);
      for (const [index, side] of ['left', 'right'].entries()) {
        const reference = hingeRest[index];
        const upper = avatar.humanoid.getNormalizedBoneNode(side + 'UpperArm');
        const elbow = avatar.humanoid.getNormalizedBoneNode(side + 'LowerArm');
        const inherited = upper.getWorldQuaternion(new THREE.Quaternion()).multiply(reference.upperRotation.clone().invert()).multiply(reference.lowerRotation);
        const relative = inherited.invert().multiply(elbow.getWorldQuaternion(new THREE.Quaternion()));
        const twist = new THREE.Vector3(relative.x, relative.y, relative.z).dot(reference.axis);
        assert.ok(Math.abs(twist) < 1e-6, `${side}: elbow adds axial twist ${twist}`);
      }
    }
    settle();
    arms.forEach((name, i) => assert.ok(original[i].angleTo(avatar.humanoid.getNormalizedBoneNode(name).quaternion) < 1e-5, `${name} accumulated twist after sequence ${pass}`));
    ['leftHand', 'rightHand'].forEach((name, i) => assert.ok(originalWrists[i].distanceTo(avatar.humanoid.getNormalizedBoneNode(name).getWorldPosition(new THREE.Vector3())) < 1e-6));
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

test('moving forearms retain bounded wrist swing without snapping at the flexion seam', () => {
  for (const dt of [1 / 30, 1 / 60, 1 / 120]) {
    const follower = new WristFollower();
    let previous;
    for (let tick = 0; tick < 12 / dt; tick++) {
      const time = tick * dt;
      const forearm = new THREE.Vector3(.3 * Math.sin(time * 3), Math.cos(time * 4), Math.sin(time * 4)).normalize();
      const target = new THREE.Quaternion().setFromEuler(new THREE.Euler(time * .7, time * .2, Math.sin(time)));
      const { frame } = follower.step(target, forearm, dt);
      const local = forearm.clone().applyQuaternion(frame.clone().invert());
      const flex = THREE.MathUtils.radToDeg(Math.atan2(local.z, local.y));
      const deviation = THREE.MathUtils.radToDeg(Math.atan2(local.x, Math.hypot(local.y, local.z)));
      assert.ok(Math.abs(flex) <= 80 + 1e-6 && Math.abs(deviation) <= 35 + 1e-6);
      assert.ok(frame.toArray().every(Number.isFinite));
      if (previous) assert.ok(previous.angleTo(frame) < 20 * dt, `Wrist jump at ${time}s (${dt}s/frame)`);
      previous = frame;
    }
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
