// Mute capture before speaker playback, including a short room-echo tail.
let blocked = false;
const sources = new Set<string>();
let tail: ReturnType<typeof setTimeout> | undefined;
const listeners = new Set<() => void>();
export const patientAudioBlocked = () => blocked;
export const subscribePatientAudio = (listener: () => void) => {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
};
export function setPatientAudioPlaying(playing: boolean, source = 'patient') {
  if (sources.has(source) === playing) return;
  if (playing) sources.add(source); else sources.delete(source);
  clearTimeout(tail);
  const update = (value: boolean) => {
    if (blocked !== value) {
      blocked = value;
      listeners.forEach((listener) => listener());
    }
  };
  if (sources.size) update(true);
  else if (blocked) tail = setTimeout(() => update(false), 600);
}
