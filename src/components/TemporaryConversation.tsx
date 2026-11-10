import { useEffect, useState } from 'react';
import { request } from '../api';
import type { TemporaryConversation as SavedConversation } from '../types';
import type { RunAction } from './SourcePanel';
import { Conversation } from './Shared';
import { Dialog } from './Dialog';

export function TemporaryConversation({ id, onClose, run }: { id: string; onClose: () => void; run: RunAction }) {
  const [saved, setSaved] = useState<SavedConversation | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    void request<SavedConversation | null>('/session/temporary').then(value => {
      if (alive) {
        if (value?.id === id) setSaved(value);
        else setError('Bản tạm này không còn được lưu.');
      }
    }).catch((problem: Error) => { if (alive) setError(problem.message); });
    return () => { alive = false; };
  }, [id]);
  return <Dialog title="Cuộc trao đổi đã lưu tạm" onClose={onClose}>
    <p className="temporary-help">Chỉ để xem lại ở phía bác sĩ. Bản này tự mất khi đóng ứng dụng hoặc khi kết thúc một phiên khác.</p>
    {error ? <p role="alert">{error}</p> : !saved ? <p>Đang mở bản tạm…</p> : <>
      <div className="temporary-conversation"><Conversation messages={saved.messages} /></div>
      {saved.speech_drafts.length > 0 && <details className="temporary-drafts"><summary>{saved.speech_drafts.length} câu chưa gửi trong phiên này</summary>{saved.speech_drafts.map(draft => <p key={draft.id}>{draft.text}<small>Chưa gửi người bệnh</small></p>)}</details>}
      <button className="button secondary" onClick={() => void run(async () => { await request('/session/temporary/discard', {}); onClose(); })}>Xóa bản tạm</button>
    </>}
  </Dialog>;
}
