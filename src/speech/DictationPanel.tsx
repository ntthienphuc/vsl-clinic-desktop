import { Check, Mic, Square, X } from 'lucide-react';
import { useEffect } from 'react';
import { useDictation } from './useDictation';

export function DictationPanel({ sessionId, available, onUse, onActive, remaining }: {
  sessionId: string;
  available: boolean;
  onUse: (text: string) => void;
  onActive: (active: boolean) => void;
  remaining: number;
}) {
  const speech = useDictation(sessionId);
  useEffect(() => onActive(speech.active), [speech.active, onActive]);
  const status = speech.phase === 'loading' ? 'Đang chuẩn bị micro…'
    : speech.phase === 'permission' ? 'Đang mở micro…'
    : speech.phase === 'finishing' ? 'Đang nhận nốt lời nói…'
      : speech.phase === 'listening' ? `Đang nghe · ${speech.seconds}s`
        : 'Nói tiếng Việt';
  return <div className={`dictation-panel ${speech.active ? 'recording' : ''}`}>
    <div className="dictation-toolbar">
      <button className="button subtle compact" disabled={!available || speech.active} onClick={() => void speech.start()}><Mic size={17} />{speech.active ? status : 'Nói tiếng Việt'}</button>
      {speech.active && <>
        <div className="audio-meter" aria-label="Mức âm thanh"><span style={{ width: `${speech.level * 100}%` }} /></div>
        <button className="button secondary compact" disabled={speech.phase !== 'listening'} onClick={speech.finish}><Square size={13} /> Dừng</button>
        <button className="icon-button" aria-label="Hủy nhận giọng nói" onClick={() => speech.cancel(true)}><X size={17} /></button>
      </>}
      {!speech.active && speech.devices.length > 1 && <select aria-label="Chọn micro" value={speech.deviceId} onChange={(event) => speech.setDeviceId(event.target.value)}><option value="">Micro mặc định</option>{speech.devices.map((device) => <option key={device.deviceId} value={device.deviceId}>{device.label || 'Micro'}</option>)}</select>}
    </div>
    <p className="dictation-help">{!available ? 'Bộ giọng nói chưa có trên máy.' : speech.phase === 'permission' ? 'Cho phép ứng dụng dùng micro nếu có hộp thoại yêu cầu. Bạn có thể hủy bằng nút ×.' : speech.active ? 'Nói từng ý ngắn và ngắt một nhịp. Micro chỉ nghe khi nút này đang bật.' : 'Lời nói được xử lý trên máy. Kiểm tra phần chữ trước khi gửi.'}</p>
    {speech.error && <p className="inline-error" role="alert">{speech.error}</p>}
    {(speech.draft || speech.decoding || speech.phase === 'finishing') && <div className="dictation-review">
      <label htmlFor="speech-draft">Lời nói vừa nhận {speech.decoding && <span>· Đang nhận ý tiếp theo…</span>}</label>
      <textarea id="speech-draft" value={speech.draft} disabled={speech.active} onChange={(event) => speech.setDraft(event.target.value)} placeholder="Bản chữ xuất hiện sau mỗi lần ngắt lời…" />
      {speech.uncertain && <p className="review-note">Có đoạn chưa nghe rõ hoặc ý nói dài. Vui lòng kiểm tra lại nội dung.</p>}
      <div className="dictation-actions"><small>{speech.latency !== null ? `Ý vừa nhận: ${(speech.latency / 1000).toFixed(1)} giây sau khi ngắt lời` : 'Có thể sửa lại phần chữ khi dừng micro.'}</small><button className="button subtle compact" disabled={speech.active || !speech.draft.trim() || speech.draft.trim().length > remaining} onClick={() => {
        onUse(speech.draft.trim());
        speech.setDraft('');
      }}><Check size={15} /> Dùng nội dung này</button></div>
      {speech.draft.trim().length > remaining && <p className="inline-error">Nội dung vượt quá chỗ còn lại. Hãy chia thành các ý ngắn trước khi gửi.</p>}
    </div>}
  </div>;
}
