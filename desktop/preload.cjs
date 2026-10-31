'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('clinicDesktop', {
  displays: () => ipcRenderer.invoke('clinic:displays'),
  arrange: (swap = false) => ipcRenderer.invoke('clinic:arrange', swap === true),
  openPatient: () => ipcRenderer.invoke('clinic:patient'),
  fullscreen: () => ipcRenderer.invoke('clinic:fullscreen'),
  quit: () => ipcRenderer.invoke('clinic:quit'),
});
