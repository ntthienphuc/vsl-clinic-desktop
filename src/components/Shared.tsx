import { t, useInterfaceLanguage, setInterfaceLanguage } from '../i18n';
import { memo, useEffect, useRef, useState } from 'react';
import { Activity, ArrowUpRight, ChevronDown, HeartPulse, Maximize2, MessageCircle, Monitor, Pause, Play, RotateCcw, Square } from 'lucide-react';
import { request, token } from '../api';
import type { Message, Playback, Role, SessionState } from '../types';
import type { RunAction } from './SourcePanel';

export function AppHeader({ role, connected, state, run }: { role: Role; connected: boolean; state: SessionState; run: RunAction }) {
  const [showDisplay, setShowDisplay] = useState(false);
  const language = useInterfaceLanguage();
  const [changingLanguage, setChangingLanguage] = useState(false);
  const displayMenu = useRef<HTMLDivElement>(null);
  const displayButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!showDisplay) return;
    const closeOutside = (event: PointerEvent) => {
      if (!displayMenu.current?.contains(event.target as Node)) setShowDisplay(false);
    };
    const closeEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setShowDisplay(false); displayButton.current?.focus(); }
    };
    document.addEventListener('pointerdown', closeOutside);
    document.addEventListener('keydown', closeEscape);
    return () => { document.removeEventListener('pointerdown', closeOutside); document.removeEventListener('keydown', closeEscape); };
  }, [showDisplay]);
  return <header className="app-header">
    <div className="brand" aria-label="VSL Clinic">
      <span className="brand-mark"><HeartPulse size={25} strokeWidth={1.7} /></span>
      <span>VSL<span className="brand-light"> Clinic</span></span>
    </div>
    <div className="header-divider" />
    <div className="role-heading"><strong>{role === 'doctor' ? t("Bác sĩ") : t("Người bệnh")}</strong></div>
    <div className="header-right">
      {role === 'doctor' && <button className="language-toggle" data-testid="interface-language" disabled={changingLanguage}
        aria-label={language === 'vi' ? 'Switch interface to English' : 'Chuyển giao diện sang tiếng Việt'}
        title={language === 'vi' ? 'Đổi giao diện · Nội dung và giọng đọc tiếng Việt' : 'Change interface · Messages and speech stay Vietnamese'}
        onClick={() => {
          setChangingLanguage(true);
          void run(() => setInterfaceLanguage(language === 'vi' ? 'en' : 'vi')).finally(() => setChangingLanguage(false));
        }}><span lang="vi" className={language === 'vi' ? 'current' : ''}>VI</span><span aria-hidden="true">/</span><span lang="en" className={language === 'en' ? 'current' : ''}>EN</span></button>}
      <span className={connected ? 'connection good' : 'connection'}><span className={connected ? 'status-dot active' : 'status-dot amber'} />{connected ? t("Đã kết nối") : t("Đang kết nối lại")}</span>
      {role === 'doctor' && <div className="display-menu" ref={displayMenu}>
        <button ref={displayButton} className="icon-button" aria-expanded={showDisplay} title={t("Bố trí màn hình")} aria-label={t("Bố trí màn hình")} onClick={() => setShowDisplay(!showDisplay)}><Monitor size={20} /></button>
        {showDisplay && <div className="dropdown">
          {role === 'doctor' && <button onClick={() => {
            if (window.clinicDesktop) {
              void run(() => window.clinicDesktop!.openPatient());
            } else {
              window.open(`/patient?token=${encodeURIComponent(token)}`, 'vsl-patient');
            }
            setShowDisplay(false);
          }}><ArrowUpRight size={16} /> {t(" Mở màn hình người bệnh")}</button>}
          {window.clinicDesktop && <><button onClick={() => { setShowDisplay(false); void run(() => window.clinicDesktop!.arrange(false)); }}><Monitor size={16} /> {t(" Tự bố trí hai cửa sổ")}</button><button onClick={() => { setShowDisplay(false); void run(() => window.clinicDesktop!.arrange(true)); }}><RotateCcw size={16} /> {t(" Đổi vị trí hai màn hình")}</button></>}
          <button onClick={() => {
            if (window.clinicDesktop) {
              void run(() => window.clinicDesktop!.fullscreen());
            } else if (document.fullscreenElement) {
              void document.exitFullscreen();
            } else {
              void document.documentElement.requestFullscreen();
            }
            setShowDisplay(false);
          }}><Maximize2 size={16} /> {t(" Toàn màn hình")}</button>
          <span>{state.clients.doctor} {t(" cửa sổ bác sĩ · ")}{state.clients.patient} {t(" cửa sổ người bệnh")}</span>
        </div>}
      </div>}
    </div>
  </header>;
}

export function PlaybackControls({ playback, pending, run }: { playback: Playback | null; pending: number; run: RunAction }) {
  if (!playback) return null;
  const control = (action: string, rate?: number) => run(() => request('/playback', { action, playback_id: playback.id, rate }));
  const active = ['playing', 'paused', 'loading'].includes(playback.status);
  return <div className="playback-controls">
    <div className="playback-buttons">
      <button className="icon-button control-button" disabled={playback.status === 'loading'} title={playback.status === 'playing' ? t("Tạm dừng") : t("Tiếp tục hoặc phát lại")} aria-label={playback.status === 'playing' ? t("Tạm dừng") : t("Tiếp tục hoặc phát lại")} onClick={() => void control(playback.status === 'playing' ? 'pause' : playback.status === 'paused' ? 'resume' : 'replay')}>{playback.status === 'playing' ? <Pause size={18} /> : <Play size={18} />}<span>{playback.status === 'playing' ? t("Tạm dừng") : playback.status === 'paused' ? t("Tiếp tục") : t("Xem lại")}</span></button>
      {active && <button className="icon-button control-button" title={t("Phát lại từ đầu")} aria-label={t("Phát lại từ đầu")} onClick={() => void control('replay')}><RotateCcw size={17} /><span>{t("Phát lại")}</span></button>}
      <button className="icon-button control-button" disabled={!active} title={t("Dừng ký hiệu và hủy nội dung đang chờ")} aria-label={t("Dừng ký hiệu và hủy nội dung đang chờ")} onClick={() => void control('stop')}><Square size={16} /><span>{t("Dừng")}</span></button>
      <select className="speed-select" aria-label={t("Tốc độ ký hiệu")} value={playback.rate} onChange={(event) => void control('speed', Number(event.target.value))}><option value={0.5}>{t("0,5×")}</option><option value={0.75}>{t("0,75×")}</option><option value={1}>{t("1×")}</option><option value={1.25}>{t("1,25×")}</option></select>
    </div>
    <span className="playback-status">{playback.status === 'playing' ? t("Đang thể hiện") : playback.status === 'paused' ? playback.pause_reason === 'patient_disconnected' ? t("Đã dừng chờ màn hình người bệnh · bấm tiếp tục khi sẵn sàng") : t("Đã tạm dừng") : playback.status === 'loading' ? t("Chờ màn hình người bệnh") : t("Đã kết thúc")}{pending > 0 && t(' · {0} đang chờ', pending)}</span>
  </div>;
}

function HandMark() { return <span className="emblem-reply"><MessageCircle size={23} strokeWidth={1.4} /></span>; }

export const Conversation = memo(function Conversation({ messages }: { messages: Message[] }) {
  useInterfaceLanguage();
  const scroll = useRef<HTMLDivElement>(null);
  const lastId = messages.at(-1)?.id;
  const lastUpdate = messages.at(-1)?.updated_at_ms;
  useEffect(() => {
    if (scroll.current) {
      scroll.current.scrollTop = scroll.current.scrollHeight;
    }
  }, [lastId, lastUpdate]);
  return <div className="conversation" ref={scroll} aria-label={t("Nội dung trao đổi")}>
    {messages.length === 0 && <div className="conversation-empty"><div className="conversation-emblem" aria-hidden="true"><MessageCircle size={36} strokeWidth={1.25} /><HandMark /></div><h2>{t('Chưa có lời trao đổi')}</h2><p>{t('Bắt đầu cuộc trao đổi, rồi nói hoặc nhập lời của bạn.')}</p><small>{t('Nội dung chỉ giữ trong phiên đang mở.')}</small></div>}
    {messages.map((message) => <article key={message.id} className={`message ${message.role}`}>
      <div className="message-meta"><span>{message.role === 'doctor' ? t("Bác sĩ") : t("Người bệnh")}</span><time>{new Date(message.created_at_ms).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}</time></div>
      <div className="message-bubble">{message.kind === 'patient_turn' && message.words?.length ? <span className="history-word-list">{message.words.map(word => <span key={word.id} className="patient-chat-word">{word.text}</span>)}</span> : message.text}</div>
      {message.speech_repair && <details className="original-words"><summary>{t("Đã sửa lỗi nghe: ")}{message.speech_repair.corrected_text}</summary>{t("Âm thanh được nhận thành: ")}{message.speech_repair.raw_text}</details>}
      {message.kind !== 'patient_turn' && message.reading?.rewritten && <details className="original-words"><summary>{t("Từ nhận được")}</summary>{message.raw_text}</details>}
      <div className="message-status">{message.role === 'patient' ? message.status === 'streaming' ? t("Đang nhận từng từ…") : message.manual ? t('Đã gửi') : t('Đã nhận từng từ') : message.status === 'interrupted' ? t("Đã ngắt để nói câu mới") : message.status === 'cancelled' ? t("Đã hủy phát") : message.status === 'queued' ? t("Đang chờ phát") : message.mode === 'sign' ? t("Chữ và ký hiệu") : t("Nội dung bằng chữ")}</div>
    </article>)}
  </div>;
});

export function Diagnostics({ state }: { state: SessionState }) {
  const capture = state.capture;
  const result = state.current_result?.metrics;
  return <details className="diagnostics">
    <summary><Activity size={14} /> {t(" Trạng thái kỹ thuật ")}<ChevronDown size={13} /></summary>
    <div className="diagnostic-grid">
      <span>{t("Tốc độ nhận hình")}<strong>{(capture.processed_fps ?? 0).toFixed(1)} fps</strong></span>
      <span>{t("Tuổi frame")}<strong>{(capture.frame_age_ms ?? 0).toFixed(0)} ms</strong></span>
      <span>Detector<strong>{(capture.detect_ms ?? 0).toFixed(0)} ms</strong></span>
      <span>{t("Frame thay thế")}<strong>{capture.dropped ?? 0}/{capture.captured ?? 0}</strong></span>
      <span>Inference<strong>{Number(result?.inference_ms ?? 0).toFixed(0)} ms</strong></span>
      <span>{t("Đang chờ xử lý")}<strong>{capture.queued_segments ?? 0} {t(" đoạn")}</strong></span>
    </div>
    <p>{state.recognition?.mode === 'sign_only' ? t("Chỉ ký hiệu: bộ 400 từ.") : t("Ký hiệu + khẩu hình: bộ 100 từ.")} {t(" Video phát ở tốc độ gốc.")}</p>
  </details>;
}
