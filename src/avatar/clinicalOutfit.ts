import * as THREE from 'three';
import type { VRM } from '@pixiv/three-vrm';

/** Keep the author's continuous skinned shirt, sleeves and body. No rigid coat panels. */
export function dressClinician(vrm: VRM) {
  vrm.scene.updateMatrixWorld(true);
  const position = (name: Parameters<typeof vrm.humanoid.getRawBoneNode>[0]) => vrm.humanoid.getRawBoneNode(name)!.getWorldPosition(new THREE.Vector3());
  const neck = position('neck');
  const shoulder = position('leftUpperArm').distanceTo(position('rightUpperArm'));
  const parent = vrm.humanoid.getRawBoneNode('upperChest') ?? vrm.humanoid.getRawBoneNode('chest')!;
  for (const material of vrm.materials ?? []) {
    const surface = material as THREE.Material & { color?: THREE.Color; shadeColorFactor?: THREE.Color; map?: THREE.Texture | null; shadeMultiplyTexture?: THREE.Texture | null; outlineWidthFactor?: number };
    if (material.name.includes('Tops')) {
      surface.map = null;
      surface.shadeMultiplyTexture = null;
      surface.color?.set('#e9f0ed');
      surface.shadeColorFactor?.set('#b7c9c7');
    } else if (material.name.includes('Bottoms')) {
      surface.map = null;
      surface.shadeMultiplyTexture = null;
      surface.color?.set('#27434d');
      surface.shadeColorFactor?.set('#182c35');
    } else if (material.name.includes('AccessoryNeck')) {
      // The source's school tie is a separate skinned primitive.
      surface.visible = false;
    } else if (/Hair/i.test(material.name)) {
      surface.color?.set('#453d38');
      surface.shadeColorFactor?.set('#292a2c');
    }
    if (surface.outlineWidthFactor !== undefined) {
      surface.outlineWidthFactor *= 0.22;
    }
    if (surface.map) {
      surface.map.anisotropy = 8;
    }
    surface.needsUpdate = true;
  }
  // Accessories are small objects attached to clothing, not substitute body geometry.
  const add = (mesh: THREE.Mesh) => {
    // Accessory vertices are authored in world space; VRM 0's scene is rotated.
    mesh.applyMatrix4(vrm.scene.matrixWorld.clone().invert());
    vrm.scene.add(mesh);
    mesh.updateMatrixWorld(true);
    parent.attach(mesh);
    mesh.frustumCulled = false;
    return mesh;
  };
  const front = neck.z + shoulder * 0.48;
  const top = neck.y - shoulder * 0.14;
  const tube = new THREE.MeshStandardMaterial({ color: '#1e5558', roughness: 0.65 });
  const metal = new THREE.MeshStandardMaterial({ color: '#b9c7cc', metalness: 0.65, roughness: 0.26 });
  const curve = new THREE.CatmullRomCurve3([
    [-.19, .03, -.12], [-.26, -.19, 0], [-.26, -.48, .015],
    [-.17, -.66, .015], [0, -.70, .02], [.19, -.62, .01], [.24, -.39, 0], [.19, .03, -.12],
  ].map(([x, y, z]) => new THREE.Vector3(neck.x + x * shoulder, top + y * shoulder, front + z * shoulder)));
  add(new THREE.Mesh(new THREE.TubeGeometry(curve, 64, shoulder * .012, 10, false), tube));
  const disc = new THREE.Mesh(new THREE.CylinderGeometry(shoulder * .058, shoulder * .058, shoulder * .024, 32), metal);
  disc.rotation.x = Math.PI / 2;
  disc.position.set(neck.x + shoulder * .19, top - shoulder * .62, front + shoulder * .025);
  add(disc);
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 320;
  const context = canvas.getContext('2d')!;
  context.fillStyle = '#f8faf8';
  context.fillRect(0, 0, 512, 320);
  context.fillStyle = '#126b68';
  context.fillRect(0, 0, 512, 65);
  context.textAlign = 'center';
  context.font = 'bold 72px sans-serif';
  context.fillText('BÁC SĨ', 256, 178);
  context.font = '40px sans-serif';
  context.fillText('VSL CLINIC', 256, 250);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  const badge = new THREE.Mesh(new THREE.PlaneGeometry(shoulder * .34, shoulder * .21), new THREE.MeshStandardMaterial({ map: texture, roughness: .8 }));
  badge.position.set(neck.x - shoulder * .32, top - shoulder * .65, front - shoulder * .015);
  add(badge);
  const buttonMaterial = new THREE.MeshStandardMaterial({ color: '#c1cccf', roughness: .6 });
  for (const height of [.84, 1.02, 1.20]) {
    const button = new THREE.Mesh(new THREE.CylinderGeometry(shoulder * .012, shoulder * .012, shoulder * .006, 12), buttonMaterial);
    button.rotation.x = Math.PI / 2;
    button.position.set(neck.x, top - shoulder * height, front - shoulder * .015);
    add(button);
  }
}
