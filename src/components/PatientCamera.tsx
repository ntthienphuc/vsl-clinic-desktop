import { Camera } from 'lucide-react';
import { previewUrl } from '../api';
import type { Bootstrap, SessionState } from '../types';
import { RecognitionModePanel } from './RecognitionModePanel';
import type { RunAction } from './SourcePanel';

export function PatientCamera({ bootstrap, state, run, disabled }: { bootstrap: Bootstrap; state: SessionState; run: RunAction; disabled: boolean }) {
  const capture = state.capture;
  const active = ['starting', 'ready', 'tracking', 'no_person', 'signing'].includes(capture.status);
  const live = capture.source_kind === 'camera';
  const status = state.recognition?.switching ? 'Đang đổi chế độ nhận dạng…' : capture.quality_warning ? capture.quality_warning
    : capture.status === 'signing' ? 'Đang nhận ký hiệu của bạn'
    : capture.status === 'error' ? 'Nhờ bác sĩ kiểm tra camera'
      : capture.status === 'ended' ? 'Video mẫu đã kết thúc'
        : capture.status === 'starting' ? 'Đang mở hình ảnh của bạn…'
          : capture.status === 'no_person' ? 'Đưa mặt và hai tay vào khung hình'
            : active ? 'Bạn có thể trả lời bằng ký hiệu'
              : state.conversation.status === 'active' ? 'Bác sĩ sẽ mở hình ảnh cho bạn' : 'Chờ bác sĩ bắt đầu';
  return <section className="source-panel with-preview patient-passive-camera">
    <div className="section-heading"><span className="heading-icon"><Camera size={18} /></span><h3>Hình ảnh của bạn</h3><span className={`soft-tag ${active ? 'teal' : ''}`}>{active ? live ? 'Trực tiếp' : 'Video mẫu' : capture.status === 'ended' ? 'Đã hết video' : 'Đang chờ'}</span></div>
    <RecognitionModePanel bootstrap={bootstrap} state={state} run={run} disabled={disabled} />
      <div className={`camera-preview ${live ? 'mirrored' : ''}`}>
        {(capture.captured ?? 0) > 0 && active ? <img key={capture.generation} src={previewUrl} alt="Hình ảnh của bạn để thực hiện ký hiệu" /> : <div className="camera-placeholder"><Camera size={36} /><strong>{status}</strong></div>}
    </div>
    {active && <div className="patient-listening" role="status"><span className="status-dot active" />{status}</div>}
    {state.current_result && <p className="patient-recognized" aria-live="polite">{state.current_result.uncertain ? 'Chưa nhận rõ: ' : 'Bạn vừa ký: '}<strong>{state.current_result.text}</strong>{state.current_result.uncertain && ' · Nhờ bác sĩ kiểm tra'}</p>}
    <p className="capture-help">Ký từng từ, hạ tay một nhịp giữa các từ.</p>
  </section>;
}
