import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
import ts from 'typescript';

const root = path.resolve(import.meta.dirname, '..');
const output = path.join(root, 'build', 'test-modules');
await fs.mkdir(output, { recursive: true });
for (const name of ['patientWordSpeaker']) {
  const code = await fs.readFile(path.join(root, 'src/speech', `${name}.ts`), 'utf8');
  const compiled = ts.transpileModule(code, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } });
  await fs.writeFile(path.join(output, `${name}.mjs`), compiled.outputText);
}
const { PatientWordSpeaker } = await import(pathToFileURL(path.join(output, 'patientWordSpeaker.mjs')));
const entries = [
  { id: 'mm100-W068', text: 'Sốt', file: 'mm100-W068.wav', duration_ms: 400 },
  { id: '204', text: 'Mệt', file: '204.wav', duration_ms: 400 },
  { id: '87', text: 'Cần', file: '87.wav', duration_ms: 400 },
  { id: '210', text: 'Nghỉ ngơi', file: '210.wav', duration_ms: 600 },
  { id: 'uncertain', text: 'Chưa chắc', file: 'uncertain.wav', duration_ms: 500 },
].map(entry => ({...entry, warning: {file: 'warning-' + entry.file, prefix_ms: 120, duration_ms: entry.duration_ms + 120}}));
const word = (id, text, extra = {}) => ({ id, text, role: 'patient', ...extra });
const snapshot = (words = [], extra = {}) => ({ session_id: 'one', capture: { generation: 1 }, conversation: { status: 'active' }, messages: [{ words }], ...extra });
function fixture(clock = () => 100) {
  const audio = [], events = [];
  const speaker = new PatientWordSpeaker(entries, (url) => {
    const item = { url, paused: false, currentTime: 0, onended: null, onerror: null, onplaying: null,
      async play() { this.onplaying?.(); }, pause() { this.paused = true; } };
    audio.push(item);
    return item;
  }, (event) => events.push(event), clock);
  speaker.sync(snapshot(), true, true);
  return { speaker, audio, events };
}

test('reads each word immediately, in order, without waiting for the turn endpoint', () => {
  const f = fixture(), words = [word('a', 'Mệt'), word('b', 'Cần'), word('c', 'Nghỉ ngơi')];
  f.speaker.sync(snapshot(words.slice(0, 1)), true, true);
  assert.equal(f.audio.length, 1);
  f.speaker.sync(snapshot(words), true, true);
  assert.equal(f.audio.length, 1, 'never overlap voices');
  f.audio[0].onended(); f.audio[1].onended(); f.audio[2].onended();
  assert.deepEqual(f.audio.map(a => a.url.split('/').at(-1)), ['204.wav', '87.wav', '210.wav']);

  f.speaker.sync(snapshot(words, { patient_turn: null }), true, true);
  assert.equal(f.audio.length, 3, 'final sentence must not repeat the words');
  f.speaker.cancel();
});

test('duplicate snapshots and confirmations never repeat audio; deliberate repeated words do', () => {
  const f = fixture(), words = [word('a', 'Mệt')];
  f.speaker.sync(snapshot(words), true, true); f.audio[0].onended();
  for (let i = 0; i < 10; i++) f.speaker.sync(snapshot(words), true, true);
  f.speaker.sync(snapshot([word('a', 'Mệt', { status: 'confirmed' })]), true, true);
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
  f.speaker.sync(snapshot([word('d', 'Mệt')], { session_id: 'two', capture: { generation: 2 } }), true, true);
  assert.equal(f.audio.length, 1);
  f.speaker.sync(snapshot([word('d', 'Mệt'), word('f', 'Mệt')], { session_id: 'two', capture: { generation: 2 } }), true, true);
  assert.equal(f.audio.length, 2);
  f.speaker.cancel();
});

test('top-1 words read immediately without warnings regardless of old uncertainty metadata', () => {
  const f = fixture(), words = [word('a', 'Mệt', {uncertain:true}), word('b', 'Cần', {uncertain:true}),
    word('c', 'Nghỉ ngơi'), word('d', 'Sốt', {uncertain:true})];
  f.speaker.sync(snapshot(words), true, true);
  assert.equal(f.events.filter(e => e.type === 'playing').length, 1);
  for(let i=0;i<4;i++) f.audio[i].onended();
  assert.deepEqual(f.audio.map(a => a.url.split('/').at(-1)), ['204.wav','87.wav','210.wav','mm100-W068.wav']);
  assert.deepEqual(f.events.filter(e => e.type === 'playing').map(e=>e.text), words.map(w=>w.text));
  assert.ok(f.events.every(e => !e.type.startsWith('beep')));

  f.speaker.cancel();
});

test('rebuffering does not repeat a word and stale completion cannot revive a corrected word', () => {
  const f = fixture();
  f.speaker.sync(snapshot([word('a','Mệt',{uncertain:true})]), true, true);
  const stale = f.audio[0].onended;
  f.audio[0].onplaying();
  assert.equal(f.events.filter(e=>e.type==='playing').length,1);
  f.speaker.sync(snapshot([word('a','Cần',{status:'confirmed'})]),true,true);
  stale();
  assert.ok(f.audio[0].paused);
  assert.deepEqual(f.events.filter(e=>e.type==='playing').map(e=>e.text),['Mệt','Cần']);
  assert.equal(f.audio.length,2);
  f.speaker.cancel();
});

test('End cancels a top-1 word and queued words even after a stale ended callback', () => {
  const f=fixture(), words=[word('a','Mệt',{uncertain:true}),word('b','Cần')];
  f.speaker.sync(snapshot(words),true,true);
  const late=f.audio[0].onended;
  f.speaker.sync(snapshot(words,{conversation:{status:'idle'}}),true,true);
  late();
  assert.ok(f.audio[0].paused);
  assert.equal(f.audio.length,1);

  assert.deepEqual(f.events.filter(e=>e.type==='playing').map(e=>e.text),['Mệt']);
});

test('first new word is not lost when source generation and result arrive in the same snapshot', () => {
  const f = fixture();
  f.speaker.sync(snapshot([word('old', 'Mệt')]),true,true);
  f.audio[0].onended();
  f.speaker.sync(snapshot([word('old', 'Mệt'),word('new','Sốt')],{capture:{generation:2}}),true,true);
  assert.equal(f.audio.length,2);
  assert.ok(f.audio[1].url.endsWith('mm100-W068.wav'));
  f.speaker.cancel();
});

test('audio failure cancels playback; stale completion cannot play queued words', () => {
  const f = fixture();
  f.speaker.sync(snapshot([word('a', 'Mệt'), word('b', 'Cần')]), true, true);
  const staleEnd = f.audio[0].onended;
  f.audio[0].onerror(); staleEnd();
  assert.equal(f.audio.length, 1);

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
    const warning = await fs.readFile(path.join(root, 'assets/patient-voice', entry.warning.file));
    assert.equal(createHash('sha256').update(warning).digest('hex'), entry.warning.sha256);
    assert.equal(entry.warning.original_sha256, entry.sha256);
    const voiceData = wav.indexOf(Buffer.from('data')) + 8;
    const warningData = warning.indexOf(Buffer.from('data')) + 8;
    const prefixBytes = Math.round(entry.warning.prefix_ms / 1000 * wav.readUInt32LE(24)) * 2;
    assert.deepEqual(warning.subarray(warningData + prefixBytes), wav.subarray(voiceData), 'all original word PCM must remain byte-identical');
    assert.ok(entry.warning.prefix_ms >= 80 && entry.warning.prefix_ms <= 150);
  }
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
