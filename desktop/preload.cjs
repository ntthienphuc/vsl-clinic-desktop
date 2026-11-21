'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('clinicDesktop', {
  getInterfaceLanguage: () => ipcRenderer.invoke('clinic:interface-language:get'),
  setInterfaceLanguage: language => ipcRenderer.invoke('clinic:interface-language:set', language),
  onInterfaceLanguageChanged: callback => {
    const listener = (_event, language) => callback(language);
    ipcRenderer.on('clinic:interface-language:changed', listener);
    return () => ipcRenderer.removeListener('clinic:interface-language:changed', listener);
  },
  displays: () => ipcRenderer.invoke('clinic:displays'),
  arrange: (swap = false) => ipcRenderer.invoke('clinic:arrange', swap === true),
  openPatient: () => ipcRenderer.invoke('clinic:patient'),
  fullscreen: () => ipcRenderer.invoke('clinic:fullscreen'),
  quit: () => ipcRenderer.invoke('clinic:quit'),
});
