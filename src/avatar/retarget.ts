import * as THREE from 'three';
import { VRM, VRMHumanBoneName } from '@pixiv/three-vrm';
import type { Point } from '../types';
import { HandArticulation, WristFollower, constrainWrist, RULES } from './kinematics';
import type { HandContact } from './contact';

interface RestBone {
  node: THREE.Object3D;
  position: THREE.Vector3;
  quaternion: THREE.Quaternion;
}

function vector(point: Point): THREE.Vector3 {
  return new THREE.Vector3(...point);
}

function basis(across: THREE.Vector3, along: THREE.Vector3): THREE.Quaternion {
  const y = along.clone().normalize();
  const x = across.clone().addScaledVector(y, -across.dot(y)).normalize();
  if (x.lengthSq() < 1e-8 || y.lengthSq() < 1e-8) {
    return new THREE.Quaternion();
  }
  const z = new THREE.Vector3().crossVectors(x, y).normalize();
  return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z));
}

export function transportAim(localDirection: THREE.Vector3, previous: THREE.Quaternion, targetDirection: THREE.Vector3) {
  if (targetDirection.lengthSq() < 1e-9) {
    return previous.clone();
  }
  const from = localDirection.clone().applyQuaternion(previous).normalize();
  const correction = new THREE.Quaternion().setFromUnitVectors(from, targetDirection.clone().normalize());
  return correction.multiply(previous).normalize();
}

export function solveArm(shoulder: THREE.Vector3, wrist: THREE.Vector3, pole: THREE.Vector3, upperLength: number, lowerLength: number) {
  const direction = wrist.clone().sub(shoulder);
  const reachAt = (degrees: number) => Math.sqrt(upperLength ** 2 + lowerLength ** 2 + 2 * upperLength * lowerLength * Math.cos(THREE.MathUtils.degToRad(degrees)));
  const distance = THREE.MathUtils.clamp(direction.length(), reachAt(RULES.elbowFlex[1]), reachAt(RULES.elbowFlex[0]));
  if (direction.lengthSq() < 1e-12) {
    direction.set(0, -1, 0);
  }
  direction.normalize();
  const bend = pole.clone().sub(shoulder);
  bend.addScaledVector(direction, -bend.dot(direction));
  if (bend.lengthSq() < 1e-8) {
    bend.copy(Math.abs(direction.z) < 0.9 ? new THREE.Vector3(0, 0, 1) : new THREE.Vector3(1, 0, 0));
    bend.addScaledVector(direction, -bend.dot(direction));
  }
  bend.normalize();
  const along = (upperLength * upperLength - lowerLength * lowerLength + distance * distance) / (2 * distance);
  const height = Math.sqrt(Math.max(0, upperLength * upperLength - along * along));
  return {
    elbow: shoulder.clone().addScaledVector(direction, along).addScaledVector(bend, height),
    wrist: shoulder.clone().addScaledVector(direction, distance),
  };
}

export class HumanoidRetargeter {
  private rest = new Map<string, RestBone>();
  private span = 0.3;
  private hands = { left: new HandArticulation('left'), right: new HandArticulation('right') };
  private palms = { left: new WristFollower(), right: new WristFollower() };
  private poles = new Map<string, THREE.Vector3>();
  private wrists = new Map<string, THREE.Vector3>();
  private armFrames = new Map<string, THREE.Quaternion>();
  private armBindings = new Map<string, { axis: THREE.Vector3; reference: THREE.Quaternion; hanging: THREE.Vector3 }>();
  private contactError = 0;
  private palmFrames = new Map<string, THREE.Quaternion>();
  private diagnostics = { profile: RULES.profile, frames: 0, maximumReachError: 0, currentReachError: 0, bonesDriven: 0, shoulderSpan: 0, armLength: 0, fingerRotations: [] as number[], wristPositions: [] as number[], jointAngles: [] as number[][][], elbowFlexDegrees: [] as number[], fingerCorrectionDegrees: [] as number[], wristCorrectionDegrees: [] as number[], limitedFingerSegments: 0, maximumPalmSpeed: 0, degeneratePalms: 0, palmForward: [] as number[] };

  constructor(private vrm: VRM) {
    vrm.scene.updateMatrixWorld(true);
    for (const name of Object.values(VRMHumanBoneName)) {
      const node = vrm.humanoid.getNormalizedBoneNode(name);
      if (node) {
        this.rest.set(name, {
          node,
          position: node.getWorldPosition(new THREE.Vector3()),
          quaternion: node.getWorldQuaternion(new THREE.Quaternion()),
        });
      }
    }
    this.span = this.get('leftUpperArm').position.distanceTo(this.get('rightUpperArm').position);
    this.diagnostics.shoulderSpan = this.span;
    this.diagnostics.armLength = this.get('leftUpperArm').position.distanceTo(this.get('leftLowerArm').position) + this.get('leftLowerArm').position.distanceTo(this.get('leftHand').position);
    for (const side of ['left', 'right'] as const) {
      const hanging = new THREE.Vector3(side === 'left' ? .12 : -.12, -1, .04).normalize();
      for (const [name, child] of [[`${side}UpperArm`, `${side}LowerArm`], [`${side}LowerArm`, `${side}Hand`]]) {
        const rest = this.get(name);
        const axis = this.get(child).position.clone().sub(rest.position).normalize().applyQuaternion(rest.quaternion.clone().invert());
        const reference = name.endsWith('LowerArm')
          ? this.get(`${side}UpperArm`).quaternion.clone().invert().multiply(rest.quaternion)
          : transportAim(axis, rest.quaternion, hanging);
        this.armBindings.set(name, { axis, reference, hanging });
      }
    }
  }

  private get(name: string): RestBone {
    const bone = this.rest.get(name);
    if (!bone) {
      throw new Error(`Avatar thiếu xương ${name}`);
    }
    return bone;
  }

  private worldRotation(name: string, desired: THREE.Quaternion, alpha = 1) {
    const { node } = this.get(name);
    const parent = node.parent?.getWorldQuaternion(new THREE.Quaternion()) ?? new THREE.Quaternion();
    const local = parent.invert().multiply(desired);
    node.quaternion.slerp(local, alpha);
    node.updateMatrixWorld(true);
    this.diagnostics.bonesDriven += 1;
  }

  private aim(name: string, targetDirection: THREE.Vector3) {
    const binding = this.armBindings.get(name)!;
    const side = name.startsWith('left') ? 'left' : 'right';
    let reference: THREE.Quaternion;
    if (name.endsWith('LowerArm')) {
      // Elbow is a hinge: inherit the upper arm's roll, then bend toward the
      // solved wrist. Independently transporting both bones around successive
      // signs accumulates different roll (holonomy), twisting the sleeve shut
      // even after the hand has returned to the neutral position.
      const upper = this.get(`${side}UpperArm`);
      reference = upper.node.getWorldQuaternion(new THREE.Quaternion())
        .multiply(binding.reference);
    } else {
      // Anchor the swing at the hanging arm, inside the signing workspace.
      // Unlike the horizontal T-pose anchor this stays away from the opposite
      // direction when a hand crosses the chest, and unlike a previous-frame
      // anchor it returns to the same roll after a closed movement sequence.
      reference = binding.reference;
      // The exact overhead antipode has no unique swing axis. Only there use
      // the preceding frame; normal signing and neutral poses remain absolute.
      if (binding.hanging.dot(targetDirection.clone().normalize()) < -.98) {
        reference = this.armFrames.get(name) ?? reference;
      }
    }
    const desired = transportAim(binding.axis, reference, targetDirection);
    this.armFrames.set(name, desired.clone());
    this.worldRotation(name, desired);
  }

  private landmark(side: 'left' | 'right', name: 'palm' | 'indexTip' | 'pairTip' | 'thumbTip' | 'indexMiddle') {
    const position = (bone: string) => this.get(side + bone).node.getWorldPosition(new THREE.Vector3());
    const tip = (finger: 'Index' | 'Middle' | 'Thumb') => {
      const distal = this.get(side + finger + 'Distal'), previous = this.get(side + finger + (finger === 'Thumb' ? 'Proximal' : 'Intermediate'));
      const restTip = distal.position.clone().sub(previous.position).multiplyScalar(.7).applyQuaternion(distal.quaternion.clone().invert());
      return distal.node.localToWorld(restTip);
    };
    if (name === 'indexTip') return tip('Index');
    if (name === 'indexMiddle') return position('IndexIntermediate');
    if (name === 'thumbTip') return tip('Thumb');
    if (name === 'pairTip') return tip('Index').add(tip('Middle')).multiplyScalar(.5);
    return position('Hand').lerp(position('MiddleProximal'), .68);
  }

  private refineContact(contact: HandContact, dt: number, previous: { left?: THREE.Vector3; right?: THREE.Vector3 }) {
    const worldPosition = (bone: RestBone) => bone.node.getWorldPosition(new THREE.Vector3());
    const source = this.landmark('right', contact.point);
    let target = contact.target === 'leftThumb' ? this.landmark('left', 'thumbTip')
      : contact.target === 'leftIndex' ? this.get('leftIndexIntermediate').node.getWorldPosition(new THREE.Vector3())
      : this.landmark('left', 'palm');
    if (contact.target === 'abdomen') {
      const center = worldPosition(this.get('leftUpperArm')).add(worldPosition(this.get('rightUpperArm'))).multiplyScalar(.5);
      target = source.clone(); target.z = center.z + this.span * .55;
    }
    if (contact.target === 'forehead' || contact.target === 'foreheadCross') {
      // Eye bones sit inside the face. The reviewed ClinicMale forehead mesh is
      // ~0.115 m forward; this anchor includes the palm/finger surface thickness.
      const head = this.get('head');
      const rotation = head.node.getWorldQuaternion(new THREE.Quaternion()).multiply(head.quaternion.clone().invert());
      const forehead = worldPosition(this.get('leftEye')).add(worldPosition(this.get('rightEye'))).multiplyScalar(.5)
        .add(new THREE.Vector3(0, this.span * .15, this.span * .34).applyQuaternion(rotation));
      if (contact.target === 'foreheadCross') {
        // Fit the horizontal index first, then cross its middle phalanx with
        // the vertical index. Fingertip-to-middle contact creates a T instead.
        this.fitHandContact('left', 'indexMiddle', forehead, contact.weight, dt, previous.left);
        target = this.landmark('left', 'indexMiddle').add(new THREE.Vector3(0, 0, this.span * .05).applyQuaternion(rotation));
      } else target = forehead.add(new THREE.Vector3(-this.span * .07, 0, 0).applyQuaternion(rotation));
    }
    if (contact.target === 'rightCheek') {
      const head = this.get('head');
      const rotation = head.node.getWorldQuaternion(new THREE.Quaternion()).multiply(head.quaternion.clone().invert());
      target = worldPosition(this.get('leftEye')).add(worldPosition(this.get('rightEye'))).multiplyScalar(.5)
        .add(new THREE.Vector3(-this.span * .34, -this.span * .26, this.span * .21).applyQuaternion(rotation));
    }
    this.fitHandContact('right', contact.point, target, contact.weight, dt, previous.right);
  }

  private fitHandContact(side: 'left' | 'right', point: HandContact['point'], target: THREE.Vector3, weight: number, dt: number, previous?: THREE.Vector3) {
    const upper = this.get(side + 'UpperArm'), lower = this.get(side + 'LowerArm'), wrist = this.get(side + 'Hand');
    const worldPosition = (bone: RestBone) => bone.node.getWorldPosition(new THREE.Vector3());
    const source = this.landmark(side, point);
    const handBones = [...this.rest.keys()].filter(name => name.startsWith(side) && /Hand|Thumb|Index|Middle|Ring|Little/.test(name));
    const rotations = handBones.map(name => [name, this.get(name).node.getWorldQuaternion(new THREE.Quaternion())] as const);
    const frame = this.palmFrames.get(side)!;
    const shoulder = worldPosition(upper);
    // Blend once from the unconstrained pose. Re-applying a fractional weight
    // inside the iterations would silently pull a fading contact to full strength.
    const desired = source.clone().lerp(target, weight);
    let forearm = worldPosition(wrist).sub(worldPosition(lower)).normalize();
    for (let iteration = 0; iteration < 5; iteration++) {
      const error = desired.clone().sub(this.landmark(side, point));
      if (error.lengthSq() < .000001) break;
      const proposed = worldPosition(wrist).add(error.clampLength(0, this.span * .45));
      // Contact is part of the same movement, so it must not bypass the wrist
      // speed limit already applied to the unconstrained source trajectory.
      if (previous) proposed.sub(previous).clampLength(0, 3 * dt).add(previous);
      const solved = solveArm(shoulder, proposed, worldPosition(lower), upper.position.distanceTo(lower.position), lower.position.distanceTo(wrist.position));
      this.aim(side + 'UpperArm', solved.elbow.clone().sub(shoulder));
      this.aim(side + 'LowerArm', solved.wrist.clone().sub(worldPosition(lower)));
      forearm = worldPosition(wrist).sub(worldPosition(lower)).normalize();
      const bounded = constrainWrist(frame, forearm);
      const correction = bounded.frame.clone().multiply(frame.clone().invert());
      for (const [name, rotation] of rotations) this.worldRotation(name, correction.clone().multiply(rotation));
      this.palmFrames.set(side, bounded.frame);
      const index = side === 'left' ? 0 : 1;
      this.diagnostics.wristCorrectionDegrees[index] = Math.max(this.diagnostics.wristCorrectionDegrees[index] ?? 0, bounded.correctionDegrees);
      this.diagnostics.currentReachError = Math.max(this.diagnostics.currentReachError, worldPosition(wrist).distanceTo(solved.wrist));
    }
    this.diagnostics.elbowFlexDegrees[side === 'left' ? 0 : 1] = THREE.MathUtils.radToDeg(worldPosition(lower).sub(shoulder).angleTo(forearm));
    this.wrists.set(side, worldPosition(wrist));
    this.contactError = Math.max(this.contactError, this.landmark(side, point).distanceTo(target));
  }

  apply(points: Point[], deltaSeconds: number, seconds: number, question = 0, contact?: HandContact) {
    const dt = THREE.MathUtils.clamp(deltaSeconds, 1 / 240, 0.1);
    const previousContactWrists = contact ? { left: this.wrists.get('left')?.clone(), right: this.wrists.get('right')?.clone() } : {};
    const alpha = 1 - Math.exp(-dt * 35);
    this.diagnostics.bonesDriven = 0;
    this.diagnostics.currentReachError = 0;
    this.diagnostics.jointAngles = [];
    this.diagnostics.elbowFlexDegrees = [];
    this.diagnostics.fingerCorrectionDegrees = [];
    this.diagnostics.wristCorrectionDegrees = [];
    this.diagnostics.palmForward = [];
    this.diagnostics.limitedFingerSegments = 0;
    const chest = this.rest.get('upperChest') ?? this.rest.get('chest');
    if (chest) {
      const shoulderLine = vector(points[11]).sub(vector(points[12]));
      const lean = THREE.MathUtils.clamp(Math.atan2(shoulderLine.y, shoulderLine.x), -0.12, 0.12);
      const breathing = Math.sin(seconds * 1.7) * 0.004;
      chest.node.quaternion.slerp(new THREE.Quaternion().setFromEuler(new THREE.Euler(breathing, 0, lean * 0.35)), alpha);
      chest.node.updateMatrixWorld(true);
    }
    const head = this.get('head');
    const headTurn = THREE.MathUtils.clamp(points[0][0] * 0.28, -0.16, 0.16);
    head.node.quaternion.slerp(new THREE.Quaternion().setFromEuler(new THREE.Euler(-0.065 * question, headTurn, 0)), alpha);
    head.node.updateMatrixWorld(true);

    const leftShoulder = this.get('leftUpperArm').node.getWorldPosition(new THREE.Vector3());
    const rightShoulder = this.get('rightUpperArm').node.getWorldPosition(new THREE.Vector3());
    const center = leftShoulder.clone().add(rightShoulder).multiplyScalar(0.5);
    const leftEye = this.rest.get('leftEye');
    const rightEye = this.rest.get('rightEye');
    const avatarNose = leftEye && rightEye
      ? leftEye.node.getWorldPosition(new THREE.Vector3()).add(rightEye.node.getWorldPosition(new THREE.Vector3())).multiplyScalar(0.5).add(new THREE.Vector3(0, -this.span * .13, this.span * .10))
      : head.node.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, this.span * .25, this.span * .35));
    const sourceNose = vector(points[0]).multiplyScalar(this.span).add(center);
    const faceOffset = avatarNose.clone().sub(sourceNose);
    const faceWeights = [15, 16].map((joint) => 1 - THREE.MathUtils.smoothstep(vector(points[joint]).distanceTo(vector(points[0])), .55, 1.35));
    // When both hands are close, translate the pair together to preserve their
    // relation. Face-relative mapping compensates for this avatar's proportions.
    const pairWeight = 1 - THREE.MathUtils.smoothstep(vector(points[15]).distanceTo(vector(points[16])), .25, .65);
    const sharedFaceWeight = Math.max(...faceWeights);
    for (const [side, index, handStart] of [['left', 0, 33], ['right', 1, 54]] as const) {
      const upper = `${side}UpperArm`;
      const lower = `${side}LowerArm`;
      const hand = `${side}Hand`;
      const shoulder = this.get(upper).node.getWorldPosition(new THREE.Vector3());
      const upperLength = this.get(upper).position.distanceTo(this.get(lower).position);
      const lowerLength = this.get(lower).position.distanceTo(this.get(hand).position);
      const targetWrist = vector(points[15 + index]).multiplyScalar(this.span).add(center);
      const targetElbow = vector(points[13 + index]).multiplyScalar(this.span).add(center);
      targetWrist.addScaledVector(faceOffset, THREE.MathUtils.lerp(faceWeights[index], sharedFaceWeight, pairWeight));
      const sourceUpper = vector(points[13 + index]).sub(vector(points[11 + index]));
      const sourceLower = vector(points[15 + index]).sub(vector(points[13 + index]));
      const sourceFlex = THREE.MathUtils.radToDeg(sourceUpper.angleTo(sourceLower));
      const sourceArmLength = sourceUpper.length() + sourceLower.length();
      const hangingRatio = -points[15 + index][1] / Math.max(sourceArmLength, 1e-5);
      const restWeight = THREE.MathUtils.smoothstep(hangingRatio, .55, .85) * (1 - THREE.MathUtils.smoothstep(sourceFlex, 35, 75));
      const restFlex = THREE.MathUtils.degToRad(THREE.MathUtils.clamp(sourceFlex, 15, 45));
      const restingReach = Math.sqrt(upperLength ** 2 + lowerLength ** 2 + 2 * upperLength * lowerLength * Math.cos(restFlex));
      const restingWrist = targetWrist.clone().sub(shoulder).normalize().multiplyScalar(restingReach).add(shoulder);
      targetWrist.lerp(restingWrist, restWeight);
      // The rendered blouse reaches 0.132 m in front of this rig. Use an
      // avatar-scaled envelope, with soft lateral edges, before solving IK.
      const torsoX = targetWrist.x - center.x;
      const torsoY = targetWrist.y - center.y;
      if (torsoY < 0.04 && torsoY > -this.span * 2.6) {
        const envelope = 1 - THREE.MathUtils.smoothstep(Math.abs(torsoX) / this.span, 0.62, 0.84);
        const clearance = side === 'right' && contact?.target === 'abdomen' ? THREE.MathUtils.lerp(.95, .55, contact.weight) : .95;
        targetWrist.z = THREE.MathUtils.lerp(targetWrist.z, Math.max(targetWrist.z, center.z + this.span * clearance), envelope);
      }
      const previousWrist = this.wrists.get(side) ?? targetWrist.clone();
      const movement = targetWrist.clone().sub(previousWrist).multiplyScalar(alpha);
      movement.clampLength(0, 3 * dt);
      targetWrist.copy(previousWrist.add(movement));
      this.wrists.set(side, targetWrist.clone());
      // Maintain the elbow's bend plane through straight-arm singularities.
      const axis = targetWrist.clone().sub(shoulder).normalize();
      const proposedPole = targetElbow.clone().sub(shoulder);
      proposedPole.addScaledVector(axis, -proposedPole.dot(axis));
      const previousPole = this.poles.get(side);
      if (previousPole) {
        const transported = previousPole.clone().addScaledVector(axis, -previousPole.dot(axis)).normalize();
        if (proposedPole.lengthSq() < 1e-6) {
          proposedPole.copy(transported);
        } else if (transported.lengthSq() > 1e-6) {
          proposedPole.normalize();
          const turn = new THREE.Quaternion().setFromUnitVectors(transported, proposedPole);
          const angle = turn.angleTo(new THREE.Quaternion());
          if (angle > 8 * dt) {
            turn.slerp(new THREE.Quaternion(), 1 - 8 * dt / angle);
            proposedPole.copy(transported.applyQuaternion(turn));
          }
        }
      }
      if (proposedPole.lengthSq() > 1e-8) {
        this.poles.set(side, proposedPole.clone().normalize());
        targetElbow.copy(shoulder).add(proposedPole);
      }
      const solved = solveArm(shoulder, targetWrist, targetElbow, upperLength, lowerLength);
      // Solve the complete chain after temporal filtering. Independently
      // smoothing these two rotations would break the IK/contact constraint.
      this.aim(upper, solved.elbow.clone().sub(shoulder));
      const actualElbow = this.get(lower).node.getWorldPosition(new THREE.Vector3());
      this.aim(lower, solved.wrist.clone().sub(actualElbow));
      const actualWrist = this.get(hand).node.getWorldPosition(new THREE.Vector3());
      this.diagnostics.currentReachError = Math.max(this.diagnostics.currentReachError, actualWrist.distanceTo(solved.wrist));
      this.diagnostics.maximumReachError = Math.max(this.diagnostics.maximumReachError, actualWrist.distanceTo(solved.wrist));
      const handPoints = points.slice(handStart, handStart + 21).map(vector);
      const articulation = this.hands[side].solve(handPoints, dt);
      this.diagnostics.jointAngles.push(articulation.angles);
      this.diagnostics.fingerCorrectionDegrees.push(articulation.correctionDegrees);
      this.diagnostics.limitedFingerSegments += articulation.limited;
      if (articulation.degenerate) {
        this.diagnostics.degeneratePalms += 1;
      }
      const upperDirection = actualElbow.clone().sub(shoulder).normalize();
      const lowerDirection = actualWrist.clone().sub(actualElbow).normalize();
      this.diagnostics.elbowFlexDegrees.push(THREE.MathUtils.radToDeg(upperDirection.angleTo(lowerDirection)));
      const restAcross = this.get(`${side}IndexProximal`).position.clone().sub(this.get(`${side}LittleProximal`).position);
      const restAlong = this.get(`${side}MiddleProximal`).position.clone().sub(this.get(hand).position);
      const wrist = this.palms[side].step(articulation.basis, lowerDirection, dt);
      this.diagnostics.wristCorrectionDegrees.push(wrist.correctionDegrees);
      const limitedPalm = wrist.frame;
      this.palmFrames.set(side, limitedPalm.clone());
      const rotation = limitedPalm.clone().multiply(basis(restAcross, restAlong).invert());
      const displayedDelta = limitedPalm.clone().multiply(articulation.basis.clone().invert());
      this.worldRotation(hand, rotation.clone().multiply(this.get(hand).quaternion));
      this.diagnostics.maximumPalmSpeed = Math.max(this.palms.left.maximumSpeed, this.palms.right.maximumSpeed);
      this.diagnostics.palmForward.push(...new THREE.Vector3(0, 1, 0).applyQuaternion(limitedPalm).toArray());

      const fingers = [
        { names: ['ThumbMetacarpal', 'ThumbProximal', 'ThumbDistal'], joints: [1, 2, 3, 4] },
        { names: ['IndexProximal', 'IndexIntermediate', 'IndexDistal'], joints: [5, 6, 7, 8] },
        { names: ['MiddleProximal', 'MiddleIntermediate', 'MiddleDistal'], joints: [9, 10, 11, 12] },
        { names: ['RingProximal', 'RingIntermediate', 'RingDistal'], joints: [13, 14, 15, 16] },
        { names: ['LittleProximal', 'LittleIntermediate', 'LittleDistal'], joints: [17, 18, 19, 20] },
      ];
      for (const [fingerIndex, finger] of fingers.entries()) {
        for (let boneIndex = 0; boneIndex < 3; boneIndex += 1) {
          const name = side + finger.names[boneIndex];
          const restDirection = boneIndex < 2
            ? this.get(side + finger.names[boneIndex + 1]).position.clone().sub(this.get(name).position)
            : this.get(name).position.clone().sub(this.get(side + finger.names[boneIndex - 1]).position);
          // A direction alone leaves roll unconstrained and flips near 180°.
          // Transport the complete palm/hinge frame, including its stable axis.
          const targetFrame = displayedDelta.clone().multiply(articulation.frames[fingerIndex][boneIndex]);
          const desired = targetFrame.multiply(basis(restAcross, restDirection).invert()).multiply(this.get(name).quaternion);
          this.worldRotation(name, desired);
        }
      }
    }
    this.contactError = 0;
    if (contact) this.refineContact(contact, dt, previousContactWrists);
    const blinkPhase = seconds % 4.7;
    const blink = blinkPhase < 0.14 ? Math.sin(blinkPhase / 0.14 * Math.PI) : 0;
    this.vrm.expressionManager?.setValue('blink', blink);
    this.vrm.expressionManager?.setValue('clinicQuestion', question);
    this.vrm.update(deltaSeconds);
    this.diagnostics.fingerRotations = ['leftIndexProximal', 'leftIndexIntermediate', 'rightIndexProximal', 'rightIndexIntermediate'].flatMap((name) => this.get(name).node.quaternion.toArray());
    this.diagnostics.wristPositions = ['leftHand', 'rightHand'].flatMap((name) => this.get(name).node.getWorldPosition(new THREE.Vector3()).toArray());
    this.diagnostics.frames += 1;
    return { ...this.diagnostics, contactErrorM: this.contactError, contactTarget: contact?.target ?? null };
  }
}
