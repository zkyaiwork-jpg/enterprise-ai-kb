import { useEffect, useState, type FormEvent } from 'react'

import { ApiError } from '../../api/client'
import type { DocumentVisibility } from '../../api/documents'
import type { DocumentItem } from './DocumentTable'

type EditDocumentModalProps = {
  document: DocumentItem | null
  onClose: () => void
  onSave: (documentId: number, payload: { original_name?: string; visibility?: DocumentVisibility }) => Promise<void>
  allowedVisibilities: DocumentVisibility[]
}

const visibilityLabels: Record<DocumentVisibility, string> = {
  private: '仅自己/受控范围', team: '小组', department: '部门', company: '全公司',
}

export function EditDocumentModal({ document, onClose, onSave, allowedVisibilities }: EditDocumentModalProps) {
  const [originalName, setOriginalName] = useState('')
  const [visibility, setVisibility] = useState<DocumentVisibility>('private')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [changeVisibility, setChangeVisibility] = useState(false)

  useEffect(() => {
    if (document) {
      setOriginalName(document.name)
      setVisibility(document.visibility ?? 'private')
      setError('')
      setSaving(false)
      setChangeVisibility(false)
    }
  }, [document])

  if (!document) return null
  const currentDocument = document

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedName = originalName.trim()
    if (!normalizedName || !/^\d+$/.test(currentDocument.id)) return
    setSaving(true)
    setError('')
    try {
      const payload = {
        ...(normalizedName !== currentDocument.name ? { original_name: normalizedName } : {}),
        ...(changeVisibility ? { visibility } : {}),
      }
      await onSave(Number(currentDocument.id), payload)
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 403) {
        setError('无权修改该文件')
      } else {
        setError('文件信息修改失败，请稍后重试')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button type="button" aria-label="关闭编辑窗口" onClick={() => !saving && onClose()} className="absolute inset-0 bg-[#172033]/25 backdrop-blur-[2px]" />
      <form onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="edit-document-title" className="relative w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="edit-document-title" className="text-xl font-semibold text-on-surface">编辑文档信息</h2>
            <p className="mt-1 text-sm text-on-surface-variant">修改显示名称和可见范围，不会编辑文档正文。</p>
          </div>
          <button type="button" onClick={onClose} disabled={saving} aria-label="关闭" className="flex h-9 w-9 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-low disabled:opacity-50"><span className="material-symbols-outlined">close</span></button>
        </div>

        <label className="mt-6 block text-sm font-medium text-on-surface">
          文档名称
          <input required maxLength={255} value={originalName} onChange={(event) => setOriginalName(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50" />
        </label>
        <label className="mt-5 flex items-center gap-3 text-sm font-medium text-on-surface">
          <input type="checkbox" checked={changeVisibility} onChange={(event) => {
            const checked = event.target.checked
            setChangeVisibility(checked)
            if (checked && !allowedVisibilities.includes(visibility)) setVisibility(allowedVisibilities[0] ?? 'private')
          }} />
          修改可见范围
        </label>
        {changeVisibility && <label className="mt-3 block text-sm font-medium text-on-surface">
          可见范围
          <select value={visibility} onChange={(event) => setVisibility(event.target.value as DocumentVisibility)} className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50">
            {allowedVisibilities.map((value) => <option key={value} value={value}>{visibilityLabels[value]}</option>)}
          </select>
        </label>}
        <p className="mt-2 text-xs text-on-surface-variant">可见不等于可管理，编辑与删除权限仍由后端对象权限规则决定。</p>
        {error && <div role="alert" className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <div className="mt-7 flex justify-end gap-3">
          <button type="button" onClick={onClose} disabled={saving} className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold disabled:opacity-50">取消</button>
          <button type="submit" disabled={saving || !originalName.trim()} className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{saving ? '保存中...' : '保存'}</button>
        </div>
      </form>
    </div>
  )
}
