import * as THREE from 'three';

// Conservative rendering guardrails, not population ROM measurements.
// Keep these versioned and report corrections instead of claiming sign accuracy.
export const RULES = Object.freeze({
  profile: 'clinic-articulation-v2',
  mcpFlex: [-20, 100],
  mcpSpread: [-30, 30],
  pipFlex: [-8, 115],
  dipFlex: [-10, 85],
  thumbBaseCone: 85,
  thumbRootCone: 45,
  thumbMcp: 85,
  thumbIp: 95,
  elbowFlex: [3, 155],
  wristFlex: [-80, 80],
  wristDeviation: [-35, 35],
  fingerSpeed: 16,
  fingerAcceleration: 150,
  palmSpeed: 12,
  palmAcceleration: 100,
});

const radians = THREE.MathUtils.degToRad;
const degrees = THREE.MathUtils.radToDeg;
const EPS = 1e-8;

export function palmBasis(points: THREE.Vector3[]): THREE.Quaternion | null {
  const along = points[9].clone().sub(points[0]);
  const across = points[5].clone().sub(points[17]);
  if (along.lengthSq() < EPS || across.lengthSq() < EPS) {
    return null;
  }
  along.normalize();
  across.addScaledVector(along, -across.dot(along));
  if (across.lengthSq() < EPS) {
    return null;
  }
  across.normalize();
  const normal = new THREE.Vector3().crossVectors(across, along).normalize();
  return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(across, along, normal));
}

export class AngleFollower {
  value: number;
  velocity = 0;
  maximumSpeed = 0;
  maximumAcceleration = 0;

  constructor(initial: number) {
    this.value = initial;
  }

  step(target: number, dt: number) {
    const error = target - this.value;
    const desired = THREE.MathUtils.clamp(error * 35, -RULES.fingerSpeed, RULES.fingerSpeed);
    const velocity = THREE.MathUtils.clamp(desired, this.velocity - RULES.fingerAcceleration * dt, this.velocity + RULES.fingerAcceleration * dt);
    const movement = velocity * dt;
    // Near the target, settle monotonically. The acceleration statistic includes
    // this braking; the audit flags it rather than hiding it in the limiter.
    const next = movement * error > 0 && Math.abs(movement) > Math.abs(error) ? target : this.value + movement;
    const actualVelocity = (next - this.value) / dt;
    this.maximumSpeed = Math.max(this.maximumSpeed, Math.abs(actualVelocity));
    this.maximumAcceleration = Math.max(this.maximumAcceleration, Math.abs(actualVelocity - this.velocity) / dt);
    this.velocity = actualVelocity;
    this.value = next;
    return next;
  }
}

export class RotationFollower {
  value: THREE.Quaternion | null = null;
  maximumSpeed = 0;
  private speed = 0;

  step(target: THREE.Quaternion, dt: number) {
    if (!this.value) {
      this.value = target.clone();
      return this.value.clone();
    }
    const angle = this.value.angleTo(target);
    const desired = Math.min(RULES.palmSpeed, angle * 35, Math.sqrt(2 * RULES.palmAcceleration * angle));
    this.speed = THREE.MathUtils.clamp(desired, this.speed - RULES.palmAcceleration * dt, this.speed + RULES.palmAcceleration * dt);
    const movement = Math.min(angle, Math.max(0, this.speed) * dt);
    this.value.rotateTowards(target, movement);
    this.maximumSpeed = Math.max(this.maximumSpeed, movement / dt);
    return this.value.clone();
  }
}

export interface HandSolution {
  basis: THREE.Quaternion;
  directions: THREE.Vector3[][];
  frames: THREE.Quaternion[][];
  angles: number[][];
  correctionDegrees: number;
  maximumCorrectionDegrees: number;
  limited: number;
  degenerate: boolean;
}

function limitDirection(direction: THREE.Vector3, anchor: THREE.Vector3, maximum: number): THREE.Vector3 {
  if (direction.lengthSq() < EPS) {
    return anchor.clone();
  }
  const target = direction.clone().normalize();
  const angle = anchor.angleTo(target);
  if (angle <= maximum) {
    return target;
  }
  const rotation = new THREE.Quaternion().setFromUnitVectors(anchor, target);
  rotation.slerp(new THREE.Quaternion(), 1 - maximum / angle);
  return anchor.clone().applyQuaternion(rotation);
}

function fitFingerFlex(observed: number[]): number[] {
  const limits = [RULES.mcpFlex, RULES.pipFlex, RULES.dipFlex].map((range) => range.map(radians));
  const angles = observed.map((value, index) => {
    const relative = index === 0 ? value : value - observed[index - 1];
    return THREE.MathUtils.clamp(Math.atan2(Math.sin(relative), Math.cos(relative)), limits[index][0], limits[index][1]);
  });
  // Fit all three directions together inside the feasible hinge envelope.
  // Each coordinate update rotates its downstream segments by the same angle.
  // This avoids propagating a clipped/noisy knuckle into an impossible fingertip.
  const weights = [1.5, 1, .75];
  for (let pass = 0; pass < 5; pass += 1) {
    for (let joint = 0; joint < 3; joint += 1) {
      let sine = 0;
      let cosine = 0;
      let cumulative = 0;
      for (let segment = 0; segment < 3; segment += 1) {
        cumulative += angles[segment];
        if (segment >= joint) {
          const target = observed[segment] - cumulative + angles[joint];
          sine += weights[segment] * Math.sin(target);
          cosine += weights[segment] * Math.cos(target);
        }
      }
      const candidate = Math.atan2(sine, cosine);
      const difference = Math.atan2(Math.sin(candidate - angles[joint]), Math.cos(candidate - angles[joint]));
      angles[joint] = THREE.MathUtils.clamp(angles[joint] + difference, limits[joint][0], limits[joint][1]);
    }
  }
  return angles;
}

/** Palm-local articulation. PIP/DIP share the MCP hinge plane, so no sideways
 * bending or per-phalanx roll can be introduced by a noisy world-space point. */
export class HandArticulation {
  private previousBasis = new THREE.Quaternion();
  private filters = new Map<string, AngleFollower>();
  private thumbFilters = [new RotationFollower(), new RotationFollower(), new RotationFollower()];
  private thumbRoot = new RotationFollower();

  constructor(private side: 'left' | 'right') {}

  private angle(key: string, value: number, limits: readonly number[], dt: number) {
    const bounded = THREE.MathUtils.clamp(value, radians(limits[0]), radians(limits[1]));
    let follower = this.filters.get(key);
    if (!follower) {
      follower = new AngleFollower(bounded);
      this.filters.set(key, follower);
    }
    const result = follower.step(bounded, dt);
    // Acceleration inertia must not carry a joint outside its hard envelope.
    const clipped = THREE.MathUtils.clamp(result, radians(limits[0]), radians(limits[1]));
    if (clipped !== result) {
      follower.velocity = 0;
      follower.value = clipped;
    }
    return clipped;
  }

  solve(points: THREE.Vector3[], dt: number): HandSolution {
    const observed = palmBasis(points);
    const frame = observed ?? this.previousBasis;
    this.previousBasis.copy(frame);
    const inverse = frame.clone().invert();
    const local = points.map((point) => point.clone().sub(points[0]).applyQuaternion(inverse));
    const palmar = new THREE.Vector3(0, 0, this.side === 'left' ? -1 : 1);
    const result: HandSolution = { basis: frame.clone(), directions: [], frames: [], angles: [], correctionDegrees: 0, maximumCorrectionDegrees: 0, limited: 0, degenerate: !observed };
    const record = (raw: THREE.Vector3, corrected: THREE.Vector3) => {
      const correction = raw.lengthSq() < EPS ? 0 : degrees(raw.angleTo(corrected));
      result.correctionDegrees += correction;
      result.maximumCorrectionDegrees = Math.max(result.maximumCorrectionDegrees, correction);
      if (correction > 5) {
        result.limited += 1;
      }
    };

    // The thumb has opposition at CMC: retain its 3-D plane, not the other
    // fingers' single hinge. Bound each cone, then filter in palm coordinates.
    const thumb: THREE.Vector3[] = [];
    const thumbFrames: THREE.Quaternion[] = [];
    // The thumb root stays on the radial side of the palm. A noisy depth
    // estimate must not move this reference behind the wrist, then make the
    // hard CMC cone snap an otherwise filtered thumb by nearly 180 degrees.
    // Filter the cone's moving anchor too; the rig's root position is fixed.
    const radialAnchor = new THREE.Vector3(.8, .6, 0);
    const rootDirection = limitDirection(local[1], radialAnchor, radians(RULES.thumbRootCone));
    const rootFrame = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), rootDirection);
    let thumbAnchor = new THREE.Vector3(0, 1, 0).applyQuaternion(this.thumbRoot.step(rootFrame, dt));
    thumbAnchor = limitDirection(thumbAnchor, radialAnchor, radians(RULES.thumbRootCone));
    for (let segment = 0; segment < 3; segment += 1) {
      const raw = local[segment + 2].clone().sub(local[segment + 1]);
      const maximum = radians([RULES.thumbBaseCone, RULES.thumbMcp, RULES.thumbIp][segment]);
      const target = limitDirection(raw, thumbAnchor, maximum);
      const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), target);
      const filteredFrame = this.thumbFilters[segment].step(q, dt);
      const filtered = new THREE.Vector3(0, 1, 0).applyQuaternion(filteredFrame);
      const direction = limitDirection(filtered, thumbAnchor, maximum);
      const constrainedFrame = new THREE.Quaternion().setFromUnitVectors(filtered, direction).multiply(filteredFrame);
      thumbFrames.push(frame.clone().multiply(constrainedFrame));
      record(raw, direction);
      thumb.push(direction.clone().applyQuaternion(frame));
      thumbAnchor = direction;
    }
    result.directions.push(thumb);
    result.frames.push(thumbFrames);
    result.angles.push([]);

    for (let finger = 0; finger < 4; finger += 1) {
      const base = 5 + finger * 4;
      const metacarpal = local[base].clone().setZ(0).normalize();
      const baseYaw = Math.atan2(metacarpal.x, metacarpal.y);
      const raw = [0, 1, 2].map((segment) => local[base + segment + 1].clone().sub(local[base + segment]).normalize());
      let spread = Math.atan2(raw[0].x, raw[0].y) - baseYaw;
      // A finger folded past 90 degrees reverses its projection. Do not
      // misinterpret that as a 180-degree lateral rotation of the knuckle.
      spread = Math.atan2(Math.sin(spread), Math.cos(spread));
      if (spread > Math.PI / 2) {
        spread -= Math.PI;
      } else if (spread < -Math.PI / 2) {
        spread += Math.PI;
      }
      const observedFlat = new THREE.Vector3(Math.sin(baseYaw + spread), Math.cos(baseYaw + spread), 0);
      const observedFlex = raw.map((direction) => Math.atan2(direction.dot(palmar), direction.dot(observedFlat)));
      const fitted = fitFingerFlex(observedFlex);
      spread = this.angle(`${finger}:spread`, spread, RULES.mcpSpread, dt);
      const flat = new THREE.Vector3(Math.sin(baseYaw + spread), Math.cos(baseYaw + spread), 0);
      const flex = this.angle(`${finger}:mcp`, fitted[0], RULES.mcpFlex, dt);
      let cumulative = flex;
      const directions: THREE.Vector3[] = [];
      const frames: THREE.Quaternion[] = [];
      const hingeAxis = new THREE.Vector3(Math.cos(baseYaw + spread), -Math.sin(baseYaw + spread), 0);
      const angles = [degrees(spread), degrees(flex)];
      for (let segment = 0; segment < 3; segment += 1) {
        if (segment > 0) {
          const bend = this.angle(`${finger}:${segment}`, fitted[segment], segment === 1 ? RULES.pipFlex : RULES.dipFlex, dt);
          cumulative += bend;
          angles.push(degrees(bend));
        }
        const direction = flat.clone().multiplyScalar(Math.cos(cumulative)).addScaledVector(palmar, Math.sin(cumulative));
        const normal = new THREE.Vector3().crossVectors(hingeAxis, direction).normalize();
        const localFrame = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(hingeAxis, direction, normal));
        frames.push(frame.clone().multiply(localFrame));
        record(raw[segment], direction);
        directions.push(direction.applyQuaternion(frame));
      }
      result.directions.push(directions);
      result.frames.push(frames);
      result.angles.push(angles);
    }
    result.correctionDegrees /= 15;
    return result;
  }
}

/** Measure wrist swing in its palm axes. Forearm roll is retained through the
 * palm frame; flexion/deviation are bounded independently. */
export function constrainWrist(frame: THREE.Quaternion, forearmDirection: THREE.Vector3) {
  const local = forearmDirection.clone().normalize().applyQuaternion(frame.clone().invert());
  const flex = Math.atan2(local.z, local.y);
  const deviation = Math.atan2(local.x, Math.hypot(local.y, local.z));
  const boundedFlex = THREE.MathUtils.clamp(flex, radians(RULES.wristFlex[0]), radians(RULES.wristFlex[1]));
  const boundedDeviation = THREE.MathUtils.clamp(deviation, radians(RULES.wristDeviation[0]), radians(RULES.wristDeviation[1]));
  const target = new THREE.Vector3(Math.sin(boundedDeviation), Math.cos(boundedDeviation) * Math.cos(boundedFlex), Math.cos(boundedDeviation) * Math.sin(boundedFlex));
  const correction = new THREE.Quaternion().setFromUnitVectors(target, local);
  return { frame: frame.clone().multiply(correction), correctionDegrees: degrees(correction.angleTo(new THREE.Quaternion())) };
}
