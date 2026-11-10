/* Exercise the shipping EXE through its opt-in local debugging endpoint. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '..');
const endpoint = 'http://127.0.0.1:58901';
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const report = { scope: 'Actual 0.3.7 EXE and bundled engine; prerecorded video, silent test microphone; no live signer validation.', checks: {} };
const sockets = [];
async function until(fn, timeout = 60000) {
  const start = Date.now();
  while (Date.now() - start < timeout) { const value = await fn(); if (value) return value; await delay(100); }
  throw new Error('Timed out');
}
async function connect(target) {
  const socket = new WebSocket(target.webSocketDebuggerUrl); sockets.push(socket);
  await new Promise(resolve => socket.addEventListener('open', resolve, { once: true }));
  let sequence = 0; const pending = new Map();
  socket.addEventListener('message', event => {
    const response = JSON.parse(event.data);
    if (response.id && pending.has(response.id)) { pending.get(response.id)(response); pending.delete(response.id); }
  });
  return async expression => {
    const id = ++sequence;
    let timer;
    const response = new Promise((resolve, reject) => {
      pending.set(id, resolve);
      timer = setTimeout(() => { pending.delete(id); reject(new Error('CDP timed out: ' + expression.slice(0, 70))); }, 15000);
    });
    socket.send(JSON.stringify({ id, method: 'Runtime.evaluate', params: { expression, returnByValue: true, awaitPromise: true } }));
    const value = await response.finally(() => clearTimeout(timer));
    if (value.error || value.result.exceptionDetails) throw new Error(JSON.stringify(value));
    return value.result.result.value;
  };
}
try {
  const pages = await until(async () => {
    try { const targets = await (await fetch(endpoint + '/json')).json(); return targets.filter(p => p.type === 'page' && /^\/(doctor|patient)$/.test(new URL(p.url).pathname)).length === 2 ? targets : null; }
    catch { return null; }
  });
  const doctor = pages.find(p => new URL(p.url).pathname === '/doctor');
  const patient = pages.find(p => new URL(p.url).pathname === '/patient');
  const evaluate = await connect(doctor), patientEvaluate = await connect(patient);
  const url = new URL(doctor.url), headers = { Authorization: 'Bearer ' + url.searchParams.get('token'), 'Content-Type': 'application/json' };
  async function api(route, body) {
    const response = await fetch(url.origin + '/api' + route, { method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body) });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }
  const state = async () => (await api('/diagnostics')).state;
  await until(async () => (await state()).clients.patient > 0);
  const health = await (await fetch(url.origin + '/healthcheck')).json();
  assert.equal(health.version, '0.3.7');
  assert.match(await evaluate('document.body.innerText'), /Demo 0\.3\.7/);
  report.checks.version = true;
  await api('/session/reset', {});
  await api('/conversation/configure', { mode: 'auto', source: { kind: 'demo', demo_id: '395' } });
  await api('/conversation/start', {});
  await until(async () => (await state()).capture.status === 'ended');
  const sent = await api('/messages', { text: 'Y tá đo nhiệt độ.', mode: 'sign' });
  await until(async () => (await state()).playback?.status === 'playing');
  const id = (await state()).playback.id;
  await delay(500); await api('/playback', { action: 'pause', playback_id: id }); await delay(200);
  const percent = async () => evaluate("Number(document.querySelector('[role=progressbar]')?.getAttribute('aria-valuenow'))");
  const frozen = await percent(); await delay(500); assert.equal(await percent(), frozen);
  assert.match(await evaluate("document.querySelector('[data-testid=avatar-progress]').innerText"), /1\/3.*Y tá/);
  await api('/playback', { action: 'speed', playback_id: id, rate: 0.5 });
  await api('/playback', { action: 'resume', playback_id: id }); await delay(700); assert.ok(await percent() > frozen);
  await until(async () => (await state()).messages.find(m => m.id === sent.id).status === 'completed');
  await until(async () => (await percent()) === 100);
  report.checks.playbackPauseSpeedCompletion = true;
  await api('/playback', { action: 'replay', playback_id: id });
  await until(async () => (await state()).playback?.status === 'playing'); assert.ok(await percent() < 25);
  await api('/messages', { text: 'Cảm ơn.', mode: 'sign' });
  await until(async () => (await state()).pending_count > 0);
  report.checks.replayAndQueue = true;
  const before = await state();
  await evaluate("document.querySelector('.keep-temporary input').click()");
  await evaluate("Array.from(document.querySelectorAll('.conversation-bar button')).find(b=>b.textContent==='Kết thúc').click()");
  await until(async () => (await state()).session_id !== before.session_id); await delay(1800);
  const ended = await state();
  assert.equal(ended.messages.length, 0); assert.equal(ended.speech_drafts.length, 0);
  assert.equal(ended.pending_count, 0); assert.equal(ended.playback, null);
  assert.equal(ended.current_result, null); assert.equal(ended.capture.status, 'idle');
  assert.equal(await evaluate("document.querySelector('[aria-label=\"Nội dung gửi người bệnh\"]').value"), '');
  assert.equal(await evaluate("!!document.querySelector('[role=progressbar]')"), false);
  assert.match(await patientEvaluate('document.body.innerText'), /Lời nhắn của bác sĩ sẽ xuất hiện ở đây/);
  assert.equal(await evaluate("document.querySelector('.live-speech-status')?.innerText.includes('Đang nghe bác sĩ') || false"), false);
  report.checks.endClearsBothWindows = true;
  assert.ok(ended.temporary);
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()==='Bản tạm').click()");
  await until(async () => evaluate("!!document.querySelector('.temporary-conversation .message')"));
  const saved = await api('/session/temporary');
  assert.ok(saved.messages.some(m => m.text === 'Y tá đo nhiệt độ.'));
  assert.equal((await state()).messages.length, 0);
  assert.ok(saved.messages.filter(m => m.role === 'doctor').every(m => m.status === 'cancelled'));
  await evaluate("Array.from(document.querySelectorAll('dialog[open] button')).find(b=>b.textContent==='Xóa bản tạm').click()");
  await until(async () => !(await state()).temporary);
  report.checks.temporaryReadOnlyAndDelete = true;
  await api('/conversation/start', {}); await delay(200);
  assert.equal(await evaluate("document.querySelector('.keep-temporary input').checked"), false);
  await api('/messages', { text: 'Cảm ơn.', mode: 'sign' });
  await api('/conversation/stop', {}); await delay(2000);
  const clean = await state();
  assert.equal(clean.messages.length, 0); assert.equal(clean.temporary, null);
  assert.equal(clean.playback, null); assert.equal(clean.speech_drafts.length, 0); assert.equal(clean.current_result, null);
  report.checks.defaultEndAndLateEvents = true;
  report.passed = true;
  fs.writeFileSync(path.join(root, 'docs/evidence/workspace-037-packaged.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report));
  void evaluate('setTimeout(()=>window.clinicDesktop.quit(), 150); true');
  await delay(500);
} catch (error) {
  report.error = String(error.stack || error);
  fs.writeFileSync(path.join(root, 'docs/evidence/workspace-037-packaged-failed.json'), JSON.stringify(report, null, 2));
  console.error(error); process.exitCode = 1;
} finally { for (const socket of sockets) socket.close(); }
