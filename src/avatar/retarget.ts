import * as THREE from 'three';
import { VRM, VRMHumanBoneName } from '@pixiv/three-vrm';
import type { Point } from '../types';
import { HandArticulation, RotationFollower, RULES, constrainWrist } from './kinematics';

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
  private palms = { left: new RotationFollower(), right: new RotationFollower() };
  private poles = new Map<string, THREE.Vector3>();
  private wrists = new Map<string, THREE.Vector3>();
  private armFrames = new Map<string, THREE.Quaternion>();
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

  private aim(name: string, child: string, targetDirection: THREE.Vector3) {
    const rest = this.get(name);
    const localDirection = this.get(child).position.clone().sub(rest.position).normalize().applyQuaternion(rest.quaternion.clone().invert());
    const previous = this.armFrames.get(name) ?? rest.quaternion;
    // Parallel-transport the full bone frame from the preceding direction.
    // Re-solving a shortest arc from the fixed T pose introduces a roll
    // singularity when an arm crosses its opposite rest direction (VRM0).
    // This changes orientation without smoothing away the solved IK endpoint.
    const desired = transportAim(localDirection, previous, targetDirection);
    this.armFrames.set(name, desired.clone());
    this.worldRotation(name, desired);
  }

  apply(points: Point[], deltaSeconds: number, seconds: number, question = 0) {
    const dt = THREE.MathUtils.clamp(deltaSeconds, 1 / 240, 0.1);
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
        targetWrist.z = THREE.MathUtils.lerp(targetWrist.z, Math.max(targetWrist.z, center.z + this.span * 0.95), envelope);
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
      this.aim(upper, lower, solved.elbow.clone().sub(shoulder));
      const actualElbow = this.get(lower).node.getWorldPosition(new THREE.Vector3());
      this.aim(lower, hand, solved.wrist.clone().sub(actualElbow));
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
      const wrist = constrainWrist(articulation.basis, lowerDirection);
      this.diagnostics.wristCorrectionDegrees.push(wrist.correctionDegrees);
      const filteredPalm = this.palms[side].step(wrist.frame, dt);
      const limitedPalm = constrainWrist(filteredPalm, lowerDirection).frame;
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
    const blinkPhase = seconds % 4.7;
    const blink = blinkPhase < 0.14 ? Math.sin(blinkPhase / 0.14 * Math.PI) : 0;
    this.vrm.expressionManager?.setValue('blink', blink);
    this.vrm.expressionManager?.setValue('clinicQuestion', question);
    this.vrm.update(deltaSeconds);
    this.diagnostics.fingerRotations = ['leftIndexProximal', 'leftIndexIntermediate', 'rightIndexProximal', 'rightIndexIntermediate'].flatMap((name) => this.get(name).node.quaternion.toArray());
    this.diagnostics.wristPositions = ['leftHand', 'rightHand'].flatMap((name) => this.get(name).node.getWorldPosition(new THREE.Vector3()).toArray());
    this.diagnostics.frames += 1;
    return this.diagnostics;
  }
}
