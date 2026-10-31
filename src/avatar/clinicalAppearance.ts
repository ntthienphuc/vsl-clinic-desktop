import * as THREE from 'three';
import type { VRM } from '@pixiv/three-vrm';

/** A restrained adult appearance on the existing, fully articulated male rig.
 * Rest-pose edits also transform morph deltas, so blinks and questions stay aligned.
 * No bone lengths, hand geometry or source motion are changed.
 */
export function clinicalAppearance(vrm: VRM): void {
  const materials = new Map<THREE.Material, THREE.MeshStandardMaterial>();
  const geometries = new Map<THREE.BufferGeometry, THREE.BufferGeometry>();
  const deformFace = (x: number, y: number, z: number) => {
    // Coordinates belong to ClinicMale's documented rest mesh, in metres.
    const eyeX = x < 0 ? -0.040 : 0.0415;
    const weight = Math.exp(-Math.pow((x - eyeX) / .038, 4) - Math.pow((y - 1.740) / .031, 4));
    const front = THREE.MathUtils.smoothstep(-z, .045, .075);
    const jaw = Math.exp(-Math.pow((y - 1.675) / .030, 2));
    return new THREE.Vector3(x + (x - eyeX) * -.10 * weight * front + x * .16 * jaw,
      y + (y - 1.740) * -.28 * weight * front, z);
  };
  vrm.scene.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return;
    const sourceMaterials = Array.isArray(object.material) ? object.material : [object.material];
    // The VRoid hair cards are deliberately replaced by one smooth short haircut.
    if (sourceMaterials.every((m) => /Hair/i.test(m.name) || (m as THREE.Material & { isOutline?: boolean }).isOutline)) {
      object.visible = false;
      return;
    }
    if (/Face/i.test(object.name)) {
      const source: THREE.BufferGeometry = object.geometry;
      let geometry = geometries.get(source);
      if (!geometry) {
        geometry = source.clone();
        const positions = geometry.getAttribute('position');
        const base = source.getAttribute('position');
        for (let i = 0; i < base.count; i++) {
          const p = deformFace(base.getX(i), base.getY(i), base.getZ(i));
          positions.setXYZ(i, p.x, p.y, p.z);
        }
        for (const morph of geometry.morphAttributes.position ?? []) {
          for (let i = 0; i < base.count; i++) {
            const relative = geometry.morphTargetsRelative;
            const p = deformFace(morph.getX(i) + (relative ? base.getX(i) : 0),
              morph.getY(i) + (relative ? base.getY(i) : 0), morph.getZ(i) + (relative ? base.getZ(i) : 0));
            morph.setXYZ(i, p.x - (relative ? positions.getX(i) : 0),
              p.y - (relative ? positions.getY(i) : 0), p.z - (relative ? positions.getZ(i) : 0));
          }
        }
        geometry.computeVertexNormals();
        geometry.computeBoundingBox();
        geometry.computeBoundingSphere();
        geometries.set(source, geometry);
      }
      object.geometry = geometry;
    }
    if (sourceMaterials.some((m) => /Tops/.test(m.name))) {
      const geometry = object.geometry.clone();
      const positions = geometry.getAttribute('position');
      for (let i = 0; i < positions.count; i++) {
        const y = positions.getY(i);
        const hem = 1 - THREE.MathUtils.smoothstep(y, 1.12, 1.35);
        positions.setXYZ(i, positions.getX(i) * (1 + .12 * hem), y - .15 * hem, positions.getZ(i));
      }
      geometry.computeVertexNormals();
      geometry.computeBoundingSphere();
      object.geometry = geometry;
    }
    const convert = (source: THREE.Material) => {
      const cached = materials.get(source);
      if (cached) return cached;
      const old = source as THREE.Material & { map?: THREE.Texture; color?: THREE.Color; isOutline?: boolean };
      const name = source.name;
      const cloth = /Tops|Bottoms|AccessoryNeck/.test(name);
      const material = new THREE.MeshStandardMaterial({ name, map: cloth ? null : old.map,
        color: /Tops/.test(name) ? '#f4f6f5' : /Bottoms/.test(name) ? '#243342' : /AccessoryNeck/.test(name) ? '#233f50' : old.color?.clone() ?? '#ffffff',
        roughness: /EyeIris|EyeWhite/.test(name) ? .48 : .84, metalness: 0,
        side: source.side, transparent: source.transparent, opacity: source.opacity,
        alphaTest: source.alphaTest, depthWrite: source.depthWrite,
      });
      if (/EyeIris/.test(name)) material.color.set('#6a665c');
      if (/Face.*SKIN|Body.*SKIN/.test(name)) material.color.set('#e8ccb9');
      if (/FaceEyelash|FaceEyeline|FaceBrow/.test(name)) material.color.set('#51473f');
      if (/EyeHighlight|Hair/i.test(name) || old.isOutline) material.visible = false;
      if (material.map) material.map.anisotropy = 8;
      materials.set(source, material);
      return material;
    };
    object.material = Array.isArray(object.material) ? sourceMaterials.map(convert) : convert(sourceMaterials[0]);
  });

  // A continuous, low-cost scalp surface: high hairline, tapered sides and subtle part.
  // World-space construction respects VRM0's facing correction when attached to head.
  vrm.scene.updateMatrixWorld(true);
  const head = vrm.humanoid.getRawBoneNode('head')!;
  const attachWorld = (mesh: THREE.Mesh) => {
    mesh.applyMatrix4(vrm.scene.matrixWorld.clone().invert());
    vrm.scene.add(mesh);
    mesh.updateMatrixWorld(true);
    head.attach(mesh);
    mesh.frustumCulled = false;
  };
  const positions: number[] = [], indices: number[] = [], colors: number[] = [];
  const rings = 24, sectors = 96;
  for (let row = 0; row <= rings; row++) {
    for (let col = 0; col <= sectors; col++) {
      const azimuth = col / sectors * Math.PI * 2;
      const front = Math.cos(azimuth);
      const edge = 1.65 - .30 * front + .07 * Math.sin(azimuth) * Math.max(0, front);
      const theta = row / rings * edge;
      const sweep = (.018 * Math.sin(azimuth * 32 + theta * 6) + .025 * Math.sin(azimuth * 2 + theta * 3)) * Math.sin(theta);
      const radius = 1 + sweep;
      positions.push(-.0008 + .103 * Math.sin(theta) * Math.sin(azimuth) * radius,
        1.777 + .116 * Math.cos(theta), .018 + .111 * Math.sin(theta) * Math.cos(azimuth) * radius);
      const strand = .80 + .20 * Math.cos(azimuth * 32 + theta * 6);
      const c = new THREE.Color('#292a29').multiplyScalar(strand);
      colors.push(c.r, c.g, c.b);
      if (row < rings && col < sectors) {
        const a = row * (sectors + 1) + col, b = a + sectors + 1;
        indices.push(a, b, a + 1, a + 1, b, b + 1);
      }
    }
  }
  const hair = new THREE.BufferGeometry();
  hair.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  hair.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  hair.setIndex(indices);
  hair.computeVertexNormals();
  attachWorld(new THREE.Mesh(hair, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .82, side: THREE.DoubleSide })));
  const frameMaterial = new THREE.MeshStandardMaterial({ color: '#404b50', metalness: .45, roughness: .4 });
  for (const side of [-1, 1]) {
    const cx = side * .040 - .0008;
    const points = [[-.027, .010], [-.018, .014], [.018, .014], [.027, .010],
      [.025, -.010], [.018, -.014], [-.018, -.014], [-.025, -.010]]
      .map(([x, y]) => new THREE.Vector3(cx + x, 1.740 + y, .104 - Math.abs(cx + x) * .10));
    attachWorld(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points, true), 48, .0010, 6, true), frameMaterial));
  }
  const bridge = new THREE.CatmullRomCurve3([new THREE.Vector3(-.014, 1.744, .105), new THREE.Vector3(0, 1.748, .112), new THREE.Vector3(.013, 1.744, .105)]);
  attachWorld(new THREE.Mesh(new THREE.TubeGeometry(bridge, 12, .001, 6, false), frameMaterial));
}
