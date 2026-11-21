import { t } from '../i18n';
import { useEffect, useRef, useState } from 'react';
import { CheckCircle2, CircleHelp, Hand, MessageSquareText, LayoutGrid, Send } from 'lucide-react';
import { request } from '../api';
import { PlaybackControls } from './Shared';
import { QuickPhrases } from './QuickPhrases';
import { LiveSpeechPanel } from '../speech/LiveSpeechPanel';
import type { RunAction } from './SourcePanel';
import type { Bootstrap, SessionState, TextPlan } from '../types';

export function Composer({ bootstrap, state, connected, run, busy, insertion }: { bootstrap: Bootstrap; state: SessionState; connected: boolean; run: RunAction; busy: boolean; insertion?: { text: string; nonce: number; sessionId: string } | null }) {
  const [text, setText] = useState('');
  const [mode, setMode] = useState<'sign' | 'text'>('sign');
  const [library, setLibrary] = useState(false);
  const input = useRef<HTMLTextAreaElement>(null);
  const quickSending = useRef(false);
  const restoreComposerFocus = () => requestAnimationFrame(() => input.current?.focus());
  const [plan, setPlan] = useState<TextPlan | null>(null);
  const [planning, setPlanning] = useState(false);
  const [planError, setPlanError] = useState('');
  useEffect(() => {
    if (!insertion || insertion.sessionId !== state.session_id) return;
    setMode('sign'); setText(previous => `${previous.trim()} ${insertion.text}`.trim().slice(0, 500));
    restoreComposerFocus();
  }, [insertion]);
  useEffect(() => {
    let valid = true;
    setPlan(null);
    setPlanError('');
    if (!text.trim()) {
      setPlanning(false);
      return;
    }
    setPlanning(true);
    const timer = setTimeout(() => {
      void (async () => {
        for (let attempt = 0; valid && attempt < 12; attempt += 1) {
          const value = await request<TextPlan>('/text/plan', { text, mode });
          if (!valid) return;
          setPlan(value);
          if (!value.language_assist?.busy) return;
          await new Promise((resolve) => setTimeout(resolve, 600));
        }
      })().catch((error: Error) => {
        if (valid) {
          setPlanError(error.message);
        }
      }).finally(() => {
        if (valid) {
          setPlanning(false);
        }
      });
    }, 450);
    return () => {
      valid = false;
      clearTimeout(timer);
    };
  }, [text, mode]);
  useEffect(() => {
    setText('');
  }, [state.session_id]);
  const canSend = connected && !busy && !!text.trim() && (mode === 'text' || (!planning && !!plan?.supported && plan.text === text.trim()));
  const send = () => {
    if (!canSend) {
      return;
    }
    void run(async () => {
      await request('/messages', { text, mode });
      setText('');
    });
  };
  const sendQuickPhrase = (value: string, supported: boolean) => {
    if (!connected || busy || quickSending.current) return;
    quickSending.current = true;
    void run(async () => {
      try {
        await request('/messages', { text: value, mode: supported ? 'sign' : 'text' });
        setLibrary(false);
        restoreComposerFocus();
      } finally {
        quickSending.current = false;
      }
    });
  };
  return <section className="composer-card" aria-label={t('Nói với người bệnh')}>
    <LiveSpeechPanel state={state} available={bootstrap.speech.available} connected={connected} run={run} />
    <div className="composer-body">
    <div className="composer-toolbar">
      <div className="composer-modes segmented" aria-label={t('Cách gửi nội dung')}>
        <button className={mode === 'sign' ? 'selected' : ''} aria-pressed={mode === 'sign'} onClick={() => setMode('sign')}><Hand size={15} />{t('Ký hiệu')}</button>
        <button className={mode === 'text' ? 'selected' : ''} aria-pressed={mode === 'text'} onClick={() => setMode('text')}><MessageSquareText size={15} />{t('Chỉ gửi chữ')}</button>
      </div>
      <div className="quick-phrases">
        <button className="library-trigger" onClick={() => setLibrary(true)} aria-haspopup="dialog"><LayoutGrid size={16}/>{t('Câu mẫu')}</button>
      </div>
    </div>
    <div className="quick-send-row" role="group" aria-label={t('Gửi nhanh')}>
      <span>{t('Gửi nhanh')}</span>
      {['ask-pain', 'nurse-temperature', 'sit-rest'].map(id => {
        const phrase = bootstrap.quick_phrases?.find(item => item.id === id);
        return phrase && <button key={id} disabled={!connected || busy} onClick={() => sendQuickPhrase(phrase.text, phrase.supported)}>{phrase.text}</button>;
      })}
    </div>
    <label className="composer-label sr-only" htmlFor="doctor-message-input">{t("Nhập lời bác sĩ")}</label>
    <div className="composer-input">
      <textarea ref={input} id="doctor-message-input" name="doctor-message" aria-label={t("Nội dung gửi người bệnh")} placeholder={mode === 'sign' ? t("Nhập câu, ví dụ: Bạn có đau không?") : t("Nhập nội dung cần trao đổi…")} maxLength={500} value={text} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
          event.preventDefault();
          send();
        }
      }} />
      <span className="character-count">{text.length > 0 ? `${text.length}/500` : t("Ctrl + Enter để gửi")}</span>
    </div>
    {mode === 'sign' && text.trim() && <div className={`plan-status ${plan && !plan.supported ? 'warning' : ''}`} aria-live="polite">
      {planning ? t("Đang chuẩn bị ký hiệu…") : planError ? t(planError) : plan?.supported ? <><CheckCircle2 size={15} /><span>{t("Sẵn sàng gửi bằng chữ và ký hiệu.")}</span></> : plan ? <><CircleHelp size={16} /><span>{t(plan.message)}{!!plan.unsupported.length && <> {t(" Chưa thể hiện đầy đủ: ")}<strong>{[...new Set(plan.unsupported.map((item) => item.text))].join(', ')}</strong>.</>}</span></> : null}
    </div>}
    {mode === 'sign' && !!plan?.suggestions.length && <div className="suggestion-panel"><strong>{t("Cách nói gần nghĩa — chỉ chọn nếu đúng ý bạn")}</strong>{plan.suggestions.map((item) => <button className="word-chip" key={item.text} title={t(item.reason)} onClick={() => setText(item.text)}>{item.text}</button>)}</div>}
    </div>
    <div className="composer-actions"><span>{mode === 'sign' ? t("Chữ và ký hiệu") : t("Gửi nguyên văn bằng chữ")}</span><button className="button primary" disabled={!canSend} aria-busy={busy} onClick={send}>{busy ? t("Đang gửi…") : t("Gửi")}<Send size={17} /></button></div>
    <PlaybackControls playback={state.playback} pending={state.pending_count} run={run} />
    {library && <QuickPhrases phrases={bootstrap.quick_phrases ?? []} disabled={!connected || busy} onClose={() => setLibrary(false)} onChoose={sendQuickPhrase}/>}
  </section>;
}
