'use strict';

const { app, BrowserWindow, dialog, ipcMain, screen, session, shell } = require('electron');
const { spawn } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');

// On hybrid laptops keep the avatar on the high-performance adapter so its
// rendering does not take the integrated GPU's shared CPU power/bandwidth.
// Chromium falls back normally when no such adapter is available.
app.commandLine.appendSwitch('force-high-performance-gpu');

const project = path.resolve(__dirname, '..');
const qaMode = !app.isPackaged && process.env.CLINIC_QA === '1';
const sessionToken = qaMode ? 'clinic-test-session' : crypto.randomBytes(32).toString('hex');
const windows = new Map();
let engine = null;
let origin = '';
let shuttingDown = false;
let allowQuit = false;
let logStream = null;
let engineExit = null;
let launchDetails = {};
let interfaceLanguage = null;
let swappedDisplays = false;
const uiText = (vi, en) => interfaceLanguage?.get() === 'en' ? en : vi;

function log(message) {
  logStream?.write(`${new Date().toISOString()} ${message}\n`);
}

function reservePort() {
  return new Promise((resolve, reject) => {
    const listener = net.createServer();
    listener.once('error', reject);
    listener.listen(qaMode ? Number(process.env.CLINIC_QA_PORT || 8766) : 0, '127.0.0.1', () => {
      const port = listener.address().port;
      listener.close(() => resolve(port));
    });
  });
}

async function startEngine() {
  const port = await reservePort();
  const assets = app.isPackaged ? path.join(process.resourcesPath, 'assets') : path.join(project, 'assets');
  const frontend = app.isPackaged ? path.join(process.resourcesPath, 'frontend') : path.join(project, 'dist');
  const executable = app.isPackaged
    ? path.join(process.resourcesPath, 'engine', 'ClinicEngine.exe')
    : path.join(project, '.venv', 'Scripts', 'python.exe');
  const cwd = app.isPackaged ? process.resourcesPath : project;
  launchDetails = { executable, cwd, enginePresent: fs.existsSync(executable), frontendPresent: fs.existsSync(path.join(frontend, 'index.html')) };
  if (!fs.existsSync(executable) || !fs.existsSync(path.join(frontend, 'index.html'))) {
    throw new Error(app.isPackaged
      ? uiText('Ứng dụng thiếu một thành phần cần thiết. Hãy chạy lại bộ cài VSL Clinic để sửa bản cài đặt.', 'An app component is missing. Run the VSL Clinic installer again to repair the installation.')
      : 'Thiếu bộ chạy hoặc giao diện. Hãy chạy tools/setup.ps1 và npm run build trong thư mục dự án.');
  }
  const args = app.isPackaged ? ['--port', String(port)] : ['-u', '-X', 'utf8', path.join(project, 'backend', 'main.py'), '--port', String(port)];
  let computeMode = process.env.CLINIC_COMPUTE || 'auto';
  if (app.isPackaged && !process.env.CLINIC_COMPUTE) {
    try {
      const preference = JSON.parse(fs.readFileSync(path.join(path.dirname(process.execPath), 'runtime-preference.json'), 'utf8'));
      if (['cpu', 'gpu'].includes(preference.compute)) computeMode = preference.compute;
    } catch { /* Older portable packages keep automatic detection. */ }
  }
  launchDetails.compute = computeMode;
  engine = spawn(executable, args, {
    cwd,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, CLINIC_COMPUTE: computeMode, CLINIC_ASSETS: assets, CLINIC_FRONTEND: frontend, CLINIC_TOKEN: sessionToken, PYTHONUNBUFFERED: '1', PYTHONUTF8: '1' },
  });
  engine.on('error', (error) => {
    engineExit = error.message;
    Object.assign(launchDetails, { code: error.code, errno: error.errno, syscall: error.syscall });
    log(`engine error: ${error.message}`);
  });
  engine.on('exit', (code, signal) => {
    Object.assign(launchDetails, { exitCode: code, signal });
    engineExit = `exit ${code}, signal ${signal}`;
    log(`engine ${engineExit}`);
    if (windows.size > 0 && !shuttingDown) {
      dialog.showErrorBox(uiText('VSL Clinic · Dịch vụ đã dừng', 'VSL Clinic · Service stopped'), uiText('Bộ nhận dạng trên máy đã dừng. Hãy đóng và mở lại ứng dụng. Chi tiết nằm trong tệp clinic-engine.log của ứng dụng.', 'Local recognition has stopped. Close and reopen the app. Details are in the app’s clinic-engine.log file.'));
    }
  });
  engine.stdout.on('data', (data) => log(data.toString().trimEnd()));
  engine.stderr.on('data', (data) => log(data.toString().trimEnd()));
  origin = `http://127.0.0.1:${port}`;
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    if (engineExit !== null) {
      throw new Error(uiText(`Bộ nhận dạng chưa khởi động được (${engineExit}). Xem clinic-engine.log.`, `Recognition could not start (${engineExit}). See clinic-engine.log.`));
    }
    try {
      const response = await fetch(`${origin}/api/ready`, {
        headers: { Authorization: `Bearer ${sessionToken}` },
        signal: AbortSignal.timeout(700),
      });
      if (response.ok && (await response.json()).version === app.getVersion()) {
        log(`ready at ${origin}; recognition=managed multimodal worker`);
        return;
      }
    } catch {
      // The local model is still loading.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(uiText('Bộ nhận dạng chưa sẵn sàng sau 60 giây.', 'Recognition was not ready after 60 seconds.'));
}

function layout(swap = swappedDisplays) {
  swappedDisplays = swap;
  const displays = screen.getAllDisplays();
  const primary = screen.getPrimaryDisplay();
  const secondary = displays.find((display) => display.id !== primary.id);
  let doctorBounds;
  let patientBounds;
  if (secondary) {
    doctorBounds = { ...primary.workArea };
    patientBounds = { ...secondary.workArea };
  } else {
    const area = primary.workArea;
    const firstWidth = Math.floor(area.width / 2);
    doctorBounds = { x: area.x, y: area.y, width: firstWidth, height: area.height };
    patientBounds = { x: area.x + firstWidth, y: area.y, width: area.width - firstWidth, height: area.height };
  }
  if (swap) {
    [doctorBounds, patientBounds] = [patientBounds, doctorBounds];
  }
  for (const [role, bounds] of [['doctor', doctorBounds], ['patient', patientBounds]]) {
    const window = windows.get(role);
    if (window && !window.isDestroyed()) {
      window.setFullScreen(false);
      window.unmaximize();
      window.setBounds(bounds);
      window.show();
    }
  }
}

function openWindow(role) {
  const existing = windows.get(role);
  if (existing && !existing.isDestroyed()) {
    existing.show();
    existing.focus();
    return existing;
  }
  const window = new BrowserWindow({
    title: role === 'doctor' ? uiText('VSL Clinic · Bác sĩ', 'VSL Clinic · Doctor') : uiText('VSL Clinic · Người bệnh', 'VSL Clinic · Patient'),
    backgroundColor: '#f3f6f5',
    minWidth: 570,
    minHeight: 600,
    width: 1100,
    height: 850,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      backgroundThrottling: false,
      spellcheck: false,
      autoplayPolicy: 'no-user-gesture-required',
    },
  });
  windows.set(role, window);
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event, url) => {
    if (new URL(url).origin !== origin) {
      event.preventDefault();
    }
  });
  window.webContents.on('console-message', (details) => {
    if (details.level === 'error' || details.level === 'warning') {
      log(`renderer:${role} ${details.level}: ${details.message}`);
    }
  });
  window.webContents.on('render-process-gone', (_event, details) => log(`renderer:${role} gone ${details.reason}`));
  window.once('ready-to-show', () => {
    layout();
    window.show();
  });
  window.on('closed', () => {
    windows.delete(role);
  });
  void window.loadURL(`${origin}/${role}?token=${encodeURIComponent(sessionToken)}`);
  return window;
}

function trustedWindow(event) {
  const window = BrowserWindow.fromWebContents(event.sender);
  if (!window || ![...windows.values()].includes(window)) {
    throw new Error('Unknown desktop window');
  }
  return window;
}

function doctorAudioOrigin(webContents, url) {
  const doctor = windows.get('doctor');
  if (!doctor || doctor.isDestroyed() || doctor.webContents !== webContents) {
    return false;
  }
  try {
    const requesting = new URL(url);
    return requesting.origin === origin && new URL(webContents.getURL()).pathname === '/doctor';
  } catch {
    return false;
  }
}

function installPermissions() {
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback, details) => {
    const audioOnly = details.mediaTypes?.length === 1 && details.mediaTypes[0] === 'audio';
    callback(permission === 'media' && audioOnly && details.isMainFrame !== false && doctorAudioOrigin(webContents, details.requestingUrl));
  });
  session.defaultSession.setPermissionCheckHandler((webContents, permission, requestingOrigin, details) => {
    return permission === 'media' && details.mediaType === 'audio' && details.isMainFrame !== false && doctorAudioOrigin(webContents, requestingOrigin);
  });
}

function installIPC() {
  interfaceLanguage = require('./interface-language.cjs')(app.getPath('userData'));
  ipcMain.handle('clinic:interface-language:get', (event) => {
    trustedWindow(event);
    return interfaceLanguage.get();
  });
  ipcMain.handle('clinic:interface-language:set', (event, language) => {
    trustedWindow(event);
    const saved = interfaceLanguage.set(language);
    for (const window of windows.values()) {
      if (!window.isDestroyed()) window.webContents.send('clinic:interface-language:changed', saved);
    }
    return saved;
  });
  ipcMain.handle('clinic:displays', (event) => {
    trustedWindow(event);
    const primary = screen.getPrimaryDisplay().id;
    return screen.getAllDisplays().map((display, index) => ({ id: display.id, label: display.label || `Màn hình ${index + 1}`, primary: display.id === primary }));
  });
  ipcMain.handle('clinic:arrange', (event, swap) => {
    trustedWindow(event);
    openWindow('doctor');
    openWindow('patient');
    layout(swap === true);
  });
  ipcMain.handle('clinic:patient', (event) => {
    trustedWindow(event);
    openWindow('patient');
  });
  ipcMain.handle('clinic:fullscreen', (event) => {
    const window = trustedWindow(event);
    window.setFullScreen(!window.isFullScreen());
  });
  ipcMain.handle('clinic:quit', (event) => {
    trustedWindow(event);
    app.quit();
  });
}

async function stopEngine() {
  if (!engine?.pid || engine.exitCode !== null || engine.killed) {
    return;
  }
  try {
    await fetch(`${origin}/api/shutdown`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${sessionToken}` },
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    log('shutdown request unavailable');
  }
  // The fusion worker has a bounded 12 s graceful close. Let the engine join
  // that child before terminating its parent (the old 3 s limit raced it).
  for (let attempt = 0; attempt < 200 && engine.exitCode === null && engine.signalCode === null; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  if (engine.exitCode === null && engine.signalCode === null) {
    log('engine graceful shutdown timed out; terminating parent');
    engine.kill();
    for (let attempt = 0; attempt < 50 && engine.exitCode === null && engine.signalCode === null; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    windows.get('doctor')?.focus();
    windows.get('patient')?.show();
  });
  app.on('window-all-closed', () => app.quit());
  app.on('before-quit', (event) => {
    if (allowQuit) {
      return;
    }
    event.preventDefault();
    if (shuttingDown) {
      return;
    }
    shuttingDown = true;
    // Close renderers first: release WebSockets, microphone, WebGL and sound
    // while the backend finishes releasing its device and worker processes.
    for (const window of [...windows.values()]) window.destroy();
    void stopEngine().finally(() => {
      log('desktop closed');
      logStream?.end();
      allowQuit = true;
      app.quit();
    });
  });
  void app.whenReady().then(async () => {
    fs.mkdirSync(app.getPath('userData'), { recursive: true });
    logStream = fs.createWriteStream(path.join(app.getPath('userData'), 'clinic-engine.log'), { flags: 'w' });
    installPermissions();
    installIPC();
    await startEngine();
    openWindow('doctor');
    openWindow('patient');
    screen.on('display-removed', () => layout());
    screen.on('display-added', () => layout());
  }).catch(async (error) => {
    log(error.stack || error.message);
    // A synchronous spawn error happens before ChildProcess emits 'error'.
    // Save only startup fields. Never include env, argv, URL tokens or session content.
    const reportPath = path.join(app.getPath('userData'), 'clinic-startup.json');
    const report = { time: new Date().toISOString(), version: app.getVersion(), arch: process.arch,
      windows: require('node:os').release(), ...launchDetails, message: error.message };
    for (const key of ['code', 'errno', 'syscall']) if (error[key] !== undefined) report[key] = error[key];
    let saved = false;
    try {
      fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf8');
      saved = true;
    } catch { /* The profile may itself be unavailable. */ }
    const locate = uiText('Xem tệp chẩn đoán', 'Show diagnostic file');
    const close = uiText('Đóng', 'Close');
    const choice = await dialog.showMessageBox({
      type: 'error', title: uiText('VSL Clinic chưa mở được', 'VSL Clinic could not start'),
      message: uiText('Chưa mở được dịch vụ nhận dạng trên máy.', 'The local recognition service could not start.'),
      detail: [error.message, saved && uiText('Khi cần hỗ trợ, hãy gửi tệp clinic-startup.json cho kỹ thuật viên.', 'For support, send clinic-startup.json to your technician.')].filter(Boolean).join('\n\n'),
      buttons: saved ? [locate, close] : [close], defaultId: saved ? 1 : 0, cancelId: saved ? 1 : 0,
    });
    if (saved && choice.response === 0) shell.showItemInFolder(reportPath);
    app.quit();
  });
}
