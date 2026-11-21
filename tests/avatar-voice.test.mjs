import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';

const root = path.resolve(import.meta.dirname, '..');
const out = path.join(root, 'build/test-modules/narration.mjs');
await fs.mkdir(path.dirname(out), { recursive: true });
await fs.writeFile(out, ts.transpileModule(await fs.readFile(path.join(root, 'src/avatar/narration.ts'), 'utf8'),
  { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText);
const { AvatarNarrator, mouthAt } = await import(pathToFileURL(out));
const entry = { id: 'p:one', text: 'Uống nước.', file: 'one.wav', duration_ms: 2000, envelope_step_ms: 20,
  envelope: [0, ...Array(98).fill(180), 0], words: [{ text: 'Uống', start_ms: 0, end_ms: 1000 }, { text: 'nước', start_ms: 1000, end_ms: 2000 }] };
const playback = (extra = {}) => ({ id: 'a', iteration: 0, status: 'playing', rate: 1, total_ms: 4000,
  audio_cues: [{ entry_id: entry.id, text: entry.text, file: entry.file, start_ms: 350, end_ms: 2350, duration_ms: 2000 }], ...extra });
function fixture() {
  const clips = [], events = [];
  const narrator = new AvatarNarrator([entry], e => events.push(e), () => {
    const audio = { paused: true, ended: false, currentTime: 0,
      load() { this.oncanplay?.(); }, removeAttribute() {},
      async play() { this.paused = false; this.ended = false; this.onplaying?.(); },
      pause() { this.paused = true; this.onpause?.(); } };
    clips.push(audio); return audio;
  });
  return { narrator, clips, events };
}
test('mouth follows actual voiced energy and closes outside audio', () => {
  assert.ok(Object.values(mouthAt(entry, 500)).some(n => n > .2));
  assert.ok(Object.values(mouthAt(entry, -1)).every(n => n === 0));
  assert.ok(Object.values(mouthAt(entry, 2000)).every(n => n === 0));
  assert.ok(Object.values(mouthAt({ ...entry, envelope: Array(100).fill(0) }, 500)).every(n => n === 0));
});
test('narration pauses, resumes at the timeline position and preserves pitch on speed changes', async () => {
  const { narrator, clips } = fixture();
  narrator.tick(playback(), true, true, 850, .1);
  await Promise.resolve();
  let state = narrator.tick(playback(), true, true, 850, .1);
  assert.equal(clips[0].currentTime, .5);
  assert.equal(state.speaking, true);
  assert.ok(Object.values(state.mouth).some(n => n > 0));
  state = narrator.tick(playback({ status: 'paused' }), true, true, 850, .1);
  assert.equal(clips[0].paused, true);
  assert.ok(Object.values(state.mouth).every(n => n === 0));
  narrator.tick(playback({ rate: .75 }), true, true, 1000, .1);
  assert.equal(clips[0].playbackRate, .75);
  assert.equal(clips[0].preservesPitch, true);
  narrator.dispose();
});
test('mute, disconnect, End and replay cannot keep stale audio speaking', async () => {
  const { narrator, clips } = fixture();
  narrator.tick(playback(), true, true, 850, .1);
  await Promise.resolve();
  const oldPlaying = clips[0].onplaying;
  let state = narrator.tick(playback(), false, true, 900, .1);
  assert.equal(state.speaking, false);
  oldPlaying(); assert.equal(clips[0].paused, true);
  narrator.tick(playback(), true, false, 900, .1);
  assert.equal(clips[0].paused, true);
  narrator.tick(playback({ iteration: 1 }), true, true, 850, .1);
  oldPlaying(); assert.equal(clips[0].paused, true);
  assert.equal(clips.length, 2);
  state = narrator.tick(null, true, true, 0, .1);
  assert.ok(clips.every(a => a.paused));
  assert.ok(Object.values(state.mouth).every(n => n === 0));
  narrator.dispose();
});

test('a slow audio clock cannot trigger a seek into the middle of a spoken word', async () => {
  const { narrator, clips, events } = fixture();
  narrator.tick(playback(), true, true, 350, .02);
  await Promise.resolve();
  clips[0].currentTime = .01; // Device progress lags the shared timeline.
  narrator.tick(playback(), true, true, 570, .02);
  assert.equal(clips[0].currentTime, .01, 'Do not cut 210ms out of the word');
  assert.equal(events.filter(e => e.type === 'playing').length, 1);
  clips[0].onplaying(); // HTMLMediaElement can emit playing again after buffering.
  assert.equal(events.filter(e => e.type === 'playing').length, 1);
  assert.equal(events.filter(e => e.type === 'resumed').length, 1);
  narrator.dispose();
});

test('voice may finish after nominal duration and repeated signs still speak again', async () => {
  const { narrator, clips, events } = fixture();
  const p = playback({ total_ms: 7000, audio_cues: [playback().audio_cues[0],
    { ...playback().audio_cues[0], start_ms: 4000, end_ms: 6000 }] });
  narrator.tick(p, true, true, 350, .02);
  await new Promise(resolve => setImmediate(resolve));
  clips[0].currentTime = 1.9;
  const state = narrator.tick(p, true, true, 2400, .02);
  assert.equal(clips[0].paused, false, 'Let the last voiced part finish before the next sign');
  assert.equal(state.speaking, true);
  clips[0].ended = true; clips[0].paused = true; clips[0].onended();
  narrator.tick(p, true, true, 2600, .02);
  narrator.tick(p, true, true, 4000, .02);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(events.filter(e => e.type === 'playing').length, 2, 'A new cue identity reads a repeated word');
  narrator.dispose();
});
