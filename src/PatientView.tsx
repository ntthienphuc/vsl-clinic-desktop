import { Check, MessageSquareText, RotateCcw } from 'lucide-react';
import { AvatarView } from './avatar/AvatarView';
import { request } from './api';
import { PlaybackControls } from './components/Shared';
import type { RunAction } from './components/SourcePanel';
import { PatientCamera } from './components/PatientCamera';
import type { Bootstrap, SessionState } from './types';

export function PatientView({ bootstrap, state, connected, run, busy }: { bootstrap: Bootstrap; state: SessionState; connected: boolean; run: RunAction; busy: boolean }) {
  const latestDoctor = [...state.messages].reverse().find((message) => message.role === 'doctor' && message.status !== 'cancelled');
  const activePlayback = state.playback && ['playing', 'paused', 'loading'].includes(state.playback.status) ? state.playback : null;
  const displayedText = activePlayback?.text ?? latestDoctor?.text;
  const lastFeedback = state.messages.at(-1);
  return <main className="patient-page">
    <div className="workspace-toolbar"><h1>Cuộc trao đổi của bạn</h1><span>Xem lời bác sĩ · Trả lời bằng ký hiệu</span></div>
    <div className="patient-grid">
      <section className="card avatar-card">
        <AvatarView bootstrap={bootstrap} playback={state.playback} />
        <PlaybackControls playback={state.playback} pending={state.pending_count} run={run} />
      </section>
      <aside className="patient-aside">
        <section className="card doctor-message-card">
          <div className="section-heading"><span className="heading-icon"><MessageSquareText size={19} /></span><div><h2>Lời bác sĩ</h2></div></div>
          <div className={displayedText ? 'doctor-caption' : 'doctor-caption empty'} data-testid="doctor-caption" aria-live="polite">{displayedText ?? 'Lời nhắn của bác sĩ sẽ xuất hiện ở đây.'}</div>
          {activePlayback && latestDoctor && latestDoctor.id !== activePlayback.message_id && <div className="current-sign-text">{latestDoctor.mode === 'text' ? 'Lời nhắn mới bằng chữ' : 'Lời nhắn tiếp theo'}: <strong>{latestDoctor.text}</strong></div>}
          <div className="feedback-buttons"><button className="button primary" disabled={!connected || busy} onClick={() => void run(() => request('/feedback', { value: 'understood' }))}><Check size={19} /> Tôi đã hiểu</button><button className="button secondary" disabled={!connected || busy} onClick={() => void run(() => request('/feedback', { value: 'repeat' }))}><RotateCcw size={17} /> Xin giải thích lại</button></div>
          {lastFeedback?.role === 'patient' && lastFeedback.manual && <div className="feedback-sent"><Check size={13} /> Đã báo với bác sĩ: {lastFeedback.text}</div>}
        </section>
        <div className="card patient-camera"><PatientCamera state={state} /></div>
      </aside>
    </div>
  </main>;
}
