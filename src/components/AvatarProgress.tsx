import { t } from '../i18n';
import { useEffect, useState } from 'react';
import { Hand, Volume2, VolumeX } from 'lucide-react';
import { playbackProgress } from '../playbackProgress';
import type { Playback } from '../types';

export function AvatarProgress({ playback, pending, voiceEnabled = true, onVoiceToggle }: { playback: Playback | null; pending: number; voiceEnabled?: boolean; onVoiceToggle?: () => void }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    setNow(Date.now());
    if (playback?.status !== 'playing') return;
    const timer = setInterval(() => setNow(Date.now()), 100);
    return () => clearInterval(timer);
  }, [playback]);
  if (!playback) return null;
  const progress = playbackProgress(playback, now);
  const title = playback.status === 'loading' ? 'Chờ màn hình người bệnh'
    : playback.status === 'paused' ? 'Ký hiệu đang tạm dừng'
    : playback.status === 'stopped' ? 'Đã dừng ký hiệu'
    : playback.status === 'completed' ? 'Đã thể hiện xong'
    : 'Người bệnh đang xem ký hiệu';
  return <div className={`doctor-avatar-progress ${playback.status}`} data-testid="avatar-progress">
    <div className="avatar-progress-heading"><Hand size={17} /><strong>{t(title)}</strong><span>{Math.floor(progress.percent)}%</span>{onVoiceToggle && <button className="icon-button" aria-label={voiceEnabled ? t("Tắt đọc lời bác sĩ") : t("Bật đọc lời bác sĩ")} aria-pressed={voiceEnabled} onClick={onVoiceToggle}>{voiceEnabled ? <Volume2 size={17} /> : <VolumeX size={17} />}</button>}</div>
    <div className="avatar-progress-track" role="progressbar" aria-label={t("Tiến độ phát ký hiệu")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.floor(progress.percent)} aria-valuetext={`${t(title)}: ${progress.label}, ${progress.index + 1}/${playback.glosses.length}`}><i style={{ width: `${progress.percent}%` }} /></div>
    <div className="avatar-progress-detail"><span title={playback.text}>{playback.status === 'loading' ? playback.text : `${progress.index + 1}/${playback.glosses.length} · ${progress.label}`}{playback.status === 'playing' && progress.phase === 'bridge' ? t(" · chuyển ký hiệu") : ''}</span><small>{playback.status === 'playing' ? t("Còn khoảng {0} giây", progress.remainingSeconds) : ''}{pending > 0 ? t(" · {0} câu đang chờ", pending) : ''}</small></div>
  </div>;
}
