type SearchEmptyProps = {
  state: 'initial' | 'loading' | 'empty' | 'error'
  detail?: string
}

const content = {
  initial: { icon: 'search', title: '请输入关键词开始搜索', description: 'AI将理解您的问题，并从企业知识库中匹配相关内容。' },
  loading: { icon: 'travel_explore', title: '正在检索知识库...', description: '正在进行语义分析与向量匹配，请稍候。' },
  empty: { icon: 'search_off', title: '未找到相关知识。', description: '请尝试更换关键词或扩大检索范围。' },
  error: { icon: 'cloud_off', title: '检索服务不可用。', description: '请确认后端服务已经启动，稍后重试。' },
}

export function SearchEmpty({ state, detail }: SearchEmptyProps) {
  const item = content[state]
  return (
    <section className="flex min-h-[300px] flex-col items-center justify-center rounded-2xl border border-dashed border-[#d7deea] bg-white/70 px-6 text-center">
      <span className={`flex h-14 w-14 items-center justify-center rounded-2xl ${state === 'error' ? 'bg-red-50 text-error' : 'bg-primary-fixed text-primary'} ${state === 'loading' ? 'animate-pulse' : ''}`}><span className="material-symbols-outlined text-[28px]">{item.icon}</span></span>
      <h2 className="mt-5 text-lg font-semibold text-on-surface">{item.title}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-on-surface-variant">{item.description}</p>
      {state === 'error' && detail && <p className="mt-3 max-w-lg rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{detail}</p>}
    </section>
  )
}
