import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import path from 'node:path'


export type DesktopSettings = {
  deepseek_api_key: string
  user_name: string
}

const defaultSettings: DesktopSettings = {
  deepseek_api_key: '',
  user_name: '',
}

export function settingsFilePath(userDataPath: string): string {
  return path.join(userDataPath, 'config', 'settings.json')
}

export function ensureSettingsFile(userDataPath: string): string {
  const filePath = settingsFilePath(userDataPath)
  if (!existsSync(filePath)) writeSettings(userDataPath, defaultSettings)
  return filePath
}

export function readSettings(userDataPath: string): DesktopSettings {
  const filePath = ensureSettingsFile(userDataPath)
  try {
    const parsed = JSON.parse(readFileSync(filePath, 'utf-8')) as Partial<DesktopSettings>
    return {
      deepseek_api_key: typeof parsed.deepseek_api_key === 'string' ? parsed.deepseek_api_key.trim() : '',
      user_name: typeof parsed.user_name === 'string' ? parsed.user_name.trim() : '',
    }
  } catch {
    return { ...defaultSettings }
  }
}

export function writeSettings(userDataPath: string, settings: DesktopSettings): void {
  const filePath = settingsFilePath(userDataPath)
  const configDir = path.dirname(filePath)
  const temporaryPath = `${filePath}.tmp`
  mkdirSync(configDir, { recursive: true })
  writeFileSync(temporaryPath, `${JSON.stringify(settings, null, 2)}\n`, {
    encoding: 'utf-8',
    mode: 0o600,
  })
  renameSync(temporaryPath, filePath)
}
