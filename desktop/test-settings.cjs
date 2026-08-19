const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

const { ensureSettingsFile, readSettings, settingsFilePath, writeSettings } = require('./dist/settings.js')

const temporaryRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'enterprise-ai-kb-settings-'))
try {
  const settingsPath = ensureSettingsFile(temporaryRoot)
  assert.equal(settingsPath, settingsFilePath(temporaryRoot))
  assert.deepEqual(readSettings(temporaryRoot), { deepseek_api_key: '', user_name: '' })

  writeSettings(temporaryRoot, { deepseek_api_key: 'sk-test-secret', user_name: '测试用户' })
  assert.deepEqual(readSettings(temporaryRoot), { deepseek_api_key: 'sk-test-secret', user_name: '测试用户' })
  assert.equal(JSON.parse(fs.readFileSync(settingsPath, 'utf-8')).deepseek_api_key, 'sk-test-secret')
  assert.equal(JSON.parse(fs.readFileSync(settingsPath, 'utf-8')).user_name, '测试用户')
  console.log('desktop settings tests: passed')
} finally {
  fs.rmSync(temporaryRoot, { recursive: true, force: true })
}
