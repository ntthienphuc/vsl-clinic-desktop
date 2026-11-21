import { t } from './i18n';
import { AvatarView } from './avatar/AvatarView';
import { PatientCamera } from './components/PatientCamera';
import type { Bootstrap, SessionState } from './types';

export function PatientView({ bootstrap, state, connected }: { bootstrap: Bootstrap; state: SessionState; connected: boolean }) {
  const latestDoctor = [...state.messages].reverse().find((message) => message.role === 'doctor' && message.status !== 'cancelled');
  const activePlayback = state.playback && ['playing', 'paused', 'loading'].includes(state.playback.status) ? state.playback : null;
  const displayedText = activePlayback?.text ?? latestDoctor?.text;
  return <main className="patient-page">
    <h1 className="sr-only">{t('Cuộc trao đổi của bạn')}</h1>
    <div className="patient-grid">
      <section className="patient-stage-panel" aria-label={t('Lời bác sĩ')}>
        <AvatarView bootstrap={bootstrap} playback={state.playback} voiceEnabled={state.avatar_voice_enabled !== false} connected={connected} />
        <div className="patient-message">
          <span className="patient-message-label">{t('Lời bác sĩ')}</span>
          <div className={displayedText ? 'doctor-caption' : 'doctor-caption empty'} data-testid="doctor-caption" aria-live="polite">{displayedText ?? t('Sẵn sàng lắng nghe bác sĩ')}</div>
          {activePlayback && latestDoctor && latestDoctor.id !== activePlayback.message_id && <div className="current-sign-text">{latestDoctor.mode === 'text' ? t('Lời nhắn mới bằng chữ') : t('Lời nhắn tiếp theo')}: <strong>{latestDoctor.text}</strong></div>}
        </div>
      </section>
      <aside className="patient-camera"><PatientCamera state={state} /></aside>
    </div>
  </main>;
}
