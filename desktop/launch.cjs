'use strict';

const { spawn } = require('node:child_process');
const path = require('node:path');
const electron = require('electron');

const environment = { ...process.env };
delete environment.ELECTRON_RUN_AS_NODE;
const child = spawn(electron, [path.resolve(__dirname, '..')], {
  env: environment,
  stdio: 'inherit',
  windowsHide: false,
});
child.on('error', (error) => {
  process.stderr.write(error.message + '\n');
  process.exitCode = 1;
});
child.on('exit', (code) => {
  process.exitCode = code ?? 1;
});
