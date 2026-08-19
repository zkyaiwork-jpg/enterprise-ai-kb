import { useEffect, useState, type ChangeEvent, type DragEvent } from 'react'
import type { Folder } from '../../api/folders'
import type { DocumentVisibility } from '../../api/documents'
import type { TeamOption } from '../../api/users'

type UploadStatus = 'idle' | 'loading' | 'success' | 'error'

type UploadModalProps = {
  open: boolean
  folders: Folder[]
  onClose: () => void
  onUpload: (file: File, folderId: number, visibility: DocumentVisibility, teamId?: number) => Promise<void>
  allowedVisibilities: DocumentVisibility[]
  teams: TeamOption[]
  currentTeamId?: number
}

const supportedExtensions = ['docx', 'pdf', 'txt']

const visibilityLabels: Record<DocumentVisibility, string> = {
  private: '仅自己/受控范围', team: '小组', department: '部门', company: '全公司',
}

export function UploadModal({ open, folders, onClose, onUpload, allowedVisibilities, teams, currentTeamId }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [folderId, setFolderId] = useState('')
  const [visibility, setVisibility] = useState<DocumentVisibility>('private')
  const [teamId, setTeamId] = useState('')
  const [status, setStatus] = useState<UploadStatus>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    if (open) {
      setFile(null)
      setFolderId(folders[0] ? String(folders[0].id) : '')
      setVisibility('private')
      setTeamId(currentTeamId ? String(currentTeamId) : '')
      setStatus('idle')
      setErrorMessage('')
    }
  }, [currentTeamId, folders, open])

  if (!open) return null

  const selectFile = (selectedFile?: File) => {
    if (!selectedFile || status === 'loading') return
    const extension = selectedFile.name.split('.').pop()?.toLowerCase() ?? ''
    if (!supportedExtensions.includes(extension)) {
      setFile(null)
      setStatus('error')
      setErrorMessage('暂不支持该文件格式，请选择 DOCX、PDF 或 TXT 文件。')
      return
    }
    setFile(selectedFile)
    setStatus('idle')
    setErrorMessage('')
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    selectFile(event.target.files?.[0])
    event.target.value = ''
  }

  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault()
    if (status !== 'loading') selectFile(event.dataTransfer.files?.[0])
  }

  const handleUpload = async () => {
    if (!file || !folderId || status === 'loading') return
    setStatus('loading')
    setErrorMessage('')
    try {
      await onUpload(file, Number(folderId), visibility, visibility === 'team' && teamId ? Number(teamId) : undefined)
      setStatus('success')
    } catch (error) {
      setStatus('error')
      setErrorMessage(error instanceof Error ? error.message : '上传失败，请稍后重试。')
    }
  }

  const closeModal = () => onClose()

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button type="button" aria-label="关闭上传窗口" onClick={closeModal} className="absolute inset-0 bg-[#172033]/25 backdrop-blur-[2px]" />
      <section role="dialog" aria-modal="true" aria-labelledby="upload-title" className="relative w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div><h2 id="upload-title" className="text-xl font-semibold text-on-surface">上传文档</h2><p className="mt-1 text-sm text-on-surface-variant">将企业资料添加到知识库</p></div>
          <button type="button" onClick={closeModal} aria-label="关闭" className="flex h-9 w-9 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-low"><span className="material-symbols-outlined">close</span></button>
        </div>

        <label onDragOver={(event) => event.preventDefault()} onDrop={handleDrop} className="mt-7 flex cursor-pointer flex-col items-center rounded-2xl border-2 border-dashed border-[#cbd5e7] bg-[#f8faff] px-6 py-10 text-center transition-colors hover:border-primary/50 hover:bg-blue-50/40">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-fixed text-primary">{status === 'loading' ? <span aria-hidden="true" className="h-7 w-7 animate-spin rounded-full border-[3px] border-primary/20 border-t-primary" /> : <span className="material-symbols-outlined text-3xl">cloud_upload</span>}</span>
          <span className="mt-4 text-sm font-semibold text-on-surface">{file ? file.name : '拖拽文件到此处，或点击选择文件'}</span>
          <span className="mt-2 text-xs text-on-surface-variant">{file ? `${(file.size / 1024).toFixed(1)} KB` : '支持 DOCX、PDF、TXT 格式'}</span>
          <input type="file" accept=".docx,.pdf,.txt" onChange={handleFileChange} className="sr-only" />
        </label>

        <label htmlFor="upload-folder" className="mt-5 block text-sm font-medium text-on-surface">所属文件夹</label>
        <select id="upload-folder" value={folderId} onChange={(event) => setFolderId(event.target.value)} disabled={status === 'loading'} className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-on-surface outline-none transition focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50 disabled:opacity-60">
          {folders.length === 0 && <option value="">请先新建文件夹</option>}
          {folders.map((folder) => <option key={folder.id} value={folder.id}>{folder.name}</option>)}
        </select>

        <label htmlFor="upload-visibility" className="mt-5 block text-sm font-medium text-on-surface">可见范围</label>
        <select
          id="upload-visibility"
          value={visibility}
          onChange={(event) => setVisibility(event.target.value as DocumentVisibility)}
          disabled={status === 'loading'}
          className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-on-surface outline-none transition focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50 disabled:opacity-60"
        >
          {allowedVisibilities.map((value) => <option key={value} value={value}>{visibilityLabels[value]}</option>)}
        </select>
        <p className="mt-2 text-xs text-on-surface-variant">可见范围只影响查看权限，修改和删除仍按角色与归属判断。</p>
        {visibility === 'team' && <label className="mt-5 block text-sm font-medium text-on-surface">目标小组<select required value={teamId} onChange={(e) => setTeamId(e.target.value)} disabled={Boolean(currentTeamId)} className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3"><option value="">请选择小组</option>{teams.map(team => <option key={team.id} value={team.id}>{team.department?.name ? `${team.department.name} / ` : ''}{team.name}</option>)}</select></label>}

        {status === 'loading' && <div className="mt-4 flex items-center gap-2 rounded-xl bg-blue-50 px-4 py-3 text-sm font-medium text-primary"><span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />正在上传...</div>}
        {status === 'success' && <div className="mt-4 flex items-center gap-2 rounded-xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700"><span className="material-symbols-outlined text-[19px]">check_circle</span>上传成功，文档列表已刷新。</div>}
        {status === 'error' && <div className="mt-4 flex items-start gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700"><span className="material-symbols-outlined mt-0.5 text-[19px]">error</span><span>{errorMessage}</span></div>}

        <div className="mt-7 flex justify-end gap-3">
          <button type="button" onClick={closeModal} className="rounded-xl border border-[#dfe3ee] px-5 py-2.5 text-sm font-semibold text-on-surface-variant hover:bg-surface-container-low">{status === 'success' ? '完成' : '取消'}</button>
          {status !== 'success' && <button type="button" onClick={() => void handleUpload()} disabled={!file || !folderId || status === 'loading' || (visibility === 'team' && !teamId)} className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#0044ad] disabled:bg-[#aebbd1]">{status === 'loading' ? <span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" /> : <span className="material-symbols-outlined text-[19px]">upload</span>}{status === 'loading' ? '正在上传...' : '上传文档'}</button>}
        </div>
      </section>
    </div>
  )
}
