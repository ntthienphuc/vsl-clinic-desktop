import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
import ts from 'typescript';

const root = path.resolve(import.meta.dirname, '..');
const output = path.join(root, 'build', 'test-modules');
await fs.mkdir(output, { recursive: true });
for (const name of ['patientWordSpeaker', 'patientAudioGate']) {
  const code = await fs.readFile(path.join(root, 'src/speech', `${name}.ts`), 'utf8');
  const compiled = ts.transpileModule(code, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } });
  await fs.writeFile(path.join(output, `${name}.mjs`), compiled.outputText);
}
const { PatientWordSpeaker } = await import(pathToFileURL(path.join(output, 'patientWordSpeaker.mjs')));
const gate = await import(pathToFileURL(path.join(output, 'patientAudioGate.mjs')));
const entries = [
  { id: 'mm100-W068', text: 'Sốt', file: 'mm100-W068.wav', duration_ms: 400 },
  { id: '204', text: 'Mệt', file: '204.wav', duration_ms: 400 },
  { id: '87', text: 'Cần', file: '87.wav', duration_ms: 400 },
  { id: '210', text: 'Nghỉ ngơi', file: '210.wav', duration_ms: 600 },
  { id: 'uncertain', text: 'Chưa chắc', file: 'uncertain.wav', duration_ms: 500 },
];
const word = (id, text, extra = {}) => ({ id, text, role: 'patient', ...extra });
const snapshot = (words = [], extra = {}) => ({ session_id: 'one', capture: { generation: 1 }, conversation: { status: 'active' }, messages: [{ words }], ...extra });
function fixture() {
  const audio = [], events = [], gates = [];
  const speaker = new PatientWordSpeaker(entries, (url) => {
    const item = { url, paused: false, onended: null, onerror: null, onplaying: null,
      async play() { assert.equal(gates.at(-1), true); this.onplaying?.(); }, pause() { this.paused = true; } };
    audio.push(item);
    return item;
  }, (value) => gates.push(value), (event) => events.push(event), () => 100);
  speaker.sync(snapshot(), true, true);
  return { speaker, audio, events, gates };
}

test('reads each word immediately, in order, without waiting for the turn endpoint', () => {
  const f = fixture(), words = [word('a', 'Mệt'), word('b', 'Cần'), word('c', 'Nghỉ ngơi')];
  f.speaker.sync(snapshot(words.slice(0, 1)), true, true);
  assert.equal(f.audio.length, 1);
  f.speaker.sync(snapshot(words), true, true);
  assert.equal(f.audio.length, 1, 'never overlap voices');
  f.audio[0].onended(); f.audio[1].onended(); f.audio[2].onended();
  assert.deepEqual(f.audio.map(a => a.url.split('/').at(-1)), ['204.wav', '87.wav', '210.wav']);
  assert.equal(f.gates.at(-1), false);
  f.speaker.sync(snapshot(words, { patient_turn: null }), true, true);
  assert.equal(f.audio.length, 3, 'final sentence must not repeat the words');
  f.speaker.cancel();
});

test('duplicate snapshots and confirmations never repeat audio; deliberate repeated words do', () => {
  const f = fixture(), words = [word('a', 'Mệt')];
  f.speaker.sync(snapshot(words), true, true); f.audio[0].onended();
  for (let i = 0; i < 10; i++) f.speaker.sync(snapshot(words), true, true);
  f.speaker.sync(snapshot([word('a', 'Cần', { status: 'confirmed' })]), true, true);
  assert.equal(f.audio.length, 1);
  f.speaker.sync(snapshot([...words, word('b', 'Mệt')]), true, true);
  assert.equal(f.audio.length, 2);
  f.speaker.cancel();
});

test('mount, reconnection, mute and source/session changes baseline old history', () => {
  const f = fixture(), first = [word('a', 'Mệt')];
  f.speaker.sync(snapshot(first), true, true);
  f.speaker.sync(snapshot(first), true, false);
  assert.equal(f.audio[0].paused, true);
  f.speaker.sync(snapshot([...first, word('b', 'Cần')]), true, true);
  assert.equal(f.audio.length, 1);
  f.speaker.sync(snapshot([word('c', 'Mệt')]), false, true);
  f.speaker.sync(snapshot([word('c', 'Mệt')]), true, true);
  assert.equal(f.audio.length, 1);
  f.speaker.sync(snapshot([word('d', 'Mệt')], { session_id: 'two' }), true, true);
  f.speaker.sync(snapshot([word('e', 'Cần')], { session_id: 'two', capture: { generation: 2 } }), true, true);
  assert.equal(f.audio.length, 1);
  f.speaker.sync(snapshot([word('e', 'Cần'), word('f', 'Mệt')], { session_id: 'two', capture: { generation: 2 } }), true, true);
  assert.equal(f.audio.length, 2);
  f.speaker.cancel();
});

test('uncertain word stays silent until the same ID is confirmed, then speaks once', () => {
  const f = fixture();
  f.speaker.sync(snapshot([word('a', 'Mệt', { uncertain: true })]), true, true);
  assert.equal(f.audio.length, 0);
  f.speaker.sync(snapshot([word('a', 'Cần', { uncertain: false, status: 'confirmed' })]), true, true);
  assert.ok(f.audio[0].url.endsWith('87.wav'));
  f.audio[0].onended();
  f.speaker.sync(snapshot([word('a', 'Cần', { uncertain: false, status: 'confirmed' })]), true, true);
  assert.equal(f.audio.length, 1);
  f.speaker.cancel();
});

test('audio failure releases microphone gate; stale completion cannot play queued words', () => {
  const f = fixture();
  f.speaker.sync(snapshot([word('a', 'Mệt'), word('b', 'Cần')]), true, true);
  const staleEnd = f.audio[0].onended;
  f.audio[0].onerror(); staleEnd();
  assert.equal(f.audio.length, 1);
  assert.equal(f.gates.at(-1), false);
  assert.equal(f.events.at(-1).type, 'error');
});

test('stopping the conversation cancels speaking; patient manual feedback is not a sign result', () => {
  const f = fixture();
  f.speaker.sync(snapshot([word('a', 'Mệt')]), true, true);
  f.speaker.sync(snapshot([word('a', 'Mệt')], { conversation: { status: 'idle' } }), true, true);
  assert.equal(f.audio[0].paused, true);
  f.speaker.sync(snapshot([], { messages: [word('manual', 'Cần', { manual: true })] }), true, true);
  assert.equal(f.audio.length, 1);
});

test('microphone gate blocks synchronously and protects the echo tail between adjacent clips', async () => {
  const states = [];
  const unsubscribe = gate.subscribePatientAudio(() => states.push(gate.patientAudioBlocked()));
  gate.setPatientAudioPlaying(true);
  assert.equal(gate.patientAudioBlocked(), true);
  gate.setPatientAudioPlaying(false);
  assert.equal(gate.patientAudioBlocked(), true);
  gate.setPatientAudioPlaying(true);
  assert.deepEqual(states, [true]);
  gate.setPatientAudioPlaying(false);
  await new Promise(resolve => setTimeout(resolve, 650));
  assert.equal(gate.patientAudioBlocked(), false);
  unsubscribe();
});

test('offline bank covers all 400 exact recognizer labels and every WAV matches its hash', async () => {
  const { createHash } = await import('node:crypto');
  const bank = JSON.parse(await fs.readFile(path.join(root, 'assets/patient-voice/manifest.json'), 'utf8'));
  const labels = (await fs.readFile(path.join(root, 'assets/gloss.csv'), 'utf8')).trim().split(/\r?\n/u).map(line => line.split(','));
  assert.equal(labels.length, 400);
  for (const [id, label] of labels) assert.equal(bank.entries.find(e => e.id === id)?.text, label);
  for (const entry of bank.entries) {
    const wav = await fs.readFile(path.join(root, 'assets/patient-voice', entry.file));
    assert.equal(createHash('sha256').update(wav).digest('hex'), entry.sha256);
    assert.equal(wav.toString('ascii', 0, 4), 'RIFF');
    assert.ok(entry.duration_ms > 100 && entry.duration_ms < 5000);
  }
});

test('one audio source cannot release another sources microphone guard', async () => {
  gate.setPatientAudioPlaying(true, 'avatar');
  gate.setPatientAudioPlaying(true);
  gate.setPatientAudioPlaying(false);
  await new Promise(resolve => setTimeout(resolve, 650));
  assert.equal(gate.patientAudioBlocked(), true);
  gate.setPatientAudioPlaying(false, 'avatar');
  await new Promise(resolve => setTimeout(resolve, 650));
  assert.equal(gate.patientAudioBlocked(), false);
});


test('multimodal identity plays the new voice and a correction cannot play its old clip', () => {
  const f = fixture();
  f.speaker.sync(snapshot([word('mm-a', 'Sốt', {voice_key:'mm100-W068'})]), true, true);
  assert.ok(f.audio[0].url.endsWith('mm100-W068.wav'));
  f.audio[0].onended();
  f.speaker.sync(snapshot([word('mm-a', 'Sốt', {voice_key:'mm100-W068'}), word('mm-b', 'Mệt', {voice_key:'mm100-W068',status:'confirmed'})]), true, true);
  assert.ok(f.audio[1].url.endsWith('204.wav'));
  f.speaker.cancel();
});
