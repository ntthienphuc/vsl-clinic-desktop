/* Run with Electron. Exercises the real renderer, detector/model and audio output. */
const { app, BrowserWindow, session } = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
// A test runner must not leave Chromium utility processes after its report.
app.on('will-quit', () => setTimeout(() => app.exit(process.exitCode || 0), 1500));
process.env.CLINIC_QA = '1';
process.env.CLINIC_QA_PORT = '58897';
app.setPath('userData', path.join(root, 'research/cache/voice-qa-profile'));
app.commandLine.appendSwitch('use-fake-device-for-media-stream');
app.commandLine.appendSwitch('use-file-for-fake-audio-capture', path.join(root, 'research/cache/mic-silence.wav'));
require('../desktop/main.cjs');
const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const origin = 'http://127.0.0.1:58897';
const headers = { Authorization: 'Bearer clinic-test-session' };
const report = { scope: 'Real Electron UI, real prerecorded-video inference, local WAV output, fake silent microphone; not human microphone or signer validation.', cases: [] };
async function api(endpoint, body) {
  const r = await fetch(origin + '/api' + endpoint, { method: body === undefined ? 'GET' : 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
async function until(fn, max = 30000) {
  const started = Date.now();
  while (Date.now() - started < max) { const value = await fn(); if (value) return value; await wait(60); }
  throw new Error('Timed out waiting for test state');
}
void app.whenReady().then(async () => {
  await until(async () => { try { return (await api('/bootstrap')).state.clients.patient > 0; } catch { return false; } }, 90000);
  const doctor = BrowserWindow.getAllWindows().find(w => new URL(w.webContents.getURL()).pathname === '/doctor');
  assert.ok(doctor);
  doctor.setContentSize(1280, 720);
  const externalRequests = [];
  session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
    const external = /^https?:/u.test(details.url) && !details.url.startsWith(origin + '/');
    if (external) externalRequests.push(details.url);
    callback({ cancel: external });
  });
  // Keep all software audio online during the test; block every external request.
  await api('/session/reset', {});
  await api('/conversation/configure', { mode: 'auto', source: { kind: 'demo', demo_id: '395' } });
  await api('/conversation/start', {});
  await until(async () => (await doctor.webContents.executeJavaScript('document.body.innerText')).includes('Đang nghe bác sĩ'));
  const kit = path.join(root, 'demo/HAI_KICH_BAN_2026-10-31');
  const cases = [
    { clip: '01_Tiep_don_va_hoi_trieu_chung/01_Tra_loi/CAU_TRA_LOI.mp4', expected: ['Đồng ý'] },
    { clip: '02_Nhu_cau_va_ho_tro/04_Tra_loi/CAU_TRA_LOI.mp4', expected: ['Mệt', 'Cần', 'Nghỉ ngơi'] },
  ];
  // Finish the initial demo started with the microphone before measuring cases.
  await until(async () => (await api('/diagnostics')).state.capture.status === 'ended');
  await wait(2000);
  for (const input of cases) {
    const before = (await api('/diagnostics')).state;
    const known = new Set(before.messages.flatMap(m => m.words ?? []).map(w => w.id));
    const form = new FormData();
    form.append('file', new Blob([fs.readFileSync(path.join(kit, input.clip))], { type: 'video/mp4' }), 'reply.mp4');
    const uploaded = await fetch(origin + '/api/capture/upload', { method: 'POST', headers, body: form });
    assert.equal(uploaded.ok, true, await uploaded.text());
    let audible = false, micBlocked = false;
    const firstStatuses = {};
    let current;
    await until(async () => {
      current = (await api('/diagnostics')).state;
      const voice = await doctor.webContents.executeJavaScript('({events:window.clinicDiagnostics?.patientVoice??[],text:document.body.innerText})');
      audible ||= doctor.webContents.isCurrentlyAudible();
      micBlocked ||= voice.text.includes('Tạm ngừng micro khi đọc ký hiệu');
      for (const turn of current.messages) for (const word of turn.words ?? []) {
        if (!known.has(word.id) && !firstStatuses[word.id]) firstStatuses[word.id] = turn.status;
      }
      return current.capture.status === 'ended' && !current.patient_turn && voice.events.filter(e => e.type === 'ended' && !known.has(e.message_id)).length >= input.expected.length;
    }, 45000);
    const words = current.messages.flatMap(m => m.words ?? []).filter(w => !known.has(w.id));
    const events = (await doctor.webContents.executeJavaScript('window.clinicDiagnostics.patientVoice')).filter(e => words.some(w => w.id === e.message_id));
    const played = events.filter(e => e.type === 'playing');
    assert.deepEqual(words.map(w => w.text), input.expected);
    assert.deepEqual(played.map(e => e.text), input.expected);
    assert.ok(audible); assert.ok(micBlocked);
    assert.ok(Object.values(firstStatuses).every(status => status === 'streaming'));
    assert.equal(current.messages.filter(m => m.role === 'doctor').length, 0);
    assert.equal(current.speech_drafts.length, 0);
    await until(async () => (await doctor.webContents.executeJavaScript('document.body.innerText')).includes('Đang nghe bác sĩ'));
    report.cases.push({ ...input, words: words.map(w => ({ text: w.text, uncertain: w.uncertain })), played, audible, micBlocked, firstStatuses, microphoneResumed: true, noSpeechFeedback: true });
    console.log(JSON.stringify(report.cases.at(-1)));
  }
  report.externalRequests = externalRequests;
  assert.equal(externalRequests.length, 0);
  report.passed = true;
  report.layouts = [];
  await api('/messages', { text: 'Bác sĩ đo nhiệt độ.', mode: 'sign' });
  await wait(400);
  for (const [width, height] of [[1280, 720], [1920, 1080]]) {
    for (const window of BrowserWindow.getAllWindows()) {
      const role = new URL(window.webContents.getURL()).pathname.slice(1);
      window.setContentSize(width, height);
      await wait(250);
      const layout = await window.webContents.executeJavaScript(`(() => {
        const root = document.documentElement;
        const words = document.querySelector('.live-word-list > span');
        const caption = document.querySelector('.doctor-caption');
        return {width:innerWidth,height:innerHeight,scrollWidth:root.scrollWidth,scrollHeight:root.scrollHeight,
          wordFont:words?getComputedStyle(words).fontSize:null, captionFont:caption?getComputedStyle(caption).fontSize:null};
      })()`);
      assert.ok(layout.scrollHeight <= layout.height + 1, JSON.stringify(layout));
      assert.ok(layout.scrollWidth <= layout.width + 1, JSON.stringify(layout));
      report.layouts.push({role,...layout});
      fs.writeFileSync(path.join(root, `docs/evidence/patient-voice-${role}-${width}.png`), (await window.webContents.capturePage()).toPNG());
    }
  }
  await api('/conversation/stop', {});
  fs.writeFileSync(path.join(root, 'docs/evidence/patient-voice-smoke-2026-11-01.json'), JSON.stringify(report, null, 2));
  fs.writeFileSync(path.join(root, 'docs/evidence/patient-voice-035.png'), (await doctor.webContents.capturePage()).toPNG());
  app.quit();
  setTimeout(() => app.exit(0), 6000);
}).catch(error => {
  report.error = error.stack;
  fs.writeFileSync(path.join(root, 'docs/evidence/patient-voice-smoke-2026-11-01-failed.json'), JSON.stringify(report, null, 2));
  console.error(error);
  process.exitCode = 1;
  app.quit();
  setTimeout(() => app.exit(1), 6000);
});
