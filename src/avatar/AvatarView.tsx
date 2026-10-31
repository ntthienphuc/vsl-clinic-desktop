import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRM, VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import { LoaderCircle, Maximize2 } from 'lucide-react';
import { request } from '../api';
import type { Bootstrap, Motion, Playback } from '../types';
import { samplePlaylist } from './motion';
import { HumanoidRetargeter } from './retarget';
import { dressClinician } from './clinicalOutfit';
import { clinicalAppearance } from './clinicalAppearance';
import { installQuestionExpression, questionWeight } from './nonmanual';

export function AvatarView({ bootstrap, playback }: { bootstrap: Bootstrap; playback: Playback | null }) {
  const host = useRef<HTMLDivElement>(null);
  const current = useRef(playback);
  const zoomRef = useRef(false);
  const [zoom, setZoom] = useState(false);
  const [ready, setReady] = useState(false);
  const [failure, setFailure] = useState('');
  const [label, setLabel] = useState('');
  const [progress, setProgress] = useState(0);
  const [activeIndex, setActiveIndex] = useState(-1);
  current.current = playback;
  zoomRef.current = zoom;

  useEffect(() => {
    const container = host.current!;
    let disposed = false;
    let frame = 0;
    let contextLost = false;
    let contextPause = '';
    let vrm: VRM | null = null;
    let retargeter: HumanoidRetargeter | null = null;
    const motions = new Map<string, Motion>();
    const sentReady = new Set<string>();
    const sentComplete = new Set<string>();
    const sentPaint = new Set<string>();
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.localClippingEnabled = true;
    renderer.domElement.setAttribute('aria-label', 'Avatar 3D thực hiện ký hiệu bằng cánh tay, bàn tay và các ngón tay');
    renderer.domElement.setAttribute('role', 'img');
    container.append(renderer.domElement);
    const pauseForContext = () => {
      const playing = current.current;
      const cycle = playing ? `${playing.id}:${playing.iteration}` : '';
      if (playing?.status === 'playing' && contextPause !== cycle) {
        contextPause = cycle;
        void request('/playback', { action: 'pause', playback_id: playing.id }).catch(() => { contextPause = ''; });
      }
    };
    const loseContext = (event: Event) => {
      event.preventDefault();
      contextLost = true;
      setFailure('Hình ảnh 3D tạm gián đoạn. Đang khôi phục; ký hiệu đã được tạm dừng.');
      pauseForContext();
    };
    const restoreContext = () => {
      contextLost = false;
      contextPause = '';
      setFailure('');
    };
    renderer.domElement.addEventListener('webglcontextlost', loseContext);
    renderer.domElement.addEventListener('webglcontextrestored', restoreContext);
    const scene = new THREE.Scene();
    let framingHeight = 1.3;
    let framingWidth = 1.3;
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 20);
    camera.position.set(0, 1.18, 3.5);
    camera.lookAt(0, 1.18, 0);
    scene.add(new THREE.HemisphereLight(0xffffff, 0xc4ced3, 1.8));
    const key = new THREE.DirectionalLight(0xfff7ed, 2.4);
    key.position.set(-1, 2.5, 3);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0xe3edf5, 1.2);
    rim.position.set(2, 1.8, -2);
    scene.add(rim);
    const resize = () => {
      const width = Math.max(1, container.clientWidth);
      const height = Math.max(1, container.clientHeight);
      const aspect = width / height;
      // Supersample thin fingers at 1080p, with a bounded GPU pixel budget.
      renderer.setPixelRatio(Math.min(Math.max(devicePixelRatio, 1.5), 2, Math.sqrt(2_400_000 / (width * height))));
      const vertical = Math.max(framingHeight, framingWidth / aspect) * (zoomRef.current ? 0.90 : 1);
      camera.left = -vertical * aspect / 2;
      camera.right = vertical * aspect / 2;
      camera.top = vertical / 2;
      camera.bottom = -vertical / 2;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(container);
    resize();
    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));
    let loaded = false;
    const setup = async () => {
      const [gltf, clips] = await Promise.all([
        loader.loadAsync(bootstrap.avatar_url),
        Promise.all(bootstrap.bank.entries.map(async (entry) => {
          const response = await fetch(entry.path);
          if (!response.ok) {
            throw new Error(`Chưa tải được chuyển động ${entry.id}`);
          }
          return await response.json() as Motion;
        })),
      ]);
      if (disposed) {
        VRMUtils.deepDispose(gltf.scene);
        return;
      }
      vrm = gltf.userData.vrm as VRM;
      if (!vrm) {
        throw new Error('Tệp avatar chưa có bộ xương VRM.');
      }
      VRMUtils.removeUnnecessaryVertices(gltf.scene);
      VRMUtils.combineSkeletons(gltf.scene);
      VRMUtils.rotateVRM0(vrm);
      vrm.scene.traverse((object) => { object.frustumCulled = false; });
      dressClinician(vrm);
      clinicalAppearance(vrm);
      installQuestionExpression(vrm);
      scene.add(vrm.scene);
      vrm.scene.updateMatrixWorld(true);
      const bounds = new THREE.Box3().setFromObject(vrm.scene);
      const hips = vrm.humanoid.getNormalizedBoneNode('hips')!.getWorldPosition(new THREE.Vector3());
      const headTop = bounds.max.y;
      const floor = hips.y - 0.18;
      framingHeight = (headTop - floor) * 1.18;
      framingWidth = 1.45;
      const centerY = (headTop + floor) / 2;
      camera.position.set(0, centerY, 3.5);
      camera.lookAt(0, centerY, 0);
      resize();
      retargeter = new HumanoidRetargeter(vrm);
      for (const clip of clips) {
        motions.set(clip.id, clip);
      }
      loaded = true;
      setReady(true);
    };
    void setup().catch((problem: Error) => {
      if (!disposed) {
        setFailure(problem.message);
      }
    });
    let lastFrame = performance.now();
    let nextFrame = lastFrame;
    let lastTargetFps = 0;
    let fpsFrames = 0;
    let fpsStarted = lastFrame;
    let measuredFps = 0;
    let lastNotice = 0;
    let lastZoom = false;
    let renderStats = { cycle: '', frames: 0, activeMs: 0, last: 0, maxGap: 0, cpuMs: 0 };
    const animate = () => {
      if (disposed) {
        return;
      }
      frame = requestAnimationFrame(animate);
      if (contextLost) { pauseForContext(); return; }
      const frameTime = performance.now();
      const playing = current.current;
      // The patient camera shares this laptop with the renderer. Preserve full
      // resolution, but don't animate a waiting avatar at display refresh rate.
      // A deadline (rather than resetting the clock on each paint) also avoids
      // locking to half the display rate when rAF is slightly late.
      const targetFps = playing?.status === 'playing' || playing?.status === 'loading' ? 30 : 12;
      if (targetFps !== lastTargetFps || lastZoom !== zoomRef.current) {
        nextFrame = frameTime;
        lastTargetFps = targetFps;
      }
      if (frameTime < nextFrame - 1) {
        return;
      }
      nextFrame += 1000 / targetFps;
      if (nextFrame < frameTime) nextFrame = frameTime + 1000 / targetFps;
      const delta = Math.min((frameTime - lastFrame) / 1000, 0.1);
      lastFrame = frameTime;
      fpsFrames += 1;
      if (frameTime - fpsStarted > 1000) {
        measuredFps = fpsFrames * 1000 / (frameTime - fpsStarted);
        fpsFrames = 0;
        fpsStarted = frameTime;
      }
      const seconds = frameTime / 1000;
      if (lastZoom !== zoomRef.current) {
        resize();
        lastZoom = zoomRef.current;
      }
      const cycle = playing ? `${playing.id}:${playing.iteration}` : '';
      if (loaded && retargeter) {
        if (playing?.status === 'loading' && !sentReady.has(cycle)) {
          sentReady.add(cycle);
          void request('/playback', { action: 'ready', playback_id: playing.id, iteration: playing.iteration }).catch(() => sentReady.delete(cycle));
        }
        const sample = samplePlaylist(playing, motions);
        const question = questionWeight(playing);
        const diagnostics = retargeter.apply(sample.pose, delta, seconds, question);
        window.clinicDiagnostics = { ...diagnostics, questionWeight: question, playbackId: playing?.id, iteration: playing?.iteration, progress: sample.progress, label: sample.label, glossIndex: sample.index, phase: sample.phase, rendererFrames: renderer.info.render.frame, measuredFps };
        if (seconds - lastNotice > 0.08) {
          setLabel(sample.label);
          setProgress(sample.progress);
          setActiveIndex(sample.index);
          lastNotice = seconds;
        }
        if (playing?.status === 'playing' && sample.complete && !sentComplete.has(cycle)) {
          sentComplete.add(cycle);
          if (renderStats.cycle === cycle) {
            void request('/metrics', { event: 'patient_avatar_render_summary', role: 'patient',
              playback_id: playing.id, iteration: playing.iteration, renderer_frames: renderStats.frames,
              measured_fps: renderStats.activeMs > 0 ? (renderStats.frames - 1) * 1000 / renderStats.activeMs : 0,
              mean_cpu_ms: renderStats.cpuMs / Math.max(1, renderStats.frames), max_frame_gap_ms: renderStats.maxGap,
            }).catch(() => undefined);
          }
          void request('/playback', { action: 'complete', playback_id: playing.id, iteration: playing.iteration }).catch(() => sentComplete.delete(cycle));
        }
        if (playing?.status === 'playing' && !sample.complete) {
          sentComplete.delete(cycle);
        }
      }
      const renderStarted = performance.now();
      renderer.render(scene, camera);
      if (loaded && playing?.status === 'playing') {
        if (renderStats.cycle !== cycle) renderStats = { cycle, frames: 0, activeMs: 0, last: 0, maxGap: 0, cpuMs: 0 };
        if (renderStats.last) {
          const gap = frameTime - renderStats.last;
          renderStats.activeMs += gap;
          renderStats.maxGap = Math.max(renderStats.maxGap, gap);
        }
        renderStats.last = frameTime;
        renderStats.frames++;
        renderStats.cpuMs += performance.now() - frameTime;
      } else {
        renderStats.last = 0;
      }
      if (window.clinicDiagnostics) {
        window.clinicDiagnostics.cpuFrameMs = performance.now() - frameTime;
        window.clinicDiagnostics.renderSubmitMs = performance.now() - renderStarted;
        window.clinicDiagnostics.drawCalls = renderer.info.render.calls;
        window.clinicDiagnostics.triangles = renderer.info.render.triangles;
      }
      if (loaded && playing?.status === 'playing' && !sentPaint.has(cycle)) {
        sentPaint.add(cycle);
        void request('/metrics', { event: 'patient_avatar_first_frame', role: 'patient', playback_id: playing.id, painted_at_ms: Date.now() }).catch(() => undefined);
      }
    };
    animate();
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      if (vrm) {
        VRMUtils.deepDispose(vrm.scene);
        for (const material of vrm.materials ?? []) material.dispose();
      }
      renderer.dispose();
      renderer.domElement.removeEventListener('webglcontextlost', loseContext);
      renderer.domElement.removeEventListener('webglcontextrestored', restoreContext);
      renderer.domElement.remove();
    };
  }, [bootstrap]);

  return <div className="avatar-stage" data-testid="avatar-stage">
    <div ref={host} className="avatar-canvas" />
    {(!ready || failure) && <div className="avatar-loading">{failure ? <span role="alert">{failure}</span> : <><LoaderCircle size={28} /><span>Đang chuẩn bị người hướng dẫn…</span></>}</div>}
    <div className="avatar-stage-top"><span className="eyebrow">LỜI BÁC SĨ QUA KÝ HIỆU</span><span className="soft-tag">Hướng dẫn trực quan</span></div>
    <div className="avatar-stage-tools">
      <button className={`icon-button ${zoom ? 'selected' : ''}`} onClick={() => setZoom(!zoom)} title={zoom ? 'Xem toàn bộ cử động' : 'Xem gần bàn tay'} aria-label={zoom ? 'Xem toàn bộ cử động' : 'Xem gần bàn tay'}><Maximize2 size={19} /></button>
    </div>
    <div className="avatar-caption"><span className={`status-dot ${playback?.status === 'playing' ? 'active' : ''}`} />{label ? `${label} · ${activeIndex + 1}/${playback?.glosses.length}` : (playback?.status === 'loading' ? 'Đang chuẩn bị ký hiệu' : 'Sẵn sàng lắng nghe bác sĩ')}</div>
    {playback && <div className="sign-sequence" aria-label="Thứ tự ký hiệu" data-testid="sign-sequence">{playback.glosses.map((gloss, index) => <span key={`${index}-${gloss.id}`} className={index === activeIndex ? 'current' : index < activeIndex ? 'done' : ''} aria-current={index === activeIndex ? 'step' : undefined}>{index + 1}. {gloss.label}</span>)}</div>}
    <div className="avatar-progress"><div style={{ width: `${progress * 100}%` }} /></div>
  </div>;
}
