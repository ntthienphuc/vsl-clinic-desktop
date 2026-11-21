import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRM, VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import { Pause, Play, RotateCcw } from 'lucide-react';
import { t } from '../i18n';
import type { Motion } from '../types';
import { MotionLibrary } from './motionLibrary';
import { blendPose, neutralPose, sampleMotion } from './motion';
import { HumanoidRetargeter } from './retarget';
import { dressClinician } from './clinicalOutfit';
import { clinicalAppearance } from './clinicalAppearance';
import { handContact } from './contact';

/** Local silent preview has no session/playback API. It cannot send a word or
 * interrupt the patient screen. One rig, three cached clips, render only open. */
export function DictionaryPreview({ id, avatarUrl, entries }: { id: string; avatarUrl: string; entries: { id: string; path: string }[] }) {
  const host = useRef<HTMLDivElement>(null);
  const controls = useRef({ id, playing: true, time: 0, speed: 1, yaw: 0, restart: 0 });
  const [playing, setPlaying] = useState(true), [speed, setSpeed] = useState(1), [yaw, setYaw] = useState(0);
  const [progress, setProgress] = useState(0), [status, setStatus] = useState('Đang mở ký hiệu…');
  const duration = useRef(1);
  controls.current.id = id; controls.current.playing = playing; controls.current.speed = speed; controls.current.yaw = yaw;
  useEffect(() => { controls.current.time = 0; controls.current.restart++; setProgress(0); setPlaying(true); setStatus('Đang mở ký hiệu…'); }, [id]);
  useEffect(() => {
    const container = host.current!;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
    renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.localClippingEnabled = true;
    renderer.domElement.setAttribute('role', 'img');
    container.append(renderer.domElement);
    const scene = new THREE.Scene(), camera = new THREE.OrthographicCamera(-.8, .8, .7, -.7, .01, 20);
    scene.add(new THREE.HemisphereLight(0xffffff, 0xc4ced3, 1.8));
    const key = new THREE.DirectionalLight(0xfff7ed, 2.4); key.position.set(-1, 2.5, 3); scene.add(key);
    const rim = new THREE.DirectionalLight(0xe3edf5, 1.2); rim.position.set(2, 1.8, -2); scene.add(rim);
    let vrm: VRM | undefined, rig: HumanoidRetargeter | undefined, motion: Motion | undefined;
    let disposed = false, frame = 0, previous = performance.now(), nextPaint = previous, lastUi = 0, selected = '', cycle = -1;
    let centerY = 1.25, framingHeight = 1.5;
    const library = new MotionLibrary(entries, 3);
    const markReady = () => { if (rig && motion && !disposed) setStatus(''); };
    const resize = () => {
      const w = Math.max(1, container.clientWidth), h = Math.max(1, container.clientHeight), aspect = w / h;
      const vertical = Math.max(framingHeight, 1.45 / aspect);
      renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5, Math.sqrt(1_500_000 / (w * h))));
      renderer.setSize(w, h, false);
      camera.left = -vertical * aspect / 2; camera.right = -camera.left; camera.top = vertical / 2; camera.bottom = -camera.top;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize); observer.observe(container); resize();
    const loader = new GLTFLoader(); loader.register(parser => new VRMLoaderPlugin(parser));
    void loader.loadAsync(avatarUrl).then(gltf => {
      if (disposed) { VRMUtils.deepDispose(gltf.scene); return; }
      vrm = gltf.userData.vrm as VRM;
      if (!vrm) throw Error('Chưa mở được ký hiệu.');
      VRMUtils.removeUnnecessaryVertices(gltf.scene); VRMUtils.combineSkeletons(gltf.scene); VRMUtils.rotateVRM0(vrm);
      dressClinician(vrm); clinicalAppearance(vrm); scene.add(vrm.scene); vrm.scene.updateMatrixWorld(true);
      const bounds = new THREE.Box3().setFromObject(vrm.scene);
      const floor = vrm.humanoid.getNormalizedBoneNode('hips')!.getWorldPosition(new THREE.Vector3()).y - .18;
      centerY = (bounds.max.y + floor) / 2; framingHeight = (bounds.max.y - floor) * 1.18;
      resize(); rig = new HumanoidRetargeter(vrm); markReady();
    }).catch(error => { if (!disposed) setStatus(error.message); });
    const lost = (event: Event) => { event.preventDefault(); setPlaying(false); setStatus('Hình ảnh tạm gián đoạn. Đóng từ điển rồi mở lại.'); };
    renderer.domElement.addEventListener('webglcontextlost', lost);
    const tick = (now: number) => {
      if (disposed) return;
      frame = requestAnimationFrame(tick);
      const c = controls.current;
      if (selected !== c.id) {
        selected = c.id; motion = undefined; const wanted = selected;
        void library.prepare([wanted]).then(() => {
          if (disposed || selected !== wanted) return;
          motion = library.motions.get(wanted); duration.current = (motion?.duration_ms ?? 1) + 700;
          c.time = 0; setProgress(0); markReady();
        }).catch(error => { if (!disposed && selected === wanted) setStatus(error.message); });
      }
      if (cycle !== c.restart) { cycle = c.restart; c.time = 0; }
      if (document.hidden) { previous = now; nextPaint = now; return; }
      if (now < nextPaint - 1) return;
      nextPaint += 1000 / (c.playing ? 30 : 12);
      if (nextPaint < now) nextPaint = now + 1000 / 30;
      const dt = Math.min(.1, Math.max(.001, (now - previous) / 1000)); previous = now;
      if (motion && rig) {
        if (c.playing) c.time = Math.min(duration.current, c.time + dt * 1000 * c.speed);
        const time = c.time, end = motion.duration_ms;
        const pose = time < 350 ? blendPose(neutralPose(), sampleMotion(motion, 0), THREE.MathUtils.smoothstep(time, 0, 350))
          : time > end + 350 ? blendPose(sampleMotion(motion, end), neutralPose(), THREE.MathUtils.smoothstep(time - end - 350, 0, 350))
          : sampleMotion(motion, time - 350);
        rig.apply(pose, dt, now / 1000, 0, time >= 350 && time <= end + 350 ? handContact(motion.id, (time - 350) / end) : undefined);
        if (time >= duration.current && c.playing) { c.playing = false; setPlaying(false); }
        if (now - lastUi > 90) { setProgress(time / duration.current); lastUi = now; }
      }
      camera.position.set(Math.sin(c.yaw) * 3.5, centerY, Math.cos(c.yaw) * 3.5); camera.lookAt(0, centerY, 0);
      renderer.render(scene, camera);
    };
    frame = requestAnimationFrame(tick);
    return () => {
      disposed = true; cancelAnimationFrame(frame); observer.disconnect(); library.dispose();
      renderer.domElement.removeEventListener('webglcontextlost', lost);
      if (vrm) VRMUtils.deepDispose(vrm.scene);
      renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove();
    };
  }, [avatarUrl, entries]);
  return <div className="dictionary-preview">
    <div className="dictionary-stage" ref={host} aria-label={t('Xem ký hiệu')} />
    {status && <p className="dictionary-preview-status" role="status">{t(status)}</p>}
    <div className="dictionary-transport">
      <button className="icon-button" aria-label={t(playing ? 'Tạm dừng' : 'Phát ký hiệu')} onClick={() => { if (progress >= 1) controls.current.restart++; setPlaying(!playing); }}>{playing ? <Pause size={18}/> : <Play size={18}/>}</button>
      <button className="icon-button" aria-label={t('Xem lại')} onClick={() => { controls.current.restart++; setPlaying(true); }}><RotateCcw size={18}/></button>
      <input type="range" min="0" max="1000" value={Math.round(progress * 1000)} aria-label={t('Vị trí ký hiệu')} onChange={e => { const value = Number(e.target.value) / 1000; controls.current.time = value * duration.current; setProgress(value); setPlaying(false); }}/>
      <button className="text-button" aria-pressed={speed < 1} onClick={() => setSpeed(speed === 1 ? .65 : 1)}>{t(speed === 1 ? 'Xem chậm' : 'Tốc độ thường')}</button>
    </div>
    <div className="dictionary-angles" aria-label={t('Góc nhìn')}>
      {([[-.5, 'Nghiêng trái'], [0, 'Chính diện'], [.5, 'Nghiêng phải']] as const).map(([angle, label]) => <button key={label} className={yaw === angle ? 'selected' : ''} aria-pressed={yaw === angle} onClick={() => setYaw(angle)}>{t(label)}</button>)}
    </div>
  </div>;
}
