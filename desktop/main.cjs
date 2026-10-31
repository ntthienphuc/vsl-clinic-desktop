'use strict';

const { app, BrowserWindow, dialog, ipcMain, screen, session } = require('electron');
const { spawn } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');

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
  if (!fs.existsSync(executable) || !fs.existsSync(path.join(frontend, 'index.html'))) {
    throw new Error('Thiếu bộ chạy hoặc giao diện. Hãy chạy tools/setup.ps1 và npm run build trong thư mục dự án.');
  }
  const args = app.isPackaged ? ['--port', String(port)] : ['-u', '-X', 'utf8', path.join(project, 'backend', 'main.py'), '--port', String(port)];
  engine = spawn(executable, args, {
    cwd: app.isPackaged ? process.resourcesPath : project,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, CLINIC_ASSETS: assets, CLINIC_FRONTEND: frontend, CLINIC_TOKEN: sessionToken, PYTHONUNBUFFERED: '1', PYTHONUTF8: '1' },
  });
  engine.on('error', (error) => {
    engineExit = error.message;
    log(`engine error: ${error.message}`);
  });
  engine.on('exit', (code, signal) => {
    engineExit = `exit ${code}, signal ${signal}`;
    log(`engine ${engineExit}`);
    if (windows.size > 0 && !shuttingDown) {
      dialog.showErrorBox('VSL Clinic · Dịch vụ đã dừng', 'Bộ nhận dạng trên máy đã dừng. Hãy đóng và mở lại ứng dụng. Chi tiết nằm trong tệp clinic-engine.log của ứng dụng.');
    }
  });
  engine.stdout.on('data', (data) => log(data.toString().trimEnd()));
  engine.stderr.on('data', (data) => log(data.toString().trimEnd()));
  origin = `http://127.0.0.1:${port}`;
  for (let attempt = 0; attempt < 240; attempt += 1) {
    if (engineExit !== null) {
      throw new Error(`Bộ nhận dạng chưa khởi động được (${engineExit}). Xem clinic-engine.log.`);
    }
    try {
      const response = await fetch(`${origin}/api/bootstrap`, {
        headers: { Authorization: `Bearer ${sessionToken}` },
        signal: AbortSignal.timeout(700),
      });
      if (response.ok) {
        log(`ready at ${origin}; model=400 words`);
        return;
      }
    } catch {
      // The local model is still loading.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error('Bộ nhận dạng chưa sẵn sàng sau 60 giây.');
}

function layout(swap = false) {
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
    title: role === 'doctor' ? 'VSL Clinic · Bác sĩ' : 'VSL Clinic · Người bệnh',
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
  if (!engine || engine.exitCode !== null || engine.killed) {
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
  for (let attempt = 0; attempt < 30 && engine.exitCode === null; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  if (engine.exitCode === null) {
    engine.kill();
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
  }).catch((error) => {
    log(error.stack || error.message);
    dialog.showErrorBox('VSL Clinic chưa mở được', error.message);
    app.quit();
  });
}
