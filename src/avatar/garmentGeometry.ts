import * as THREE from 'three';
import type { VRM } from '@pixiv/three-vrm';

/** Remove only the concealed arm triangles. Hands and a visible wrist margin
 * retain their original vertices, morphs and skinning. This avoids skin breaking
 * through the coat during a tight elbow bend without per-frame collision work. */
export function coveredArmGeometry(source: THREE.BufferGeometry, mesh: THREE.SkinnedMesh, vrm: VRM) {
  if (!source.index) return source;
  const inverse = mesh.matrixWorld.clone().invert(), positions = source.getAttribute('position');
  const arms = (['left', 'right'] as const).map(side => {
    const shoulder = vrm.humanoid.getRawBoneNode(`${side}UpperArm`)!.getWorldPosition(new THREE.Vector3()).applyMatrix4(inverse);
    const wrist = vrm.humanoid.getRawBoneNode(`${side}Hand`)!.getWorldPosition(new THREE.Vector3()).applyMatrix4(inverse);
    const axis = wrist.clone().sub(shoulder).normalize();
    return { shoulder, axis, length: wrist.distanceTo(shoulder) };
  });
  const covered = (id: number) => arms.some(arm => {
    const offset = new THREE.Vector3().fromBufferAttribute(positions, id).sub(arm.shoulder);
    const along = offset.dot(arm.axis);
    return along > .015 && along < arm.length - .032 && offset.addScaledVector(arm.axis, -along).length() < .14;
  });
  const indices: number[] = [];
  for (let i = 0; i < source.index.count; i += 3) {
    const face = [0, 1, 2].map(c => source.index!.getX(i + c));
    if (!face.every(covered)) indices.push(...face);
  }
  if (indices.length === source.index.count) return source;
  const result = source.clone(); result.setIndex(indices); result.clearGroups();
  result.addGroup(0, indices.length, 0); return result;
}

export function extendSleeves(source: THREE.BufferGeometry, mesh: THREE.SkinnedMesh, vrm: VRM) {
  const result = source.clone(), positions = result.getAttribute('position');
  const joints = result.getAttribute('skinIndex'), weights = result.getAttribute('skinWeight');
  const inverse = mesh.matrixWorld.clone().invert();
  for (const side of ['left', 'right'] as const) {
    const upper = vrm.humanoid.getRawBoneNode(`${side}UpperArm`)!, lower = vrm.humanoid.getRawBoneNode(`${side}LowerArm`)!;
    const hand = vrm.humanoid.getRawBoneNode(`${side}Hand`)!;
    const shoulder = upper.getWorldPosition(new THREE.Vector3()).applyMatrix4(inverse);
    const elbow = lower.getWorldPosition(new THREE.Vector3()).applyMatrix4(inverse);
    const wrist = hand.getWorldPosition(new THREE.Vector3()).applyMatrix4(inverse);
    const axis = elbow.clone().sub(shoulder).normalize(), upperLength = shoulder.distanceTo(elbow);
    const armLength = upperLength + elbow.distanceTo(wrist) - .018;
    const upperId = mesh.skeleton.bones.indexOf(upper as THREE.Bone), lowerId = mesh.skeleton.bones.indexOf(lower as THREE.Bone);
    if (upperId < 0 || lowerId < 0) continue;
    for (let i = 0; i < positions.count; i++) {
      const p = new THREE.Vector3().fromBufferAttribute(positions, i), offset = p.clone().sub(shoulder);
      const d = offset.dot(axis);
      if (d <= .025) continue;
      // Cloth displacement depends on position, never on inherited bone weights.
      // Adjacent shirt vertices can have different weights at the old armhole;
      // using those weights as a displacement mask tears the extended sleeve.
      // Restrict the mask to the armhole radius: wide waist vertices may also
      // lie beyond the shoulder's x coordinate but do not belong to a sleeve.
      const radius = offset.clone().addScaledVector(axis, -d).length();
      const tailoring = THREE.MathUtils.smoothstep(d, .025, .065)
        * (1 - THREE.MathUtils.smoothstep(radius, .13, .20));
      if (tailoring === 0) continue;
      const cuffPlane = .2775 + .088 * (p.y - 1.53) + .040 * (p.z + .016);
      const cuffPoint = p.clone(); cuffPoint.x = Math.sign(p.x) * cuffPlane;
      const cuffDistance = cuffPoint.sub(shoulder).dot(axis);
      const t = THREE.MathUtils.clamp((d - .025) / (cuffDistance - .025), 0, 1.006);
      const newD = .025 + t * (armLength - .025);
      const center = newD < upperLength ? shoulder.clone().lerp(elbow, newD / upperLength)
        : elbow.clone().lerp(wrist, (newD - upperLength) / elbow.distanceTo(wrist));
      const radial = offset.addScaledVector(axis, -d).multiplyScalar(1 - .39 * t);
      const cuff = THREE.MathUtils.smoothstep(t, .74, 1);
      const cuffRadius = .034;
      radial.lerp(radial.clone().normalize().multiplyScalar(cuffRadius), cuff * .85);
      // Millimetre-scale, broad folds. Geometry is generated once, then skinned.
      const fold = 1 + .028 * Math.sin(t * Math.PI * 7) * Math.sin(t * Math.PI);
      const target = center.addScaledVector(radial, fold).lerp(p, 1 - tailoring);
      positions.setXYZ(i, target.x, target.y, target.z);
      const lowerWeight = THREE.MathUtils.smoothstep(newD, upperLength - .055, upperLength + .055);
      const skin = new Map<number, number>();
      for (let c = 0; c < 4; c++)skin.set(joints.getComponent(i, c), (skin.get(joints.getComponent(i, c)) ?? 0) + weights.getComponent(i, c) * (1 - tailoring));
      skin.set(upperId, (skin.get(upperId) ?? 0) + (1 - lowerWeight) * tailoring);
      skin.set(lowerId, (skin.get(lowerId) ?? 0) + lowerWeight * tailoring);
      const strongest = [...skin].sort((a, b) => b[1] - a[1]).slice(0, 4), sum = strongest.reduce((s, [, w]) => s + w, 0);
      for (let c = 0; c < 4; c++) { joints.setComponent(i, c, strongest[c]?.[0] ?? 0); weights.setComponent(i, c, (strongest[c]?.[1] ?? 0) / sum); }
    }
  }
  // Fair the stretched surface in bind space, carrying skin weights through
  // the same neighborhood. The old short sleeve has a very uneven longitudinal
  // density; without this, interpolation makes saw-tooth folds at deep bends.
  const neighbors = Array.from({ length: positions.count }, () => new Set<number>());
  if (result.index) for (let i = 0; i < result.index.count; i += 3) {
    const ids = [0, 1, 2].map(c => result.index!.getX(i + c));
    for (let c = 0; c < 3; c++) { neighbors[ids[c]].add(ids[(c + 1) % 3]); neighbors[ids[c]].add(ids[(c + 2) % 3]); }
  }
  for (let pass = 0; pass < 4; pass++) {
    const original = positions.array.slice(), oldJoints = joints.array.slice(), oldWeights = weights.array.slice();
    for (let i = 0; i < positions.count; i++) {
      if (Math.abs(original[i * 3]) < .19 || original[i * 3 + 1] < 1.30 || neighbors[i].size < 2) continue;
      const total = neighbors[i].size, point = new THREE.Vector3(), influences = new Map<number, number>();
      const add = (id: number, factor: number) => {
        point.addScaledVector(new THREE.Vector3(original[id * 3], original[id * 3 + 1], original[id * 3 + 2]), factor);
        for (let c = 0; c < 4; c++)influences.set(oldJoints[id * 4 + c], (influences.get(oldJoints[id * 4 + c]) ?? 0) + oldWeights[id * 4 + c] * factor);
      };
      add(i, .5); for (const j of neighbors[i]) add(j, .5 / total);
      positions.setXYZ(i, point.x, point.y, point.z);
      const skin = [...influences].sort((a, b) => b[1] - a[1]).slice(0, 4), sum = skin.reduce((s, [, w]) => s + w, 0);
      for (let c = 0; c < 4; c++) { joints.setComponent(i, c, skin[c]?.[0] ?? 0); weights.setComponent(i, c, (skin[c]?.[1] ?? 0) / sum); }
    }
  }
  return result;
}

/** One Loop subdivision on the existing sewn garment. Welding happens in rest
 * space, with skin influences carried through the same convex combinations.
 * This replaces the short sleeve by a continuous long sleeve, retaining the
 * original shoulder/armhole topology instead of stacking separate cylinders. */
export function tailoredCoat(source: THREE.BufferGeometry): THREE.BufferGeometry {
  const position = source.getAttribute('position');
  const joints = source.getAttribute('skinIndex'), weights = source.getAttribute('skinWeight');
  if (!joints || !weights || !source.index) return source.clone();
  type Vertex = { p: THREE.Vector3; skin: Map<number, number> };
  const vertices: Vertex[] = [], triangles: number[][] = [], welded = new Map<string, number>();
  const ids = new Map<number, number>();
  const vertex = (i: number) => {
    const known = ids.get(i); if (known !== undefined) return known;
    const p = new THREE.Vector3().fromBufferAttribute(position, i);
    const key = p.toArray().map(v => Math.round(v * 100000)).join(',');
    let id = welded.get(key);
    if (id === undefined) {
      id = vertices.length; welded.set(key, id);
      const skin = new Map<number, number>();
      for (let c = 0; c < 4; c++) {
        const w = weights.getComponent(i, c), j = joints.getComponent(i, c);
        skin.set(j, (skin.get(j) ?? 0) + w);
      }
      vertices.push({ p, skin });
    }
    ids.set(i, id); return id;
  };
  for (let i = 0; i < source.index.count; i += 3) {
    const face = [0, 1, 2].map(c => vertex(source.index!.getX(i + c)));
    if (new Set(face).size === 3) triangles.push(face);
  }
  const neighbors = vertices.map(() => new Set<number>());
  const edges = new Map<string, { a: number; b: number; opposite: number[]; id?: number }>();
  const key = (a: number, b: number) => a < b ? `${a}:${b}` : `${b}:${a}`;
  for (const f of triangles) for (let c = 0; c < 3; c++) {
    const a = f[c], b = f[(c + 1) % 3], opposite = f[(c + 2) % 3];
    neighbors[a].add(b); neighbors[b].add(a);
    const k = key(a, b), edge = edges.get(k) ?? { a, b, opposite: [] };
    edge.opposite.push(opposite); edges.set(k, edge);
  }
  const mix = (terms: [number, number][]): Vertex => {
    const p = new THREE.Vector3(), skin = new Map<number, number>();
    for (const [id, factor] of terms) {
      p.addScaledVector(vertices[id].p, factor);
      for (const [bone, w] of vertices[id].skin) skin.set(bone, (skin.get(bone) ?? 0) + w * factor);
    }
    return { p, skin };
  };
  const next = vertices.map((_, i) => {
    const boundary = [...neighbors[i]].filter(j => edges.get(key(i, j))!.opposite.length !== 2);
    if (boundary.length === 2) return mix([[i, .75], ...boundary.map(j => [j, .125] as [number, number])]);
    if (boundary.length) return mix([[i, 1]]);
    const n = neighbors[i].size, beta = n === 3 ? 3 / 16 : 3 / (8 * n);
    return mix([[i, 1 - n * beta], ...[...neighbors[i]].map(j => [j, beta] as [number, number])]);
  });
  for (const edge of edges.values()) {
    edge.id = next.length;
    next.push(mix(edge.opposite.length === 2
      ? [[edge.a, .375], [edge.b, .375], [edge.opposite[0], .125], [edge.opposite[1], .125]]
      : [[edge.a, .5], [edge.b, .5]]));
  }
  const index: number[] = [];
  for (const [a, b, c] of triangles) {
    const ab = edges.get(key(a, b))!.id!, bc = edges.get(key(b, c))!.id!, ca = edges.get(key(c, a))!.id!;
    index.push(a, ab, ca, ab, b, bc, ca, bc, c, ab, bc, ca);
  }
  const positions: number[] = [], skinIndices: number[] = [], skinWeights: number[] = [];
  for (const v of next) {
    positions.push(...v.p.toArray());
    const influences = [...v.skin].sort((a, b) => b[1] - a[1]).slice(0, 4);
    const total = influences.reduce((sum, [, w]) => sum + w, 0) || 1;
    for (let c = 0; c < 4; c++) {
      skinIndices.push(influences[c]?.[0] ?? 0); skinWeights.push((influences[c]?.[1] ?? 0) / total);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(skinIndices, 4));
  geometry.setAttribute('skinWeight', new THREE.Float32BufferAttribute(skinWeights, 4));
  geometry.setIndex(index); geometry.addGroup(0, index.length, 0); geometry.computeVertexNormals();
  geometry.computeBoundingBox(); geometry.computeBoundingSphere();
  return geometry;
}
