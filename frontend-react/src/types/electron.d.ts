export {}

declare global {
  interface Window {
    desktopApp?: {
      platform: string
      versions: {
        electron: string
        chrome: string
      }
      getSettingsStatus: () => Promise<{ hasDeepseekApiKey: boolean }>
      saveDeepseekApiKey: (apiKey: string) => Promise<{ success: boolean; backendReady: boolean }>
      getUserInfo: () => Promise<{ userName: string; hasUserName: boolean }>
      saveUserName: (userName: string) => Promise<{ success: boolean; userName: string }>
    }
  }
}
