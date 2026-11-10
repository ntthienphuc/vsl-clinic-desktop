import { Play, Square } from 'lucide-react';
import { useEffect, useState } from 'react';
import { request } from '../api';
import type { SessionState } from '../types';
import type { RunAction } from './SourcePanel';

export function ConversationBar({ state, run, busy, connected }: { state: SessionState; run: RunAction; busy: boolean; connected: boolean }) {
  const active = state.conversation.status === 'active';
  const [keepTemporary, setKeepTemporary] = useState(false);
  useEffect(() => setKeepTemporary(false), [state.session_id]);
  return <div className="conversation-bar">
    <span><i className={`status-dot ${active ? 'active' : ''}`} />{active ? state.conversation.mode === 'auto' ? 'Đang trao đổi · Lời nói tự gửi' : 'Đang trao đổi · Kiểm tra lời nói trước khi gửi' : 'Bấm Bắt đầu để mở camera và micro'}</span>
    {active && <label className="keep-temporary" title="Giữ một bản để bác sĩ xem lại. Tự mất khi đóng ứng dụng."><input type="checkbox" checked={keepTemporary} disabled={busy} onChange={event => setKeepTemporary(event.target.checked)} /> Lưu tạm</label>}
    <button className={`button ${active ? 'secondary' : 'primary'} compact`} disabled={!connected || (!active && busy)} title={active ? 'Dừng camera, micro, avatar và dọn nội dung trên cả hai màn hình' : undefined} onClick={() => void run(() => request(active ? '/conversation/stop' : '/conversation/start', active ? { keep_temporary: keepTemporary } : {}))}>{active ? <Square size={16} /> : <Play size={16} />}{active ? 'Kết thúc' : 'Bắt đầu cuộc trao đổi'}</button>
  </div>;
}
