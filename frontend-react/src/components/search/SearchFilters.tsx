import type { Folder } from '../../api/folders'

export type SearchFilterValues = {
  folderId: number | 'all'
  fileType: string
  time: string
}

type SearchFiltersProps = {
  values: SearchFilterValues
  folders: Folder[]
  onChange: (values: SearchFilterValues) => void
}

const groups = [
  { key: 'fileType' as const, label: '文件类型', options: ['全部', 'DOCX', 'PDF', 'TXT'] },
  { key: 'time' as const, label: '时间', options: ['不限', '最近一天', '最近一周', '最近一个月'] },
]

export function SearchFilters({ values, folders, onChange }: SearchFiltersProps) {
  return (
    <section className="rounded-2xl border border-white bg-white p-5 shadow-ambient">
      <div className="flex items-center gap-2 text-sm font-semibold text-on-surface"><span className="material-symbols-outlined text-[19px] text-primary">tune</span>筛选条件</div>
      <div className="mt-4 space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <span className="w-20 shrink-0 text-xs font-medium text-on-surface-variant">文档分类</span>
          <div className="flex flex-wrap gap-2">
            {[{ id: 'all' as const, name: '全部' }, ...folders].map((folder) => {
              const active = values.folderId === folder.id
              return <button key={folder.id} type="button" onClick={() => onChange({ ...values, folderId: folder.id })} className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${active ? 'bg-primary-fixed text-primary' : 'bg-[#f6f7fb] text-on-surface-variant hover:bg-[#edf2fb] hover:text-on-surface'}`}>{folder.name}</button>
            })}
          </div>
        </div>
        {groups.map((group) => (
          <div key={group.key} className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <span className="w-20 shrink-0 text-xs font-medium text-on-surface-variant">{group.label}</span>
            <div className="flex flex-wrap gap-2">
              {group.options.map((option) => {
                const active = values[group.key] === option
                return <button key={option} type="button" onClick={() => onChange({ ...values, [group.key]: option })} className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${active ? 'bg-primary-fixed text-primary' : 'bg-[#f6f7fb] text-on-surface-variant hover:bg-[#edf2fb] hover:text-on-surface'}`}>{option}</button>
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
