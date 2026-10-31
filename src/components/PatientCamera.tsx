import { Camera } from 'lucide-react';
import { previewUrl } from '../api';
import type { SessionState } from '../types';

export function PatientCamera({ state }: { state: SessionState }) {
  const capture = state.capture;
  const active = ['starting', 'ready', 'tracking', 'no_person', 'signing'].includes(capture.status);
  const live = capture.source_kind === 'camera';
  const status = capture.status === 'signing' ? 'Đang nhận ký hiệu của bạn'
    : capture.status === 'error' ? 'Nhờ bác sĩ kiểm tra camera'
      : capture.status === 'ended' ? 'Video mẫu đã kết thúc'
        : capture.status === 'starting' ? 'Đang mở hình ảnh của bạn…'
          : capture.status === 'no_person' ? 'Đưa mặt và hai tay vào hình'
            : active ? 'Bạn có thể trả lời bằng ký hiệu'
              : state.conversation.status === 'active' ? 'Bác sĩ sẽ mở hình ảnh cho bạn' : 'Chờ bác sĩ bắt đầu';
  return <section className="source-panel with-preview patient-passive-camera">
    <div className="section-heading"><span className="heading-icon"><Camera size={18} /></span><h3>Hình ảnh của bạn</h3><span className={`soft-tag ${active ? 'teal' : ''}`}>{active ? live ? 'Trực tiếp' : 'Video mẫu' : capture.status === 'ended' ? 'Đã hết video' : 'Đang chờ'}</span></div>
    <div className={`camera-preview ${live ? 'mirrored' : ''}`}>
      {(capture.captured ?? 0) > 0 && active ? <img key={capture.generation} src={previewUrl} alt="Hình ảnh của bạn để thực hiện ký hiệu" /> : <div className="camera-placeholder"><Camera size={36} /><strong>{status}</strong><span>Bạn không cần bấm để trả lời.</span></div>}
    </div>
    <div className="patient-listening" role="status"><span className={`status-dot ${active ? 'active' : ''}`} />{status}</div>
    <p className="capture-help">Ngắt nhẹ giữa các từ. Nghỉ lâu hơn khi nói xong một ý.</p>
  </section>;
}
