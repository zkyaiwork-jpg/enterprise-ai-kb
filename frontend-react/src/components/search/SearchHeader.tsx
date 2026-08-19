import { useState, type FormEvent } from 'react'

type SearchHeaderProps = {
  onSearch: (query: string) => void
  loading: boolean
}

export function SearchHeader({ onSearch, loading }: SearchHeaderProps) {
  const [query, setQuery] = useState('')

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (query.trim() && !loading) onSearch(query.trim())
  }

  return (
    <section className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-[#eaf2ff] via-[#f5f8ff] to-white px-6 py-8 shadow-ambient sm:px-10 sm:py-10">
      <div className="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-[#d4e3ff]/60" />
      <div className="relative mx-auto max-w-3xl text-center">
        <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-primary shadow-sm"><span className="material-symbols-outlined text-[26px]">manage_search</span></span>
        <h1 className="mt-5 text-3xl font-semibold tracking-tight text-on-surface">智能检索</h1>
        <p className="mt-2 text-sm leading-6 text-on-surface-variant">通过AI语义理解快速定位企业知识。</p>

        <form onSubmit={submit} className="mt-7 flex flex-col gap-3 rounded-2xl border border-white bg-white p-2 shadow-[0_10px_35px_rgba(37,70,125,0.10)] sm:flex-row sm:items-center">
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">搜索问题或关键词</span>
            <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-[21px] text-on-surface-variant">search</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="请输入问题或关键词..." className="w-full rounded-xl border-0 bg-transparent py-3 pl-11 pr-4 text-sm text-on-surface outline-none placeholder:text-[#8c93a5]" />
          </label>
          <button type="submit" disabled={!query.trim() || loading} className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-[#0044ad] disabled:cursor-not-allowed disabled:bg-[#aebbd1]">
            <span className="material-symbols-outlined text-[19px]">travel_explore</span>{loading ? '检索中...' : '开始搜索'}
          </button>
        </form>
        <div className="mt-4 flex items-center justify-center gap-2 text-xs text-on-surface-variant">
          <span>示例：</span><button type="button" onClick={() => setQuery('员工年假政策')} className="font-medium text-primary hover:underline">员工年假政策</button>
        </div>
      </div>
    </section>
  )
}
