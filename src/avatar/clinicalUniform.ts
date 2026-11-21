import * as THREE from 'three';
import type { VRM } from '@pixiv/three-vrm';

/** Curved, rig-attached tailoring. The continuous coat/sleeves are derived from
 * the original skinned garment by garmentGeometry; these are only folded lapels,
 * shirt and small trim. No garment physics runs in the animation loop. */
export function addClinicalUniform(vrm: VRM) {
  vrm.scene.updateMatrixWorld(true);
  const at = (name: Parameters<typeof vrm.humanoid.getRawBoneNode>[0]) => vrm.humanoid.getRawBoneNode(name)!;
  const neck = at('neck').getWorldPosition(new THREE.Vector3());
  const span = at('leftUpperArm').getWorldPosition(new THREE.Vector3()).distanceTo(at('rightUpperArm').getWorldPosition(new THREE.Vector3()));
  const chest = at('upperChest') ?? at('chest');
  const white = new THREE.MeshStandardMaterial({ color: '#f4f6f3', roughness: .91, side: THREE.DoubleSide });
  const thread = new THREE.MeshStandardMaterial({ color: '#d7dfd9', roughness: .95 });
  const blue = new THREE.MeshStandardMaterial({ color: '#b9cfd7', roughness: .94, side: THREE.DoubleSide });
  const green = new THREE.MeshStandardMaterial({ color: '#28534a', roughness: .91, side: THREE.DoubleSide });
  const mount = (mesh: THREE.Mesh) => {
    mesh.applyMatrix4(vrm.scene.matrixWorld.clone().invert()); vrm.scene.add(mesh);
    mesh.updateMatrixWorld(true); chest.attach(mesh); mesh.frustumCulled = false; return mesh;
  };
  const point = ([x, y, z]: number[]) => new THREE.Vector3(neck.x + x * span, neck.y + y * span, neck.z + (.48 + z) * span);
  const patch = (left: number[][], right: number[][], material: THREE.Material, fullness = .012) => {
    const a = new THREE.CatmullRomCurve3(left.map(point), false, 'centripetal');
    const b = new THREE.CatmullRomCurve3(right.map(point), false, 'centripetal');
    const positions: number[] = [], indices: number[] = [];
    const rows = 32, columns = 12;
    for (let row = 0; row <= rows; row++) {
      const v = row / rows, start = a.getPoint(v), end = b.getPoint(v);
      for (let col = 0; col <= columns; col++) {
        const u = col / columns, p = start.clone().lerp(end, u);
        p.z += span * fullness * Math.sin(Math.PI * u) * Math.sin(Math.PI * v);
        positions.push(...p.toArray());
        if (row < rows && col < columns) { const q = row * (columns + 1) + col, r = q + columns + 1; indices.push(q, r, q + 1, q + 1, r, r + 1); }
      }
    }
    const geometry = new THREE.BufferGeometry(); geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setIndex(indices); geometry.computeVertexNormals(); return mount(new THREE.Mesh(geometry, material));
  };
  patch([[-.20, -.08, -.04], [-.17, -.39, .005], [0, -.91, .015]], [[.20, -.08, -.04], [.17, -.39, .005], [0, -.91, .015]], blue, .02);
  for (const side of [-1, 1]) {
    const mirror = (points: number[][]) => points.map(([x, y, z]) => [side * x, y, z]);
    patch(mirror([[.16, -.025, -.03], [.29, -.08, -.005], [.39, -.15, .005]]),
      mirror([[.07, -.20, .07], [.18, -.30, .085], [.26, -.36, .065]]), white, .018);
    patch(mirror([[.39, -.15, .007], [.44, -.32, .015], [.34, -.42, .035], [.38, -.49, .027], [.025, -1.08, .03]]),
      mirror([[.27, -.24, .035], [.22, -.32, .045], [.19, -.42, .05], [.14, -.64, .045], [.025, -1.08, .03]]), white, .008);
  }
  patch([[-.058, -.22, .095], [-.045, -.31, .105]], [[.058, -.22, .095], [.045, -.31, .105]], green, .02);
  patch([[-.034, -.30, .09], [-.045, -.63, .085], [-.060, -.77, .07], [0, -.85, .08]],
    [[.034, -.30, .09], [.045, -.63, .085], [.060, -.77, .07], [0, -.85, .08]], green, .015);
  for (const height of [1.12, 1.42, 1.72]) {
    const button = new THREE.Mesh(new THREE.SphereGeometry(span * .012, 12, 8), thread);
    button.scale.z = .4; button.position.copy(point([.025, -height, .007])); mount(button);
  }
  // A small generic identity badge, guided by the supplied 175 uniform images.
  const canvas = document.createElement('canvas'); canvas.width = 256; canvas.height = 384;
  const c = canvas.getContext('2d')!; c.textAlign = 'center';
  c.fillStyle = '#22745f'; c.font = 'italic 900 72px Segoe UI'; c.fillText('175', 128, 78);
  c.fillStyle = '#d34a4a'; c.fillRect(105, 1, 10, 30); c.fillRect(95, 11, 30, 10);
  c.fillStyle = '#e1eae4'; c.fillRect(32, 138, 192, 225); c.fillStyle = '#fff'; c.fillRect(42, 149, 172, 202);
  c.fillStyle = '#2d6959'; c.fillRect(42, 149, 172, 28); c.font = '600 24px Segoe UI'; c.fillText('BÁC SĨ', 128, 236);
  c.fillStyle = '#638276'; c.font = '16px Segoe UI'; c.fillText('VSL CLINIC', 128, 273);
  const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace; texture.anisotropy = 4;
  const badge = new THREE.Mesh(new THREE.PlaneGeometry(span * .19, span * .285), new THREE.MeshStandardMaterial({ map: texture, transparent: true, roughness: .94, depthWrite: false }));
  badge.position.copy(point([.43, -.72, .015])); mount(badge);

  // A narrow sewn cuff covers the original folded short-sleeve hem after it is
  // extended. It follows the forearm and leaves the complete wrist/hand free.
  for (const side of ['left', 'right'] as const) {
    const lower = at(`${side}LowerArm`), wrist = at(`${side}Hand`).getWorldPosition(new THREE.Vector3());
    const direction = wrist.clone().sub(lower.getWorldPosition(new THREE.Vector3())).normalize();
    const cuff = new THREE.Mesh(new THREE.CylinderGeometry(.036, .037, .040, 32, 4, true), white);
    cuff.name = `Clinic-${side}-cuff`; cuff.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
    cuff.position.copy(wrist).addScaledVector(direction, -.029);
    cuff.applyMatrix4(vrm.scene.matrixWorld.clone().invert()); vrm.scene.add(cuff); cuff.updateMatrixWorld(true);
    lower.attach(cuff); cuff.frustumCulled = false;
  }
}
