import { Play, Square } from 'lucide-react';
import { request } from '../api';
import type { SessionState } from '../types';
import type { RunAction } from './SourcePanel';

export function ConversationBar({ state, run, busy, connected }: { state: SessionState; run: RunAction; busy: boolean; connected: boolean }) {
  const active = state.conversation.status === 'active';
  return <div className="conversation-bar">
    <div className="segmented" aria-label="Chế độ cuộc trao đổi">
      <button className={state.conversation.mode === 'auto' ? 'selected' : ''} disabled={busy} onClick={() => void run(() => request('/conversation/configure', { mode: 'auto' }))}>Tự động</button>
      <button className={state.conversation.mode === 'manual' ? 'selected' : ''} disabled={busy} onClick={() => void run(() => request('/conversation/configure', { mode: 'manual' }))}>Xác nhận trước khi gửi</button>
    </div>
    <span><i className={`status-dot ${active ? 'active' : ''}`} />{active ? 'Hai màn hình đang trao đổi' : 'Camera và micro chưa bật'}</span>
    <button className={`button ${active ? 'secondary' : 'primary'} compact`} disabled={busy || !connected} onClick={() => void run(() => request(active ? '/conversation/stop' : '/conversation/start', {}))}>{active ? <Square size={16} /> : <Play size={16} />}{active ? 'Kết thúc' : 'Bắt đầu cuộc trao đổi'}</button>
  </div>;
}
