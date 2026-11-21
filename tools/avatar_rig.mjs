import * as THREE from 'three';
import { VRMHumanoid } from '@pixiv/three-vrm';

/** Actual avatar hierarchy for joint regressions without a texture renderer.
 * Rendered skin, cloth and contact readability still need browser inspection. */
export function avatarRig(bytes) {
  const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString('utf8'));
  const scene = new THREE.Group();
  const nodes = gltf.nodes.map(entry => {
    const node = new THREE.Object3D();
    node.name = entry.name ?? '';
    if (entry.translation) node.position.fromArray(entry.translation);
    if (entry.rotation) node.quaternion.fromArray(entry.rotation);
    if (entry.scale) node.scale.fromArray(entry.scale);
    if (entry.matrix) new THREE.Matrix4().fromArray(entry.matrix).decompose(node.position, node.quaternion, node.scale);
    return node;
  });
  gltf.nodes.forEach((entry, index) => {
    for (const child of entry.children ?? []) nodes[index].add(nodes[child]);
  });
  for (const index of gltf.scenes[gltf.scene ?? 0].nodes) scene.add(nodes[index]);
  const legacy = !gltf.extensions.VRMC_vrm;
  if (legacy) scene.rotation.y = Math.PI;
  scene.updateMatrixWorld(true);
  const bones = legacy
    ? gltf.extensions.VRM.humanoid.humanBones.map(entry => [entry.bone.replace('ThumbProximal', 'ThumbMetacarpal').replace('ThumbIntermediate', 'ThumbProximal'), entry])
    : Object.entries(gltf.extensions.VRMC_vrm.humanoid.humanBones);
  const humanoid = new VRMHumanoid(Object.fromEntries(bones.map(([name, entry]) => [name, { node: nodes[entry.node] }])));
  scene.add(humanoid.normalizedHumanBonesRoot);
  scene.updateMatrixWorld(true);
  return { scene, humanoid, update: () => humanoid.update() };
}
