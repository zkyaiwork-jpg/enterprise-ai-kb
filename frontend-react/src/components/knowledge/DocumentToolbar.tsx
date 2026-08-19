type DocumentToolbarProps = {
  search: string
  onSearchChange: (value: string) => void
}

export function DocumentToolbar({ search, onSearchChange }: DocumentToolbarProps) {
  return (
    <div className="flex flex-col gap-3 border-b border-[#e7eaf3] p-4 sm:flex-row sm:items-center sm:justify-between">
      <label className="relative block w-full sm:max-w-sm">
        <span className="sr-only">搜索文档名称</span>
        <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-[20px] text-on-surface-variant">search</span>
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="搜索文档名称..."
          className="w-full rounded-xl border border-[#dfe3ee] bg-white py-2.5 pl-10 pr-4 text-sm text-on-surface outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10"
        />
      </label>
      <div className="flex gap-2">
        <button type="button" className="inline-flex items-center gap-2 rounded-xl border border-[#dfe3ee] bg-white px-4 py-2.5 text-sm font-medium text-on-surface-variant hover:bg-surface-container-low">
          <span className="material-symbols-outlined text-[19px]">filter_list</span>筛选
        </button>
        <button type="button" className="inline-flex items-center gap-2 rounded-xl border border-[#dfe3ee] bg-white px-4 py-2.5 text-sm font-medium text-on-surface-variant hover:bg-surface-container-low">
          <span className="material-symbols-outlined text-[19px]">sort</span>排序
        </button>
      </div>
    </div>
  )
}
