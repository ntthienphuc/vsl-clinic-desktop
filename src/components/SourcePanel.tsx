import { useRef, useState } from 'react';
import { Camera, FileVideo, Play, Settings2, Square, Upload, VideoOff } from 'lucide-react';
import { Dialog } from './Dialog';
import { previewUrl, request, uploadVideo } from '../api';
import type { CaptureState, ConversationSettings, Word } from '../types';

export type RunAction = (action: () => Promise<unknown>) => Promise<void>;

export function SourcePanel({ words, capture, run, busy, showPreview = false, conversation }: {
  words: Word[];
  capture: CaptureState;
  run: RunAction;
  busy: boolean;
  showPreview?: boolean;
  conversation?: ConversationSettings;
}) {
  const [source, setSource] = useState(conversation?.source.kind ?? 'demo');
  const demos = words.filter((item) => item.model_id !== null && item.demo);
  const [word, setWord] = useState(conversation?.source.demo_id ?? demos[0]?.id ?? '');
  const [camera, setCamera] = useState(conversation?.source.camera_index ?? 0);
  const configure = (kind: 'camera' | 'demo', demoId = word, cameraIndex = camera) => {
    setSource(kind);
    setWord(demoId);
    setCamera(cameraIndex);
    if (conversation) {
      void run(() => request('/conversation/configure', { mode: conversation.mode, source: { kind, demo_id: demoId, camera_index: cameraIndex } }));
    }
  };
  const [settingsOpen, setSettingsOpen] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const active = ['starting', 'ready', 'tracking', 'no_person', 'signing'].includes(capture.status);
  const hasFrame = (capture.captured ?? 0) > 0;
  const liveCamera = active && capture.source_kind === 'camera';
  const start = () => run(() => request('/capture/start', source === 'demo'
    ? { kind: 'demo', demo_id: word }
    : { kind: 'camera', camera_index: camera }));

  const controls = <div className="source-options">
      <div className="segmented" aria-label="Loại nguồn hình ảnh">
        <button disabled={busy} className={source === 'demo' ? 'selected' : ''} onClick={() => configure('demo')}><FileVideo size={15} /> Video mẫu</button>
        <button disabled={busy} className={source === 'camera' ? 'selected' : ''} onClick={() => configure('camera')}><Camera size={15} /> Camera</button>
      </div>
      <div className="source-select">
        {source === 'demo'
          ? <select disabled={busy} aria-label="Chọn video mẫu" value={word} onChange={(event) => configure(source, event.target.value)}>{demos.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select>
          : <select disabled={busy} aria-label="Chọn camera" value={camera} onChange={(event) => configure(source, word, Number(event.target.value))}>{[0, 1, 2, 3].map((index) => <option key={index} value={index}>Camera {index + 1}{index === 0 ? ' · mặc định' : ''}</option>)}</select>}
        <button className="button primary compact" disabled={busy} onClick={() => void start()}><Play size={15} fill="currentColor" />{active ? 'Phát lại' : 'Bắt đầu'}</button>
        {active && <button className="icon-button stop" disabled={busy} aria-label="Dừng nhận dạng" title="Dừng nhận dạng" onClick={() => void run(() => request('/capture/stop', {}))}><Square size={16} fill="currentColor" /></button>}
      </div>
      <input ref={fileInput} type="file" accept=".mp4,.mov,.avi,.mkv" className="visually-hidden" aria-label="Tệp video nhận dạng" onChange={(event) => {
        const file = event.target.files?.[0];
        if (file) {
          void run(() => uploadVideo(file));
        }
        event.target.value = '';
      }} />
      <button className="text-button upload-button" disabled={busy} onClick={() => fileInput.current?.click()}><Upload size={14} /> Mở video trên máy <span>MP4 · tối đa 3 phút</span></button>
    </div>;
  return <section className={showPreview ? 'source-panel with-preview' : 'source-panel'}>
    <div className="section-heading">
      <span className="heading-icon"><Camera size={18} /></span>
      <div><h3>{showPreview ? 'Hình ảnh của bạn' : 'Camera và video mẫu'}</h3></div>
      <span className={active ? 'soft-tag teal' : 'soft-tag'}>{liveCamera ? 'Trực tiếp' : active ? 'Video mẫu' : capture.status === 'ended' ? 'Đã hết video' : 'Chưa phát'}</span>
    </div>
    {showPreview && <>
      <div className={liveCamera ? 'camera-preview mirrored' : 'camera-preview'}>
        {hasFrame && active
          ? <img key={capture.generation} src={previewUrl} alt={liveCamera ? 'Hình ảnh camera của bạn' : 'Video đang được nhận dạng theo thời gian thực'} />
          : <div className="camera-placeholder"><Camera size={38} strokeWidth={1.3} /><strong>{capture.status === 'ended' ? 'Video đã phát xong' : 'Giữ mặt và hai tay trong hình'}</strong><span>{capture.status === 'ended' ? 'Chọn video khác hoặc bấm Bắt đầu để phát lại.' : 'Bấm Bắt đầu khi bạn sẵn sàng.'}</span></div>}
        {hasFrame && active && <span className="preview-source">{liveCamera ? 'Camera · xem như gương' : 'Video mẫu · tốc độ gốc'}</span>}
      </div>
      <div className="capture-toolbar">
        <button className="button primary" disabled={busy} onClick={() => void (active ? run(() => request('/capture/stop', {})) : start())}>
          {active ? <Square size={17} /> : <Play size={17} />}{active ? 'Dừng nhận dạng' : 'Bắt đầu'}
        </button>
        <button className="button secondary" onClick={() => setSettingsOpen(true)}><Settings2 size={17} /> Camera / video</button>
      </div>
      <p className="capture-help">Hạ tay một nhịp sau mỗi ký hiệu.</p>
      {settingsOpen && <Dialog title="Chọn camera hoặc video" onClose={() => setSettingsOpen(false)}>{controls}</Dialog>}
    </>}
    {!showPreview && controls}
    {capture.status === 'error' && <div className="inline-error"><VideoOff size={16} />{capture.message || 'Chưa mở được nguồn hình ảnh. Hãy thử video mẫu.'}</div>}
    {active && <div className="tracking-note"><span className={capture.has_pose ? 'status-dot active' : 'status-dot amber'} />{capture.status === 'starting' ? 'Đang mở nguồn hình ảnh…' : capture.has_pose ? `Đã thấy người · ${capture.hand_count ?? 0} bàn tay` : 'Đưa mặt, vai và hai bàn tay vào khung hình.'}</div>}
  </section>;
}
