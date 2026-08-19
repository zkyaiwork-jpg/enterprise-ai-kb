export type Category = {
  id: number | 'all'
  name: string
  count: number
  icon: string
}

type CategorySidebarProps = {
  categories: Category[]
  activeCategory: number | 'all'
  onChange: (category: number | 'all') => void
  onCreate: () => void
}

export function CategorySidebar({ categories, activeCategory, onChange, onCreate }: CategorySidebarProps) {
  return (
    <aside className="rounded-2xl border border-white bg-white p-3 shadow-ambient lg:sticky lg:top-24">
      <div className="px-3 pb-3 pt-2">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-on-surface-variant">文档分类</p>
        <button type="button" onClick={onCreate} className="mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-primary px-3 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#0044ad]">
          <span className="material-symbols-outlined text-[18px]">create_new_folder</span>新建文件夹
        </button>
      </div>
      <nav aria-label="文档分类" className="flex gap-2 overflow-x-auto lg:flex-col">
        {categories.map((category) => {
          const active = category.id === activeCategory
          return (
            <button
              key={category.id}
              type="button"
              onClick={() => onChange(category.id)}
              className={`flex min-w-fit items-center gap-3 rounded-xl px-3 py-3 text-left text-sm transition-colors lg:w-full ${
                active ? 'bg-primary-fixed font-semibold text-primary' : 'text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">{category.icon}</span>
              <span className="flex-1 whitespace-nowrap">{category.name}</span>
              <span className={`rounded-full px-2 py-0.5 text-xs ${active ? 'bg-white/70 text-primary' : 'bg-surface-container-low text-on-surface-variant'}`}>
                {category.count}
              </span>
            </button>
          )
        })}
      </nav>
    </aside>
  )
}
