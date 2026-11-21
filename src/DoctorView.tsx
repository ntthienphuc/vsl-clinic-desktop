import { t } from './i18n';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowDownLeft, BookOpen, Hand, History, MessageSquare, Settings2, Volume2, VolumeX } from 'lucide-react';
import { request } from './api';
import { Conversation, Diagnostics } from './components/Shared';
import { SourcePanel, type RunAction } from './components/SourcePanel';
import { RecognitionModePanel } from './components/RecognitionModePanel';
import { Composer } from './components/Composer';
import { usePatientVoice } from './speech/usePatientVoice';
import { ConversationBar } from './components/ConversationBar';
import { Dialog } from './components/Dialog';
import { AvatarProgress } from './components/AvatarProgress';
import { TemporaryConversation } from './components/TemporaryConversation';
import { PatientWordResult } from './components/PatientWordResult';
import type { Bootstrap, SessionState } from './types';
import { SignDictionary } from './components/SignDictionary';

function RecognitionCard({ state, connected }: { state: SessionState; connected: boolean }) {
  const voice = usePatientVoice(state, connected);
  const captureError = state.capture.status === 'error';
  const result = state.current_result;
  const turn = state.patient_turn ?? [...state.messages].reverse().find(item => item.kind === 'patient_turn');
  const liveWords = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = liveWords.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [turn?.id, turn?.words?.length]);
  return <section className="recognition-card">
    <div className="section-heading"><span className="heading-icon"><ArrowDownLeft size={19} /></span><div><h2>{t('Lời người bệnh')}</h2></div><button className="icon-button" aria-label={voice.enabled ? t('Tắt đọc ký hiệu') : t('Bật đọc ký hiệu')} aria-pressed={voice.enabled} title={voice.enabled ? t('Đang bật giọng đọc tiếng Việt') : t('Bật giọng đọc tiếng Việt')} onClick={voice.toggle}>{voice.enabled ? <Volume2 size={19} /> : <VolumeX size={19} />}</button></div>
    {voice.error ? <small className="patient-voice-error" role="alert">{t(voice.error)}</small> : voice.status && <small className="patient-voice-status" role="status">{t(voice.status)}</small>}
    {turn && <div className="live-patient-turn" data-testid="live-patient-turn" aria-live="polite">
      <span className="result-label">{turn.status === 'streaming' ? t('ĐANG NHẬN TỪNG TỪ') : t('LƯỢT VỪA KẾT THÚC')}</span>
      <div className="live-word-list ranked-word-list" ref={liveWords}>{turn.words?.map(word => <PatientWordResult key={word.id} word={word} />)}</div>
      {turn.status === 'streaming' ? <small>{state.capture.status === 'signing' ? t('Người bệnh đang tiếp tục…') : t('Đang chờ ý tiếp theo…')}</small> : <small>{t('Đã gom lượt vào nội dung trao đổi.')}</small>}
    </div>}
    {!turn && result && <PatientWordResult word={result} />}
    {!result && !turn && <div className="recognition-idle"><span className="idle-symbol"><Hand size={29} strokeWidth={1.4} /></span><strong>{captureError ? t('Chưa nhận được hình ảnh') : state.conversation.status === 'active' ? t('Đang theo dõi người bệnh') : t('Sẵn sàng lắng nghe')}</strong><p>{captureError ? t('Mở Tùy chọn để kiểm tra camera. Bạn vẫn có thể gửi chữ hoặc chọn câu mẫu.') : state.capture.status === 'no_person' ? t('Đưa mặt, vai và hai tay vào khung hình.') : t('Mỗi từ hiện ngay khi nhận xong. Nghỉ một nhịp dài để kết thúc lượt.')}</p></div>}
  </section>;
}


export function DoctorView({ bootstrap, state, connected, run, busy }: { bootstrap: Bootstrap; state: SessionState; connected: boolean; run: RunAction; busy: boolean }) {
  const [resetOpen, setResetOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(false);
  const [temporaryOpen, setTemporaryOpen] = useState(false);
  const [workspace, setWorkspace] = useState<'conversation' | 'dictionary'>('conversation');
  const [insertion, setInsertion] = useState<{ text: string; nonce: number; sessionId: string } | null>(null);
  const useDictionaryWord = useCallback((text: string) => { setInsertion({ text, nonce: Date.now(), sessionId: state.session_id }); setWorkspace('conversation'); }, [state.session_id]);
  useEffect(() => { setTemporaryOpen(false); setSourceOpen(false); setResetOpen(false); setInsertion(null); setWorkspace('conversation'); }, [state.session_id]);
  return <main className="doctor-page" id="clinic-workspace" tabIndex={-1}>
    <div className="workspace-toolbar">
      <div className="workspace-title"><h1>{t('Cuộc trao đổi')}</h1><p>{state.conversation.status === 'active' ? t('Nói, nhập chữ hoặc chọn câu mẫu.') : t('Bấm Bắt đầu để mở camera và micro.')}</p></div>
      <div className="workspace-tools">
        {state.temporary && <button className="icon-button" title={t('Xem lại bản tạm')} aria-label={t('Xem lại bản tạm')} onClick={() => setTemporaryOpen(true)}><History size={19} /></button>}
        <button className="icon-button settings-trigger" title={t('Camera và tùy chọn')} aria-label={t('Camera và tùy chọn')} onClick={() => setSourceOpen(true)}><Settings2 size={18} /><span>{t("Tùy chọn")}</span></button>
        <ConversationBar state={state} run={run} busy={busy} connected={connected} />
      </div>
    </div>
    <nav className="workspace-navigation" role="tablist" aria-label={t('Không gian bác sĩ')} onKeyDown={event => {
      if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
        event.preventDefault(); const next = event.key === 'Home' ? 'conversation' : event.key === 'End' ? 'dictionary' : workspace === 'conversation' ? 'dictionary' : 'conversation';
        setWorkspace(next); document.getElementById('workspace-tab-' + next)?.focus();
      }
    }}>
      <button role="tab" id="workspace-tab-conversation" aria-controls="conversation-panel" aria-selected={workspace === 'conversation'} tabIndex={workspace === 'conversation' ? 0 : -1} onClick={() => setWorkspace('conversation')}><MessageSquare size={17}/>{t('Cuộc trao đổi')}</button>
      <button role="tab" id="workspace-tab-dictionary" aria-controls="dictionary-panel" aria-selected={workspace === 'dictionary'} tabIndex={workspace === 'dictionary' ? 0 : -1} onClick={() => setWorkspace('dictionary')}><BookOpen size={17}/>{t('Từ điển ký hiệu')}</button>
    </nav>
    <div className="doctor-workspace" id="conversation-panel" role="tabpanel" aria-labelledby="workspace-tab-conversation" hidden={workspace !== 'conversation'}>
      <RecognitionCard state={state} connected={connected} />
      <section className="conversation-card" aria-label={t('Nội dung trao đổi')}>
        <Conversation messages={state.messages} />
        {state.clients.patient === 0 && <div className="conversation-footer"><span className="status-dot amber" />{t('Mở màn hình người bệnh để xem ký hiệu')}</div>}
      </section>
      <div className="playback-shelf"><AvatarProgress playback={state.playback} pending={state.pending_count} voiceEnabled={state.avatar_voice_enabled !== false} onVoiceToggle={() => void run(() => request('/avatar/voice', { enabled: state.avatar_voice_enabled === false }))} /></div>
      <Composer key={state.session_id} bootstrap={bootstrap} state={state} connected={connected} run={run} busy={busy} insertion={insertion} />
    </div>
    <div id="dictionary-panel" role="tabpanel" aria-labelledby="workspace-tab-dictionary" hidden={workspace !== 'dictionary'}>{workspace === 'dictionary' && <SignDictionary bootstrap={bootstrap} onUse={useDictionaryWord}/>}</div>
    {sourceOpen && <Dialog title={t("Camera và tùy chọn")} onClose={() => setSourceOpen(false)}>
      <label className="settings-voice-option"><input type="checkbox" checked={state.avatar_voice_enabled !== false} disabled={busy || !connected}
        onChange={event => void run(() => request('/avatar/voice', { enabled: event.target.checked }))} />{t('Đọc lời bác sĩ cùng ký hiệu')}</label>
      <label className="conversation-send-option">{t("Gửi lời nói của bác sĩ ")}<select aria-label={t("Gửi lời nói của bác sĩ")} value={state.conversation.mode} disabled={busy || !connected} onChange={event => void run(() => request('/conversation/configure', { mode: event.target.value }))}>
          <option value="auto">{t("Tự gửi sau khi nói")}</option><option value="manual">{t("Kiểm tra trước khi gửi")}</option>
        </select>
      </label>
      <h3 className="settings-heading">{t("Cách nhận ký hiệu người bệnh")}</h3>
      <RecognitionModePanel bootstrap={bootstrap} state={state} run={run} disabled={busy || !connected} />
      <SourcePanel key={state.recognition?.mode} words={bootstrap.recognition_catalogs[state.recognition?.mode ?? 'fusion']} capture={state.capture} run={run} busy={busy || !connected || !!state.recognition?.switching} conversation={state.conversation} />
      <Diagnostics state={state} />
      <div className="session-reset-option"><button className="text-button" onClick={() => { setSourceOpen(false); setResetOpen(true); }}>{t("Xóa nội dung và bắt đầu lại")}</button></div>
    </Dialog>}
    {temporaryOpen && state.temporary && <TemporaryConversation id={state.temporary.id} onClose={() => setTemporaryOpen(false)} run={run} />}
    {resetOpen && <Dialog title={t("Bắt đầu cuộc trao đổi mới?")} onClose={() => setResetOpen(false)}><p>{t("Nội dung hiện tại sẽ được xóa khỏi cả hai màn hình. Camera, micro và ký hiệu đang phát cũng sẽ dừng.")}</p><div className="dialog-actions"><button className="button secondary" onClick={() => setResetOpen(false)}>{t("Tiếp tục trao đổi")}</button><button className="button primary" disabled={busy} onClick={() => void run(async () => {
      await request('/session/reset', {});
      setResetOpen(false);
    })}>{t("Bắt đầu phiên mới")}</button></div></Dialog>}
  </main>;
}
