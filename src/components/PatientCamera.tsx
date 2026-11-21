import { t } from '../i18n';
import { Camera } from 'lucide-react';
import { previewUrl } from '../api';
import type { SessionState } from '../types';

export function PatientCamera({ state }: { state: SessionState }) {
  const capture = state.capture;
  const active = ['starting', 'ready', 'tracking', 'no_person', 'signing'].includes(capture.status);
  const live = capture.source_kind === 'camera';
  const status = state.recognition?.switching ? 'Đang đổi chế độ nhận dạng…'
    : capture.status === 'signing' ? 'Đang nhận ký hiệu của bạn'
    : capture.status === 'error' ? 'Nhờ bác sĩ kiểm tra camera'
      : capture.status === 'ended' ? 'Video mẫu đã kết thúc'
        : capture.status === 'starting' ? 'Đang mở hình ảnh của bạn…'
          : capture.status === 'no_person' ? 'Đưa mặt và hai tay vào khung hình'
            : active ? 'Bạn có thể trả lời bằng ký hiệu'
              : state.conversation.status === 'active' ? 'Bác sĩ sẽ mở hình ảnh cho bạn' : 'Chờ bác sĩ bắt đầu';
  return <section className="source-panel with-preview patient-passive-camera">
    <div className="section-heading"><span className="heading-icon"><Camera size={18} /></span><h3>{t("Hình ảnh của bạn")}</h3><span className={`soft-tag ${active ? 'teal' : ''}`}>{active ? live ? t("Trực tiếp") : t("Video mẫu") : capture.status === 'ended' ? t("Đã hết video") : t("Đang chờ")}</span></div>
      <div className={`camera-preview ${live ? 'mirrored' : ''}`}>
        {(capture.captured ?? 0) > 0 && active ? <img key={capture.generation} src={previewUrl} alt={t("Hình ảnh của bạn để thực hiện ký hiệu")} /> : <div className="camera-placeholder"><Camera size={36} /><strong>{t(status)}</strong></div>}
    </div>
    {active && <div className="patient-listening" role="status"><span className="status-dot active" />{t(status)}</div>}
    {state.current_result && <p className="patient-recognized" aria-live="polite">{t('Bạn vừa ký: ')}<strong>{state.current_result.text}</strong></p>}
    <p className="capture-help">{t("Ký từng từ, hạ tay một nhịp giữa các từ.")}</p>
  </section>;
}
