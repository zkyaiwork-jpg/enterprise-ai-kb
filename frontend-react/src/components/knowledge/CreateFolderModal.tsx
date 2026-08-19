import { useEffect, useState, type FormEvent } from 'react'

type CreateFolderModalProps = {
  open: boolean
  onClose: () => void
  onCreate: (name: string) => Promise<void>
}

export function CreateFolderModal({ open, onClose, onCreate }: CreateFolderModalProps) {
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      setName('')
      setError('')
      setSaving(false)
    }
  }, [open])

  if (!open) return null

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedName = name.trim()
    if (!normalizedName || saving) return
    setSaving(true)
    setError('')
    try {
      await onCreate(normalizedName)
      onClose()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '文件夹创建失败，请稍后重试。')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button type="button" aria-label="关闭新建文件夹窗口" onClick={() => !saving && onClose()} className="absolute inset-0 bg-[#172033]/25 backdrop-blur-[2px]" />
      <form onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="create-folder-title" className="relative w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div><h2 id="create-folder-title" className="text-xl font-semibold text-on-surface">新建文件夹</h2><p className="mt-1 text-sm text-on-surface-variant">为企业知识创建清晰的目录</p></div>
          <button type="button" onClick={onClose} disabled={saving} aria-label="关闭" className="flex h-9 w-9 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-low disabled:opacity-50"><span className="material-symbols-outlined">close</span></button>
        </div>
        <label htmlFor="folder-name" className="mt-6 block text-sm font-medium text-on-surface">文件夹名称</label>
        <input id="folder-name" autoFocus maxLength={100} value={name} onChange={(event) => setName(event.target.value)} placeholder="请输入文件夹名称" className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-on-surface outline-none transition focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50" />
        {error && <div className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        <div className="mt-7 flex justify-end gap-3">
          <button type="button" onClick={onClose} disabled={saving} className="rounded-xl border border-[#dfe3ee] px-5 py-2.5 text-sm font-semibold text-on-surface-variant hover:bg-surface-container-low disabled:opacity-50">取消</button>
          <button type="submit" disabled={!name.trim() || saving} className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#0044ad] disabled:bg-[#aebbd1]">{saving ? '创建中...' : '创建'}</button>
        </div>
      </form>
    </div>
  )
}
