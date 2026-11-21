/* Bounded actual-EXE acceptance: passive screen, lazy assets, motion/voice and lifecycle. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const args = Object.fromEntries(process.argv.slice(2).map(value => value.replace(/^--/, '').split('=')));
const output = path.resolve(args.output);
fs.mkdirSync(output, { recursive: true });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const sockets = [];
const report = { checks: {}, cases: [], scope: 'Actual EXE, synthetic doctor text and bundled sign video. No live signer or microphone claim.' };
const until = async (fn, limit = 60000) => {
  const start = Date.now();
  while (Date.now() - start < limit) { const result = await fn(); if (result) return result; await delay(100); }
  throw Error('Timeout: ' + fn.toString().slice(0, 140));
};
async function connect(target) {
  const ws = new WebSocket(target.webSocketDebuggerUrl); sockets.push(ws);
  await new Promise(resolve => ws.addEventListener('open', resolve, { once: true }));
  let sequence = 0; const pending = new Map();
  ws.addEventListener('message', event => { const value = JSON.parse(event.data); pending.get(value.id)?.(value); });
  const call = async (method, params = {}) => {
    const id = ++sequence; let timer;
    const promise = new Promise((resolve, reject) => { pending.set(id, resolve); timer = setTimeout(() => reject(Error('CDP timeout')), 20000); });
    ws.send(JSON.stringify({ id, method, params }));
    const result = await promise.finally(() => { clearTimeout(timer); pending.delete(id); });
    if (result.error) throw Error(JSON.stringify(result.error));
    return result.result;
  };
  return { call, eval: async expression => {
    const result = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  } };
}
try {
  const pages = await until(async () => { try {
    const all = await (await fetch(`http://127.0.0.1:${args.port || 58964}/json`)).json();
    const relevant = all.filter(row => row.type === 'page' && /\/(doctor|patient)\?/.test(row.url));
    return relevant.length === 2 ? relevant : null;
  } catch { return null; } });
  const doctorPage = pages.find(p => p.url.includes('/doctor?'));
  const doctor = await connect(doctorPage), patient = await connect(pages.find(p => p.url.includes('/patient?')));
  const url = new URL(doctorPage.url);
  const headers = { Authorization: 'Bearer ' + url.searchParams.get('token'), 'Content-Type': 'application/json' };
  const api = async (route, body) => {
    const response = await fetch(url.origin + '/api' + route, { method: body === undefined ? 'GET' : 'POST', headers,
      body: body === undefined ? undefined : JSON.stringify(body) });
    if (!response.ok) throw Error(await response.text());
    return response.json();
  };
  const state = async () => (await api('/diagnostics')).state;
  await until(() => patient.eval('!!window.clinicDiagnostics?.mouthExpressions'));
  await delay(500);
  report.version = (await (await fetch(url.origin + '/healthcheck')).json()).version;
  for (const [name, page] of [['doctor', doctor], ['patient', patient]]) {
    await page.call('HeapProfiler.collectGarbage');
    report[name] = { heap: await page.call('Runtime.getHeapUsage'), ...await page.eval(`({
      motionRequests: performance.getEntriesByType('resource').filter(e=>e.name.includes('/assets/motions/')).length,
      scriptBytes: performance.getEntriesByType('resource').filter(e=>e.name.includes('/ui-assets/')&&e.name.includes('.js')).reduce((n,e)=>n+e.decodedBodySize,0),
      controls: [...document.querySelectorAll('button,a,input,textarea,select,[role=button],[contenteditable=true]')].length,
      width: innerWidth, height: innerHeight, bodyWidth: document.body.scrollWidth
    })`) };
  }
  if (args.mode === 'baseline' || args.mode === 'close') {
    report.passed = true;
    await doctor.eval('setTimeout(() => window.clinicDesktop.quit(), 100); true');
  } else {
    assert.equal(report.version, args.version || '0.6.4');
    assert.equal(report.patient.controls, 0);
    assert.equal(report.patient.motionRequests, 0);
    assert.equal(await patient.eval("/VSL100|100 từ|400 từ|fusion|sign.only/i.test(document.body.innerText)"), false);
    report.checks.passivePatient = report.checks.lazyMotionsAtStartup = true;
    const bootstrap = await api('/bootstrap');
    assert.equal(bootstrap.vocabulary.length, Number(args.vocabulary || 80));
    report.quickPhrases = bootstrap.quick_phrases.length;
    await api('/session/reset', {});
    const cases = [
      ['Đồng ý nằm nghỉ ngơi', ['Đồng ý', 'Nằm', 'Nghỉ ngơi']],
      ['Bạn có đau mắt không? Bạn có đau tai không?', ['Đau mắt', 'Đau tai']],
      ['Bạn cần đi vệ sinh không? Bạn muốn ăn uống không?', ['Cần', 'Nhà vệ sinh', 'Đi', 'Muốn', 'Ăn uống']],
      ['Bác sĩ băng bó. Y tá tiêm. Gọi cấp cứu. Khẩu trang.', ['Bác sĩ', 'Băng bó', 'Y tá', 'Tiêm', 'Cấp cứu', 'Gọi', 'Khẩu trang']],
    ];
    if (args.product === 'true') cases.push(
      ['Bạn có đau bụng không?', ['Bụng', 'Đau']],
      ['Bạn cần gối không? Bạn cần chăn không?', ['Cần', 'Gối (đầu)', 'Cần', 'Mền']],
      ['Bạn muốn rửa mặt không? Bạn muốn gội đầu không? Bạn muốn tắm rửa không?', ['Muốn', 'Rửa mặt', 'Muốn', 'Gội đầu', 'Muốn', 'Tắm rửa']],
    );
    for (const [text, expected] of cases) {
      assert.equal((await api('/text/plan', { text })).supported, true);
      await api('/messages', { text, mode: 'sign' });
      const playback = await until(async () => { const p = (await state()).playback; return p?.text === text && p.status === 'playing' ? p : null; });
      assert.deepEqual(playback.glosses.map(g => g.label), expected);
      const row = { text, expected, audioEvents: [], mouthSeen: false }; report.cases.push(row);
      await until(async () => {
        const n = await patient.eval('window.clinicDiagnostics?.narration');
        if (n?.speaking && Object.values(n.mouth).some(v => v > .01)) row.mouthSeen = true;
        row.audioEvents = n?.events.filter(e => e.type === 'playing' && e.cycle === playback.id + ':' + playback.iteration) ?? [];
        return (await state()).playback?.status === 'completed';
      }, 90000);
      assert.equal(row.audioEvents.length, expected.length);
      assert.ok(row.mouthSeen);
      row.maximumVoiceOffsetMs = Math.max(...row.audioEvents.map((e, index) => Math.abs(e.timeline_ms - playback.audio_cues[index].start_ms)));
      assert.ok(row.maximumVoiceOffsetMs < 250);
    }
    report.checks.wordsVoiceAndMouth = true;
    // Pause/replay/reset after a lazy-loaded sentence still uses the shared clock.
    await api('/messages', { text: cases[0][0], mode: 'sign' });
    let playback = await until(async () => { const p = (await state()).playback; return p?.status === 'playing' ? p : null; });
    await api('/playback', { action: 'pause', playback_id: playback.id });
    await delay(350);
    assert.equal((await state()).playback.status, 'paused');
    await api('/playback', { action: 'resume', playback_id: playback.id });
    await delay(200);
    assert.equal((await state()).playback.status, 'playing');
    await api('/session/reset', {});
    assert.equal((await state()).playback, null);
    await delay(300);
    assert.equal(await patient.eval('window.clinicDiagnostics?.narration.speaking'), false);
    report.checks.resetStopsVoice = true;
    await api('/recognition/mode', { mode: 'sign_only' });
    assert.equal((await state()).recognition.mode, 'sign_only');
    await api('/recognition/mode', { mode: 'fusion' });
    await until(async () => (await state()).recognition.status === 'ready', 90000);
    report.checks.modeSwitch = true;
    await api('/conversation/configure', { mode: 'auto', source: { kind: 'demo', demo_id: 'mm100:W068' } });
    await api('/conversation/start', {});
    await until(async () => (await state()).capture.status === 'ended', 90000);
    await until(() => doctor.eval("(window.clinicDiagnostics?.patientVoice ?? []).some(e=>e.type==='ended'&&e.text==='Sốt')"), 90000);
    report.patientVideo = { words: (await state()).messages.filter(m => m.role === 'patient').flatMap(m => m.words ?? [m]).map(w => w.text),
      voiceEvents: await doctor.eval('window.clinicDiagnostics?.patientVoice ?? []') };
    assert.ok(report.patientVideo.words.includes('Sốt'));
    assert.equal(report.patientVideo.voiceEvents.filter(e => /warning|beep/.test(e.type)).length, 0);
    report.checks.patientVideoAndImmediateVoice = true;
    await api('/session/reset', {});
    assert.equal((await state()).messages.length, 0);
    // Read all UI text in both languages without changing signed Vietnamese.
    await doctor.eval("window.clinicDesktop.setInterfaceLanguage('en')");
    await delay(200);
    report.patientEnglish = await patient.eval('document.body.innerText');
    assert.ok(report.patientEnglish.includes('Ready for the doctor') || report.patientEnglish.includes('Ready to listen to your doctor'));
    assert.equal(await patient.eval("document.querySelectorAll('button,a,input,select,textarea').length"), 0);
    await doctor.eval("window.clinicDesktop.setInterfaceLanguage('vi')");
    for (const [name, page] of [['doctor', doctor], ['patient', patient]]) {
      const shot = await page.call('Page.captureScreenshot', { format: 'png' });
      fs.writeFileSync(path.join(output, name + '.png'), Buffer.from(shot.data, 'base64'));
    }
    report.passed = true;
    if (args.quit === 'true') await doctor.eval('setTimeout(() => window.clinicDesktop.quit(), 100); true');
  }
} catch (error) { report.passed = false; report.error = String(error.stack ?? error); process.exitCode = 1; }
finally { sockets.forEach(socket => socket.close()); fs.writeFileSync(path.join(output, 'probe.json'), JSON.stringify(report, null, 2)); console.log(JSON.stringify(report)); }
