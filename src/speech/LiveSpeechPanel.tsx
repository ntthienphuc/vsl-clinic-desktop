import { useEffect, useRef, useState } from 'react';
import { Check, Mic, MicOff, Send, X } from 'lucide-react';
import { request } from '../api';
import { useDictation } from './useDictation';
import type { SessionState, SpeechDraft } from '../types';
import type { RunAction } from '../components/SourcePanel';

function Review({ draft, run, canRetry, onRetry }: { draft: SpeechDraft; run: RunAction; canRetry: boolean; onRetry: () => void }) {
  const [text, setText] = useState(draft.text);
  const [sending, setSending] = useState(false);
  const needsRetry = draft.reason_code === 'unsupported' || draft.reason_code === 'unclear';
  const send = (mode: 'sign' | 'text') => {
    if (sending) {
      return;
    }
    setSending(true);
    void run(() => request('/speech/review', { draft_id: draft.id, text, mode })).finally(() => setSending(false));
  };
  return <div className="speech-review-item">
    {needsRetry && <div className="speech-warning" role="alert">
      <strong>{draft.reason_code === 'unsupported' ? 'Câu này chưa gửi: thiếu ký hiệu hoặc mẫu câu' : 'Chưa nghe rõ câu này'}</strong>
      <span>{draft.reason}</span>
    </div>}
    <textarea aria-label="Sửa lời nói trước khi gửi" value={text} onChange={(event) => setText(event.target.value)} maxLength={500} />
    {!needsRetry && <small>{draft.reason}</small>}
    <div className="speech-review-actions">
      {needsRetry && <button className="button primary compact" disabled={sending || !canRetry} onClick={() => {
        setSending(true);
        void run(async () => {
          await request('/speech/review', { draft_id: draft.id });
          onRetry();
        }).finally(() => setSending(false));
      }}><Mic size={14} /> Nói lại</button>}
      <button className={`button ${needsRetry ? 'secondary' : 'primary'} compact`} disabled={sending || !text.trim() || (!draft.supported && text === draft.text)} onClick={() => send('sign')}><Check size={14} /> Gửi ký hiệu</button>
      <button className="text-button" disabled={sending || !text.trim()} onClick={() => send('text')}><Send size={14} /> Gửi chữ</button>
      <button className="icon-button" aria-label="Bỏ câu vừa nhận" disabled={sending} onClick={() => void run(() => request('/speech/review', { draft_id: draft.id }))}><X size={16} /></button>
    </div>
  </div>;
}

export function LiveSpeechPanel({ state, available, connected, run }: { state: SessionState; available: boolean; connected: boolean; run: RunAction }) {
  const context = `${state.session_id}:${state.conversation.epoch}`;
  const speech = useDictation(context, true);
  const attempted = useRef('');
  const [selectedId, setSelectedId] = useState('');
  const latestId = state.speech_drafts.at(-1)?.id ?? '';
  useEffect(() => setSelectedId(latestId), [latestId]);
  const selected = state.speech_drafts.find((draft) => draft.id === selectedId) ?? state.speech_drafts.at(-1);
  const enabled = state.conversation.status === 'active' && connected && available;
  useEffect(() => {
    if (!enabled) {
      speech.cancel(true);
      attempted.current = '';
      return;
    }
    if (attempted.current !== context) {
      attempted.current = context;
      void speech.start();
    }
  }, [context, enabled, speech.start, speech.cancel]);
  return <div className={`live-speech ${speech.active ? 'recording' : ''}`}>
    <div className="live-speech-status">
      {speech.active ? <Mic size={19} /> : <MicOff size={19} />}
      <strong>{!enabled ? 'Micro bật khi bắt đầu cuộc trao đổi' : speech.phase === 'listening' ? 'Đang nghe bác sĩ' : speech.phase === 'permission' ? 'Cho phép micro để nói' : speech.active ? 'Đang mở micro…' : 'Micro đang tắt'}</strong>
      {speech.active && <div className="audio-meter" aria-label="Mức âm thanh"><span style={{ width: `${speech.level * 100}%` }} /></div>}
      {enabled && <button className="text-button" onClick={() => speech.active ? speech.cancel(true) : void speech.start()}>{speech.active ? 'Tắt micro' : 'Bật micro'}</button>}
    </div>
    <p>{state.conversation.mode === 'auto' ? 'Nói một câu rồi nghỉ khoảng nửa giây: câu đủ ký hiệu tự gửi. Có cảnh báo thì nói lại hoặc sửa câu.' : 'Nói từng ý ngắn. Mỗi câu sẽ chờ bạn xác nhận trước khi gửi.'}</p>
    {speech.error && <div className="inline-error" role="alert">{speech.error}</div>}
    {speech.notice && <div className="speech-warning" role="status">{speech.notice}</div>}
    {speech.decoding && <small role="status">Đang nhận câu vừa nói…</small>}
    {speech.draft && speech.delivery === 'sent' && <div className="speech-last" role="status">Đã gửi người bệnh: {speech.draft}</div>}
    {selected && <section className="speech-drafts" aria-label="Lời nói chưa gửi">
      <div className="speech-review-heading">
        <strong>{state.speech_drafts.length} câu chưa gửi</strong>
        {state.speech_drafts.length > 1 && <select aria-label="Chọn câu cần kiểm tra" value={selected.id} onChange={(event) => setSelectedId(event.target.value)}>
          {state.speech_drafts.map((draft, index) => <option value={draft.id} key={draft.id}>{index + 1}. {draft.text.slice(0, 60)}</option>)}
        </select>}
      </div>
      <Review key={selected.id} draft={selected} run={run} canRetry={enabled} onRetry={() => {
        speech.setDraft('');
        if (!speech.active) {
          void speech.start();
        }
      }} />
    </section>}
  </div>;
}
