/* Standalone QA of the actual packaged EXE via its opt-in debugging endpoint. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '..');
const endpoint = 'http://127.0.0.1:58901';
const version = process.argv[2] || '0.3.5';
const evidenceName = process.argv[3] || 'patient-voice-packaged-2026-11-01';
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let doctorSocket;
const report = { scope: `Actual ${version} Windows EXE, bundled engine/assets/audio, prerecorded sign video, fake silent microphone.` };
async function waitFor(fn, timeout = 60000) {
  const start = Date.now();
  while (Date.now() - start < timeout) { const result = await fn(); if (result) return result; await delay(80); }
  throw new Error('Timed out');
}
try {
  const target = await waitFor(async () => {
    try { return (await (await fetch(endpoint + '/json')).json()).find(p => p.type === 'page' && new URL(p.url).pathname === '/doctor'); }
    catch { return null; }
  });
  const url = new URL(target.url), origin = url.origin;
  const headers = { Authorization: 'Bearer ' + url.searchParams.get('token') };
  doctorSocket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(resolve => doctorSocket.addEventListener('open', resolve, { once: true }));
  let sequence = 0;
  const pending = new Map();
  doctorSocket.addEventListener('message', event => {
    const response = JSON.parse(event.data);
    if (response.id && pending.has(response.id)) { pending.get(response.id)(response); pending.delete(response.id); }
  });
  async function evaluate(expression) {
    const id = ++sequence;
    const response = new Promise(resolve => pending.set(id, resolve));
    doctorSocket.send(JSON.stringify({ id, method: 'Runtime.evaluate', params: { expression, returnByValue: true, awaitPromise: true } }));
    const value = await response;
    if (value.error || value.result.exceptionDetails) throw new Error(JSON.stringify(value));
    return value.result.result.value;
  }
  async function api(endpoint, body) {
    const response = await fetch(origin + '/api' + endpoint, { method: body === undefined ? 'GET' : 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }
  await waitFor(async () => (await api('/bootstrap')).state.clients.patient > 0);
  const bankResponse = await fetch(origin + '/assets/patient-voice/manifest.json');
  const bank = await bankResponse.json();
  assert.equal(bank.entries.length, 401);
  report.bundledVoiceClips = bank.entries.length;
  report.voice = bank.voice;
  assert.ok((await evaluate('document.body.innerText')).includes('Demo ' + version));
  await api('/session/reset', {});
  await api('/conversation/configure', { mode: 'auto', source: { kind: 'demo', demo_id: '395' } });
  await api('/conversation/start', {});
  let result, microphonePaused = false, readBeforeTurnFinished = false;
  await waitFor(async () => {
    result = await api('/diagnostics');
    const view = await evaluate('({text:document.body.innerText,voice:window.clinicDiagnostics?.patientVoice??[]})');
    microphonePaused ||= view.text.includes('Tạm ngừng micro khi đọc ký hiệu');
    readBeforeTurnFinished ||= !!result.state.patient_turn && view.voice.some(e => e.type === 'playing');
    return result.state.capture.status === 'ended' && view.voice.some(e => e.type === 'ended');
  });
  await waitFor(async () => (await evaluate('document.body.innerText')).includes('Đang nghe bác sĩ'));
  const events = await evaluate('window.clinicDiagnostics.patientVoice');
  const played = events.filter(e => e.type === 'playing');
  assert.deepEqual(played.map(e => e.text), ['Đồng ý']);
  assert.ok(microphonePaused); assert.ok(readBeforeTurnFinished);
  assert.equal(result.state.speech_drafts.length, 0);
  assert.equal(result.state.messages.filter(m => m.role === 'doctor').length, 0);
  // A deliberate mute stays off through another readout.
  await evaluate(`document.querySelector('.live-speech-status button').click()`);
  await delay(200);
  const file = path.join(root, 'demo/HAI_KICH_BAN_2026-10-31/02_Nhu_cau_va_ho_tro/04_Tra_loi/CAU_TRA_LOI.mp4');
  const form = new FormData();
  form.append('file', new Blob([fs.readFileSync(file)], {type:'video/mp4'}), 'reply.mp4');
  const upload = await fetch(origin + '/api/capture/upload', { method:'POST',headers,body:form });
  assert.ok(upload.ok);
  await waitFor(async () => (await evaluate('window.clinicDiagnostics.patientVoice')).filter(e => e.type === 'ended').length === 4);
  await delay(900);
  assert.match(await evaluate('document.body.innerText'), /Micro đang tắt/u);
  report.events = await evaluate('window.clinicDiagnostics.patientVoice');
  report.played = report.events.filter(e => e.type === 'playing').map(e => ({word:e.text, latency_ms:e.latency_ms}));
  assert.deepEqual(report.played.map(e => e.word), ['Đồng ý','Mệt','Cần','Nghỉ ngơi']);
  report.microphonePaused = microphonePaused;
  report.microphoneResumed = true;
  report.manualMutePreserved = true;
  report.readBeforeTurnFinished = readBeforeTurnFinished;
  report.passed = true;
  fs.writeFileSync(path.join(root, `docs/evidence/${evidenceName}.json`), JSON.stringify(report,null,2));
  console.log(JSON.stringify(report));
  await api('/conversation/stop', {});
  await evaluate('window.clinicDesktop.quit()');
  doctorSocket.close();
} catch(error) {
  report.error = String(error.stack || error);
  fs.writeFileSync(path.join(root, `docs/evidence/${evidenceName}-failed.json`), JSON.stringify(report,null,2));
  doctorSocket?.close();
  console.error(error);
  process.exitCode = 1;
}
