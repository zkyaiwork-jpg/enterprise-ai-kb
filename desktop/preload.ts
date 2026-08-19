import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('desktopApp', {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
  },
  getSettingsStatus: () => ipcRenderer.invoke('settings:get-status'),
  saveDeepseekApiKey: (apiKey: string) => ipcRenderer.invoke('settings:save-deepseek-key', apiKey),
  getUserInfo: () => ipcRenderer.invoke('settings:get-user-info'),
  saveUserName: (userName: string) => ipcRenderer.invoke('settings:save-user-name', userName),
})
