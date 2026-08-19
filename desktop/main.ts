import { ChildProcessWithoutNullStreams, spawn } from 'node:child_process'
import { appendFileSync, createReadStream, existsSync, mkdirSync, statSync } from 'node:fs'
import http, { IncomingMessage, ServerResponse } from 'node:http'
import path from 'node:path'

import { app, BrowserWindow, dialog, ipcMain, Menu } from 'electron'

import { ensureSettingsFile, readSettings, settingsFilePath, writeSettings } from './settings'


const BACKEND_URL = 'http://127.0.0.1:8000'
const HEALTH_URL = `${BACKEND_URL}/health`
let backendProcess: ChildProcessWithoutNullStreams | null = null
let frontendServer: http.Server | null = null
let mainWindow: BrowserWindow | null = null
let shuttingDown = false
let electronStartLogPath: string | null = null

const hasSingleInstanceLock = app.requestSingleInstanceLock()
if (!hasSingleInstanceLock) app.quit()

function initializeElectronStartLog(): void {
  const logDir = path.join(app.getPath('userData'), 'logs')
  mkdirSync(logDir, { recursive: true })
  electronStartLogPath = path.join(logDir, 'electron-start.log')
}

function writeElectronStartLog(message: string): void {
  console.log(message)
  if (!electronStartLogPath) return
  try {
    appendFileSync(electronStartLogPath, `${new Date().toISOString()} ${message}\n`, 'utf8')
  } catch (error) {
    console.error('[electron] failed to write startup log', error)
  }
}

const userDataOverride = process.env.ENTERPRISE_AI_USER_DATA
if (userDataOverride) app.setPath('userData', path.resolve(userDataOverride))

const mimeTypes: Record<string, string> = {
  '.css': 'text/css; charset=utf-8',
  '.gif': 'image/gif',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
}

function projectRoot(): string {
  return path.resolve(app.getAppPath(), '..')
}

function preparePackagedBackend(): { executable: string; cwd: string } {
  const backendRoot = path.join(process.resourcesPath, 'backend')
  const executable = path.join(backendRoot, 'enterprise-ai-kb-backend.exe')
  return { executable, cwd: backendRoot }
}

function startBackend(apiKey: string): void {
  if (backendProcess && !backendProcess.killed) return

  let command: string
  let args: string[]
  let cwd: string

  if (app.isPackaged) {
    const packaged = preparePackagedBackend()
    command = packaged.executable
    args = []
    cwd = packaged.cwd
  } else {
    const root = projectRoot()
    command = path.join(root, 'venv', 'Scripts', 'python.exe')
    args = ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000']
    cwd = root
  }

  const appDataDir = path.join(app.getPath('userData'), 'data')
  const backendLogDir = path.join(appDataDir, 'logs')
  mkdirSync(appDataDir, { recursive: true })

  writeElectronStartLog('[electron] starting backend')
  writeElectronStartLog(`[electron] backend path=${command}`)
  writeElectronStartLog(`[electron] backend cwd=${cwd}`)
  writeElectronStartLog(`[electron] APP_DATA_DIR=${appDataDir} exists=${existsSync(appDataDir)}`)
  writeElectronStartLog(`[electron] APP_LOG_DIR=${backendLogDir}`)
  writeElectronStartLog(`[electron] key configured=${Boolean(apiKey)}`)
  if (app.isPackaged) {
    const modelCacheDir = path.join(process.resourcesPath, 'model-cache')
    writeElectronStartLog(`[electron] model-cache=${modelCacheDir} exists=${existsSync(modelCacheDir)}`)
  }
  if (!existsSync(command)) throw new Error(`backend executable not found: ${command}`)
  if (!existsSync(cwd)) throw new Error(`backend working directory not found: ${cwd}`)

  backendProcess = spawn(command, args, {
    cwd,
    env: {
      ...process.env,
      DEEPSEEK_API_KEY: apiKey,
      APP_DATA_DIR: appDataDir,
      APP_LOG_DIR: backendLogDir,
      ...(app.isPackaged ? {
        HF_HOME: path.join(process.resourcesPath, 'model-cache'),
        HF_HUB_OFFLINE: '1',
        TRANSFORMERS_OFFLINE: '1',
      } : {}),
      PYTHONUNBUFFERED: '1',
    },
    windowsHide: true,
  })
  writeElectronStartLog(`[electron] backend started pid=${backendProcess.pid ?? 'pending'}`)
  backendProcess.stdout.on('data', (data) => {
    const output = String(data).trimEnd()
    if (output) console.info(`[backend:stdout] ${output}`)
  })
  backendProcess.stderr.on('data', (data) => {
    const output = String(data).trimEnd()
    if (output) console.error(`[backend:stderr] ${output}`)
  })
  backendProcess.on('error', (error) => {
    writeElectronStartLog(`[electron] backend spawn error=${error.message}`)
  })
  backendProcess.on('exit', (code) => {
    writeElectronStartLog(`[electron] backend exit code=${String(code)}`)
    backendProcess = null
    if (!shuttingDown) console.error(`FastAPI backend exited unexpectedly with code ${code}`)
  })
}

async function stopBackend(): Promise<void> {
  const processToStop = backendProcess
  if (!processToStop || processToStop.killed) return
  await new Promise<void>((resolve) => {
    const timeout = setTimeout(() => {
      if (!processToStop.killed) processToStop.kill()
      resolve()
    }, 10_000)
    processToStop.once('exit', () => {
      clearTimeout(timeout)
      resolve()
    })
    processToStop.kill()
  })
  if (backendProcess === processToStop) backendProcess = null
}

async function restartBackend(apiKey: string): Promise<void> {
  await stopBackend()
  startBackend(apiKey)
  await waitForBackendHealthy()
}

async function getBackendHealthStatus(): Promise<string | null> {
  try {
    const response = await fetch(HEALTH_URL, { signal: AbortSignal.timeout(5_000) })
    if (!response.ok) return null
    const health = await response.json() as { status?: unknown }
    return typeof health.status === 'string' ? health.status : null
  } catch {
    return null
  }
}

async function waitForBackendHealthy(timeoutMs = 120_000): Promise<void> {
  writeElectronStartLog('[electron] waiting health')
  const deadline = Date.now() + timeoutMs
  let lastHealthStatus: string | null | undefined
  while (Date.now() < deadline) {
    const healthStatus = await getBackendHealthStatus()
    if (healthStatus !== lastHealthStatus) {
      writeElectronStartLog(`[electron] health result=${healthStatus || 'unavailable'}`)
      lastHealthStatus = healthStatus
    }
    if (healthStatus === 'healthy') {
      writeElectronStartLog('[electron] backend healthy')
      return
    }
    await new Promise((resolve) => setTimeout(resolve, 1_000))
  }
  writeElectronStartLog('[electron] health timeout after 120 seconds')
  throw new Error('AI服务启动失败，请检查日志。')
}

async function ensureBackendHealthy(apiKey: string): Promise<void> {
  const currentStatus = await getBackendHealthStatus()
  if (currentStatus === 'healthy') {
    writeElectronStartLog('[electron] health result=healthy')
    writeElectronStartLog('[electron] backend healthy')
    return
  }
  // A responding health endpoint means another backend already owns port 8000.
  // Wait for that process instead of starting a duplicate instance.
  if (currentStatus === null) startBackend(apiKey)
  await waitForBackendHealthy()
}

async function startBackendInBackground(apiKey: string): Promise<void> {
  try {
    await ensureBackendHealthy(apiKey)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    writeElectronStartLog(`[electron] backend startup failed message=${message}`)
  }
}

async function waitForUrl(url: string, timeoutMs = 180_000): Promise<void> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(5_000) })
      if (response.ok) return
    } catch {
      // Expected while Vite, the embedding model, or FastAPI is starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 1_000))
  }
  throw new Error(`Timed out waiting for ${url}`)
}

function proxyApi(request: IncomingMessage, response: ServerResponse): void {
  const targetPath = (request.url || '/').replace(/^\/api/, '') || '/'
  const proxy = http.request({
    hostname: '127.0.0.1',
    port: 8000,
    path: targetPath,
    method: request.method,
    headers: { ...request.headers, host: '127.0.0.1:8000' },
  }, (upstream) => {
    response.writeHead(upstream.statusCode || 502, upstream.headers)
    upstream.pipe(response)
  })
  proxy.on('error', () => {
    if (!response.headersSent) response.writeHead(502, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify({ detail: '后端服务不可用' }))
  })
  request.pipe(proxy)
}

function serveFrontend(root: string): Promise<string> {
  return new Promise((resolve, reject) => {
    frontendServer = http.createServer((request, response) => {
      if ((request.url || '').startsWith('/api/')) {
        proxyApi(request, response)
        return
      }

      const requestPath = decodeURIComponent((request.url || '/').split('?')[0])
      const relativePath = requestPath === '/' ? 'index.html' : requestPath.replace(/^\/+/, '')
      let filePath = path.resolve(root, relativePath)
      if (!filePath.startsWith(path.resolve(root))) {
        response.writeHead(403).end()
        return
      }
      if (!existsSync(filePath) || statSync(filePath).isDirectory()) filePath = path.join(root, 'index.html')

      response.writeHead(200, {
        'Content-Type': mimeTypes[path.extname(filePath).toLowerCase()] || 'application/octet-stream',
        'Cache-Control': filePath.endsWith('index.html') ? 'no-cache' : 'public, max-age=604800',
      })
      createReadStream(filePath).pipe(response)
    })
    frontendServer.once('error', reject)
    frontendServer.listen(0, '127.0.0.1', () => {
      const address = frontendServer?.address()
      if (!address || typeof address === 'string') return reject(new Error('Unable to bind frontend server'))
      resolve(`http://127.0.0.1:${address.port}`)
    })
  })
}

async function createWindow(): Promise<void> {
  console.log('[electron] creating window')
  const userDataPath = app.getPath('userData')
  ensureSettingsFile(userDataPath)
  const settings = readSettings(userDataPath)
  const hasUserName = Boolean(settings.user_name)

  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 700,
    show: false,
    backgroundColor: '#F5F7FB',
    autoHideMenuBar: true,
    titleBarStyle: 'hidden',
    titleBarOverlay: {
      color: '#F5F7FB',
      symbolColor: '#475569',
      height: 40,
    },
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })
  mainWindow.setMenuBarVisibility(false)
  console.log('[electron] window created')
  mainWindow.on('closed', () => {
    mainWindow = null
  })

  let pageUrl: string
  if (!app.isPackaged) {
    const devUrl = process.env.ELECTRON_DEV_URL || 'http://127.0.0.1:5173'
    await waitForUrl(devUrl, 60_000)
    pageUrl = hasUserName ? devUrl : `${devUrl}/welcome`
  } else {
    const frontendUrl = await serveFrontend(path.join(process.resourcesPath, 'frontend'))
    pageUrl = hasUserName ? frontendUrl : `${frontendUrl}/welcome`
  }
  console.log('[electron] loading url', pageUrl)
  await mainWindow.loadURL(pageUrl)
  writeElectronStartLog('[electron] opening main window')
  mainWindow.show()
  mainWindow.focus()
}

function registerSettingsIpc(): void {
  ipcMain.handle('settings:get-status', () => {
    const settings = readSettings(app.getPath('userData'))
    return { hasDeepseekApiKey: Boolean(settings.deepseek_api_key) }
  })

  ipcMain.handle('settings:save-deepseek-key', async (_event, apiKey: unknown) => {
    if (typeof apiKey !== 'string' || !apiKey.trim()) {
      throw new Error('请输入有效的 DeepSeek API Key')
    }
    const normalizedKey = apiKey.trim()
    const settings = readSettings(app.getPath('userData'))
    writeSettings(app.getPath('userData'), { ...settings, deepseek_api_key: normalizedKey })
    await restartBackend(normalizedKey)
    return { success: true, backendReady: true }
  })

  ipcMain.handle('settings:get-user-info', () => {
    const settings = readSettings(app.getPath('userData'))
    return {
      userName: settings.user_name,
      hasUserName: Boolean(settings.user_name),
    }
  })

  ipcMain.handle('settings:save-user-name', (_event, userName: unknown) => {
    if (typeof userName !== 'string' || !userName.trim()) {
      throw new Error('请输入有效的姓名')
    }
    const normalizedUserName = userName.trim().slice(0, 50)
    const settings = readSettings(app.getPath('userData'))
    writeSettings(app.getPath('userData'), { ...settings, user_name: normalizedUserName })
    return { success: true, userName: normalizedUserName }
  })
}

function stopChildren(): void {
  shuttingDown = true
  frontendServer?.close()
  frontendServer = null
  if (backendProcess && !backendProcess.killed) backendProcess.kill()
  backendProcess = null
}

app.whenReady().then(async () => {
  if (!hasSingleInstanceLock) return
  initializeElectronStartLog()
  writeElectronStartLog(`[electron] startup time=${new Date().toISOString()}`)
  writeElectronStartLog(`[electron] app ready packaged=${app.isPackaged}`)
  writeElectronStartLog(`[electron] resources path=${process.resourcesPath}`)
  writeElectronStartLog(`[electron] userData path=${app.getPath('userData')}`)
  Menu.setApplicationMenu(null)
  registerSettingsIpc()

  const userDataPath = app.getPath('userData')
  const settingsPath = settingsFilePath(userDataPath)
  ensureSettingsFile(userDataPath)
  const settings = readSettings(userDataPath)
  writeElectronStartLog(`[electron] settings path=${settingsPath}`)
  writeElectronStartLog(`[electron] key configured=${Boolean(settings.deepseek_api_key)}`)
  await createWindow()
  if (settings.deepseek_api_key) {
    void startBackendInBackground(settings.deepseek_api_key)
  }
}).catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error)
  writeElectronStartLog(`[electron] startup failed message=${message}`)
  dialog.showErrorBox('AI服务启动失败', message)
  stopChildren()
  app.quit()
})

app.on('second-instance', () => {
  const window = mainWindow
  if (!window) return
  if (window.isMinimized()) window.restore()
  window.show()
  window.focus()
})

app.on('before-quit', stopChildren)
app.on('window-all-closed', () => app.quit())
