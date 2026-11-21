import { t } from '../i18n';
import { Play, Square } from 'lucide-react';
import { useEffect, useState } from 'react';
import { request } from '../api';
import type { SessionState } from '../types';
import type { RunAction } from './SourcePanel';

export function ConversationBar({ state, run, busy, connected }: { state: SessionState; run: RunAction; busy: boolean; connected: boolean }) {
  const active = state.conversation.status === 'active';
  const [transition, setTransition] = useState<'start' | 'stop' | null>(null);
  const [keepTemporary, setKeepTemporary] = useState(false);
  useEffect(() => setKeepTemporary(false), [state.session_id]);
  return <div className="conversation-bar">
    <span><i className={`status-dot ${active ? 'active' : ''}`} />{active ? state.conversation.mode === 'auto' ? t("Đang trao đổi · Lời nói tự gửi") : t("Đang trao đổi · Kiểm tra lời nói trước khi gửi") : t("Sẵn sàng bắt đầu")}</span>
    {active && <label className="keep-temporary" title={t("Giữ một bản để bác sĩ xem lại. Tự mất khi đóng ứng dụng.")}><input type="checkbox" checked={keepTemporary} disabled={busy} onChange={event => setKeepTemporary(event.target.checked)} /> {t(" Lưu tạm")}</label>}
    <button className={`button ${active ? 'secondary' : 'primary'} compact`} disabled={!connected || transition !== null || (!active && busy)} title={active ? t("Dừng camera, micro, avatar và dọn nội dung trên cả hai màn hình") : undefined} onClick={() => {
      setTransition(active ? 'stop' : 'start');
      void run(() => request(active ? '/conversation/stop' : '/conversation/start', active ? { keep_temporary: keepTemporary } : {})).finally(() => setTransition(null));
    }}>{active ? <Square size={16} /> : <Play size={16} />}{transition === 'start' ? t("Đang mở…") : transition === 'stop' ? t("Đang đóng…") : active ? t("Kết thúc") : t("Bắt đầu")}</button>
  </div>;
}
