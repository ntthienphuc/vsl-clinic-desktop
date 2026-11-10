import { useEffect, useRef, useState } from 'react';
import type { SessionState } from '../types';
import bank from '../../assets/patient-voice/manifest.json';
import { PatientWordSpeaker, type VoiceEvent } from './patientWordSpeaker';
import { setPatientAudioPlaying } from './patientAudioGate';

export function usePatientVoice(state: SessionState, connected: boolean) {
  const [enabled, setEnabled] = useState(() => localStorage.getItem('clinic-patient-voice') !== 'off');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const events = useRef<VoiceEvent[]>([]);
  const speaker = useRef<PatientWordSpeaker | null>(null);
  useEffect(() => {
    speaker.current = new PatientWordSpeaker(bank.entries, (url) => {
      const audio = new Audio(url);
      audio.playbackRate = 0.9;
      audio.preservesPitch = true;
      return audio;
    }, setPatientAudioPlaying, (event) => {
      events.current = [...events.current.slice(-79), { ...event, recorded_at_ms: Date.now() }];
      window.clinicDiagnostics = { ...window.clinicDiagnostics, patientVoice: events.current };
      if (event.type === 'playing') setStatus(`Đang đọc: ${event.text}`);
      if (event.type === 'ended' || event.type === 'cancelled') setStatus('');
      if (event.type === 'error') { setError(event.detail ?? 'Không phát được giọng đọc.'); setEnabled(false); }
    });
    return () => { speaker.current?.cancel(); speaker.current = null; };
  }, []);
  useEffect(() => { speaker.current?.sync(state, enabled, connected); }, [state, enabled, connected]);
  const toggle = () => {
    const next = !enabled;
    if (!next) speaker.current?.cancel();
    setEnabled(next);
    setError('');
    localStorage.setItem('clinic-patient-voice', next ? 'on' : 'off');
  };
  return { enabled, toggle, status, error };
}
