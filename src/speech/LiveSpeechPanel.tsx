import { t } from '../i18n';
import { useEffect, useRef, useState } from 'react';
import { Check, Mic, MicOff, Send, X } from 'lucide-react';
import { request } from '../api';
import { useDictation } from './useDictation';
import { Dialog } from '../components/Dialog';
import type { SessionState, SpeechDraft } from '../types';
import type { RunAction } from '../components/SourcePanel';

function Review({ draft, initialText, run, canRetry, onRetry, onDone }: { draft: SpeechDraft; initialText?: string; run: RunAction; canRetry: boolean; onRetry: () => void; onDone: () => void }) {
  const [text, setText] = useState(initialText ?? draft.text);
  const [sending, setSending] = useState(false);
  const needsRetry = draft.reason_code === 'unsupported' || draft.reason_code === 'unclear';
  const send = (mode: 'sign' | 'text') => {
    if (sending) {
      return;
    }
    setSending(true);
    void run(async () => { await request('/speech/review', { draft_id: draft.id, text, mode }); onDone(); }).finally(() => setSending(false));
  };
  return <div className="speech-review-item">
    {needsRetry && <div className="speech-warning" role="alert">
      <strong>{draft.reason_code === 'unsupported' ? t("Câu này cần bạn kiểm tra") : t("Chưa nghe rõ câu này")}</strong>
      <span>{t(draft.reason)}</span>
    </div>}
    <textarea aria-label={t("Sửa lời nói trước khi gửi")} value={text} onChange={(event) => setText(event.target.value)} maxLength={500} />
    {needsRetry && !!draft.suggestions?.length && <div className="suggestion-panel"><strong>{t("Có phải ý bạn là:")}</strong>{draft.suggestions.map((item) => <button key={item.text} className="word-chip" disabled={sending} onClick={() => setText(item.text)}>{item.text}</button>)}</div>}
    {!needsRetry && <small>{t(draft.reason)}</small>}
    <div className="speech-review-actions">
      {needsRetry && <button className="button primary compact" disabled={sending || !canRetry} onClick={() => {
        setSending(true);
        void run(async () => {
          await request('/speech/review', { draft_id: draft.id });
          onRetry();
          onDone();
        }).finally(() => setSending(false));
      }}><Mic size={14} /> {t(" Nói lại")}</button>}
      <button className={`button ${needsRetry ? 'secondary' : 'primary'} compact`} disabled={sending || !text.trim() || (!draft.supported && text === draft.text)} onClick={() => send('sign')}><Check size={14} /> {t(" Gửi ký hiệu")}</button>
      <button className="text-button" disabled={sending || !text.trim()} onClick={() => send('text')}><Send size={14} /> {t(" Gửi chữ")}</button>
      <button className="icon-button" aria-label={t("Bỏ câu vừa nhận")} disabled={sending} onClick={() => void run(async () => { await request('/speech/review', { draft_id: draft.id }); onDone(); })}><X size={16} /></button>
    </div>
  </div>;
}

export function LiveSpeechPanel({ state, available, connected, run }: { state: SessionState; available: boolean; connected: boolean; run: RunAction }) {
  const context = `${state.session_id}:${state.conversation.epoch}`;
  const speech = useDictation(context, true);
  const attempted = useRef('');
  const [userMuted, setUserMuted] = useState(false);
  useEffect(() => setUserMuted(false), [context]);
  const [selectedId, setSelectedId] = useState('');
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewText, setReviewText] = useState<string>();
  const latestId = state.speech_drafts.at(-1)?.id ?? '';
  useEffect(() => { if (!reviewOpen) setSelectedId(latestId); }, [latestId, reviewOpen]);
  const selected = state.speech_drafts.find((draft) => draft.id === selectedId) ?? state.speech_drafts.at(-1);
  const enabled = state.conversation.status === 'active' && connected && available;
  useEffect(() => {
    if (!enabled || userMuted) {
      speech.cancel(true);
      attempted.current = '';
      return;
    }
    if (attempted.current !== context) {
      attempted.current = context;
      void speech.start();
    }
  }, [context, enabled, userMuted, speech.start, speech.cancel]);
  return <div className={`live-speech ${speech.active ? 'recording' : ''}`}>
    <div className="live-speech-status">
      {speech.active ? <Mic size={19} /> : <MicOff size={19} />}
      <strong>{!connected ? t('Đang kết nối lại…') : !available ? t('Chưa dùng được micro · Bạn vẫn có thể nhập chữ') : !enabled ? t("Bắt đầu để nói bằng micro") : speech.phase === 'listening' ? t("Đang nghe bác sĩ") : speech.phase === 'permission' ? t("Cho phép micro để nói") : speech.active ? t("Đang mở micro…") : t("Micro đang tắt")}</strong>
      {speech.active && <div className="audio-meter" aria-label={t("Mức âm thanh")}><span style={{ width: `${speech.level * 100}%` }} /></div>}
      {enabled && <button className="text-button" onClick={() => {
        if (speech.active) { setUserMuted(true); speech.cancel(true); }
        else { setUserMuted(false); void speech.start(); }
      }}>{speech.active ? t("Tắt micro") : t("Bật micro")}</button>}
    </div>
    <p className="speech-instruction">{state.conversation.mode === 'auto' ? t("Nói từng câu ngắn rồi nghỉ. Câu nghe rõ và đủ ký hiệu sẽ tự gửi.") : t("Nói từng câu ngắn, kiểm tra rồi gửi.")}</p>
    {speech.error && <div className="inline-error" role="alert">{t(speech.error)}</div>}
    {speech.notice && <div className="speech-warning" role="status">{t(speech.notice)}</div>}
    {speech.decoding && <small role="status">{t("Đang nhận câu vừa nói…")}</small>}
    {speech.draft && speech.delivery === 'sent' && <div className="speech-last" role="status">{t("Đã gửi người bệnh: ")}{speech.draft}</div>}
    {selected && <section className="speech-drafts compact-drafts" aria-label={t("Lời nói chưa gửi")}>
      <button className="draft-summary" onClick={() => { setReviewText(undefined); setReviewOpen(true); }}><strong>{state.speech_drafts.length} {t(" câu chưa gửi · Kiểm tra")}</strong><span>{selected.text}</span><small>{selected.reason_code === 'unsupported' ? t("Bạn có thể nói lại bằng một ý ngắn hoặc chọn gợi ý gần nghĩa.") : selected.reason_code === 'unclear' ? t("Có phần chưa nghe rõ") : t("Chờ bạn xác nhận")}</small></button>
      {(selected.reason_code === 'unsupported' || selected.reason_code === 'unclear') && <div className="speech-retry-prompt" role="status">
        {selected.language_assist_busy && <span>{t('Đang tìm câu có sẵn gần ý bạn…')}</span>}
        {!selected.language_assist_busy && selected.reason_code === 'unsupported' && !selected.suggestions?.length && <span>{t('Chưa có câu đủ gần nghĩa. Bạn có thể nói lại hoặc gửi chữ.')}</span>}
        <div className="speech-retry-actions"><button className="text-button" disabled={!enabled} onClick={() => void run(async () => {
          await request('/speech/review', { draft_id: selected.id });
          speech.setDraft(''); setUserMuted(false); if (!speech.active) void speech.start();
        })}><Mic size={14}/>{t('Nói lại')}</button><button className="text-button" onClick={() => { setReviewText(undefined); setReviewOpen(true); }}>{t('Sửa hoặc gửi chữ')}</button></div>
        {!!selected.suggestions?.length && <div className="speech-nearby-phrases"><strong>{t('Gợi ý gần nghĩa · Chọn nếu đúng ý')}</strong>{selected.suggestions.map(item => <button className="word-chip" key={item.text} onClick={() => { setReviewText(item.text); setReviewOpen(true); }}>{item.text}</button>)}</div>}
      </div>}
    </section>}
    {selected && reviewOpen && <Dialog title={t("Kiểm tra lời nói chưa gửi")} onClose={() => setReviewOpen(false)}>
      <div className="speech-review-heading">
        <strong>{state.speech_drafts.length} {t(" câu chưa gửi")}</strong>
        {state.speech_drafts.length > 1 && <select aria-label={t("Chọn câu cần kiểm tra")} value={selected.id} onChange={(event) => setSelectedId(event.target.value)}>
          {state.speech_drafts.map((draft, index) => <option value={draft.id} key={draft.id}>{index + 1}. {draft.text.slice(0, 60)}</option>)}
        </select>}
      </div>
      <Review key={selected.id + ':' + (reviewText ?? '')} draft={selected} initialText={reviewText} run={run} canRetry={enabled} onRetry={() => {
        speech.setDraft('');
        setUserMuted(false);
        if (!speech.active) {
          void speech.start();
        }
      }} onDone={() => setReviewOpen(false)} />
    </Dialog>}
  </div>;
}
