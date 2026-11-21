import * as THREE from 'three';
import type { VRM } from '@pixiv/three-vrm';
import { addClinicalUniform } from './clinicalUniform';

export function dressClinician(vrm: VRM) {
  for (const material of vrm.materials ?? []) {
    const surface=material as THREE.Material & {color?:THREE.Color;shadeColorFactor?:THREE.Color;map?:THREE.Texture|null;shadeMultiplyTexture?:THREE.Texture|null;outlineWidthFactor?:number};
    if (/Tops|Bottoms/.test(material.name)) {
      surface.map=null;surface.shadeMultiplyTexture=null;
      surface.color?.set(material.name.includes('Tops')?'#f8faf7':'#243342');
      surface.shadeColorFactor?.set(material.name.includes('Tops')?'#c6d2cd':'#182c35');
    }
    if(material.name.includes('AccessoryNeck'))surface.visible=false;
    if(surface.outlineWidthFactor!==undefined)surface.outlineWidthFactor*=.22;
    if(surface.map)surface.map.anisotropy=4;
    surface.needsUpdate=true;
  }
  addClinicalUniform(vrm);
}
