import { useEffect, useRef, useState } from 'react';
import { Activity, ArrowUpRight, Check, ChevronDown, HeartPulse, Maximize2, Monitor, Pause, Play, RotateCcw, Square } from 'lucide-react';
import { request, token } from '../api';
import type { Message, Playback, Role, SessionState } from '../types';
import type { RunAction } from './SourcePanel';

export function AppHeader({ role, connected, state, run }: { role: Role; connected: boolean; state: SessionState; run: RunAction }) {
  const [showDisplay, setShowDisplay] = useState(false);
  return <header className="app-header">
    <a className="brand" href={`/${role}?token=${encodeURIComponent(token)}`} aria-label="VSL Clinic">
      <span className="brand-mark"><HeartPulse size={25} strokeWidth={1.7} /></span>
      <span>VSL<span className="brand-light"> Clinic</span></span>
    </a>
    <div className="header-divider" />
    <div className="role-heading"><strong>{role === 'doctor' ? 'Bác sĩ' : 'Người bệnh'}</strong></div>
    <div className="header-right">
      <span className={connected ? 'connection good' : 'connection'}><span className={connected ? 'status-dot active' : 'status-dot amber'} />{connected ? 'Đã kết nối' : 'Đang kết nối lại'}</span>
      <div className="display-menu">
        <button className="icon-button" title="Bố trí màn hình" aria-label="Bố trí màn hình" onClick={() => setShowDisplay(!showDisplay)}><Monitor size={20} /></button>
        {showDisplay && <div className="dropdown">
          {role === 'doctor' && <button onClick={() => {
            if (window.clinicDesktop) {
              void run(() => window.clinicDesktop!.openPatient());
            } else {
              window.open(`/patient?token=${encodeURIComponent(token)}`, 'vsl-patient');
            }
            setShowDisplay(false);
          }}><ArrowUpRight size={16} /> Mở màn hình người bệnh</button>}
          {window.clinicDesktop && <><button onClick={() => void run(() => window.clinicDesktop!.arrange(false))}><Monitor size={16} /> Tự bố trí hai cửa sổ</button><button onClick={() => void run(() => window.clinicDesktop!.arrange(true))}><RotateCcw size={16} /> Đổi vị trí hai màn hình</button></>}
          <button onClick={() => {
            if (window.clinicDesktop) {
              void run(() => window.clinicDesktop!.fullscreen());
            } else if (document.fullscreenElement) {
              void document.exitFullscreen();
            } else {
              void document.documentElement.requestFullscreen();
            }
            setShowDisplay(false);
          }}><Maximize2 size={16} /> Toàn màn hình</button>
          <span>{state.clients.doctor} cửa sổ bác sĩ · {state.clients.patient} cửa sổ người bệnh</span>
        </div>}
      </div>
    </div>
  </header>;
}

export function PlaybackControls({ playback, pending, run }: { playback: Playback | null; pending: number; run: RunAction }) {
  if (!playback) {
    return <div className="playback-empty"><span className="status-dot" /> Sẵn sàng phát ký hiệu</div>;
  }
  const control = (action: string, rate?: number) => run(() => request('/playback', { action, playback_id: playback.id, rate }));
  const active = ['playing', 'paused', 'loading'].includes(playback.status);
  return <div className="playback-controls">
    <div className="playback-buttons">
      <button className="icon-button control-button" disabled={playback.status === 'loading'} title={playback.status === 'playing' ? 'Tạm dừng' : 'Tiếp tục hoặc phát lại'} aria-label={playback.status === 'playing' ? 'Tạm dừng' : 'Tiếp tục hoặc phát lại'} onClick={() => void control(playback.status === 'playing' ? 'pause' : playback.status === 'paused' ? 'resume' : 'replay')}>{playback.status === 'playing' ? <Pause size={18} /> : <Play size={18} />}<span>{playback.status === 'playing' ? 'Tạm dừng' : playback.status === 'paused' ? 'Tiếp tục' : 'Xem lại'}</span></button>
      <button className="icon-button control-button" title="Phát lại từ đầu" aria-label="Phát lại từ đầu" onClick={() => void control('replay')}><RotateCcw size={17} /><span>Phát lại</span></button>
      <button className="icon-button control-button" disabled={!active} title="Dừng ký hiệu và hủy nội dung đang chờ" aria-label="Dừng ký hiệu và hủy nội dung đang chờ" onClick={() => void control('stop')}><Square size={16} /><span>Dừng</span></button>
      <select className="speed-select" aria-label="Tốc độ ký hiệu" value={playback.rate} onChange={(event) => void control('speed', Number(event.target.value))}><option value={0.5}>0,5×</option><option value={0.75}>0,75×</option><option value={1}>1×</option><option value={1.25}>1,25×</option></select>
    </div>
    <span className="playback-status">{playback.status === 'playing' ? 'Đang thể hiện' : playback.status === 'paused' ? playback.pause_reason === 'patient_disconnected' ? 'Đã dừng chờ màn hình người bệnh · bấm tiếp tục khi sẵn sàng' : 'Đã tạm dừng' : playback.status === 'loading' ? 'Chờ màn hình người bệnh' : 'Đã kết thúc'}{pending > 0 && ` · ${pending} đang chờ`}</span>
  </div>;
}

export function Conversation({ messages }: { messages: Message[] }) {
  const scroll = useRef<HTMLDivElement>(null);
  const lastId = messages.at(-1)?.id;
  const lastUpdate = messages.at(-1)?.updated_at_ms;
  useEffect(() => {
    if (scroll.current) {
      scroll.current.scrollTop = scroll.current.scrollHeight;
    }
  }, [lastId, lastUpdate]);
  return <div className="conversation" ref={scroll} aria-label="Nội dung trao đổi">
    {messages.length === 0 && <div className="conversation-empty"><span className="conversation-line" /><p>Cuộc trao đổi sẽ xuất hiện ở đây</p><small>Nội dung chỉ giữ trong phiên đang mở.</small></div>}
    {messages.map((message) => <article key={message.id} className={`message ${message.role}`}>
      <div className="message-meta"><span>{message.role === 'doctor' ? 'Bác sĩ' : 'Người bệnh'}</span><time>{new Date(message.created_at_ms).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}</time></div>
      <div className="message-bubble">{message.text}</div>
      {message.kind === 'patient_turn' && message.reading?.rewritten && <details className="original-words"><summary>Từ nhận được</summary>{message.raw_text}</details>}
      <div className="message-status">{message.role === 'patient' ? message.status === 'streaming' ? 'Đang nhận từng từ…' : message.status === 'confirmed' ? <><Check size={11} /> Đã xác nhận</> : message.reading?.rewritten ? 'Gợi ý diễn đạt · giữ nguyên các từ gốc để đối chiếu' : 'Kết quả nhận dạng · cần đối chiếu' : message.status === 'cancelled' ? 'Đã hủy phát' : message.status === 'queued' ? 'Đang chờ phát' : message.mode === 'sign' ? 'Chữ và ký hiệu' : 'Nội dung bằng chữ'}</div>
    </article>)}
  </div>;
}

export function Diagnostics({ state }: { state: SessionState }) {
  const capture = state.capture;
  const result = state.current_result?.metrics;
  return <details className="diagnostics">
    <summary><Activity size={14} /> Trạng thái kỹ thuật <ChevronDown size={13} /></summary>
    <div className="diagnostic-grid">
      <span>Tốc độ nhận hình<strong>{(capture.processed_fps ?? 0).toFixed(1)} fps</strong></span>
      <span>Tuổi frame<strong>{(capture.frame_age_ms ?? 0).toFixed(0)} ms</strong></span>
      <span>Detector<strong>{(capture.detect_ms ?? 0).toFixed(0)} ms</strong></span>
      <span>Frame thay thế<strong>{capture.dropped ?? 0}/{capture.captured ?? 0}</strong></span>
      <span>Inference<strong>{Number(result?.inference_ms ?? 0).toFixed(0)} ms</strong></span>
      <span>Đang chờ xử lý<strong>{capture.queued_segments ?? 0} đoạn</strong></span>
    </div>
    <p>Nhận dạng 400 từ riêng lẻ. Video được đọc ở tốc độ gốc; frame cũ được thay bằng frame mới khi xử lý chậm.</p>
  </details>;
}
