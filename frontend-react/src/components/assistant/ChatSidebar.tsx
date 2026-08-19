export type Conversation = {
  id: string
  title: string
  updatedAt: string
}

type ChatSidebarProps = {
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onNewChat: () => void
  loading?: boolean
  error?: boolean
}

export function ChatSidebar({ conversations, activeId, onSelect, onNewChat, loading = false, error = false }: ChatSidebarProps) {
  return (
    <aside className="flex h-full min-h-[640px] flex-col border-r border-[#e7eaf3] bg-[#fbfcff] p-4">
      <div className="flex items-center justify-between px-1">
        <div><p className="text-sm font-semibold text-on-surface">历史对话</p><p className="mt-1 text-xs text-on-surface-variant">最近的知识库问答</p></div>
        <span className="material-symbols-outlined text-[20px] text-on-surface-variant">history</span>
      </div>

      <button type="button" onClick={onNewChat} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#0044ad]"><span className="material-symbols-outlined text-[19px]">add</span>新建对话</button>

      <nav aria-label="历史对话" className="mt-5 space-y-2">
        {loading && <p className="px-3 py-4 text-center text-xs text-on-surface-variant">正在加载历史对话...</p>}
        {!loading && error && <p className="rounded-lg bg-red-50 px-3 py-3 text-center text-xs text-red-700">历史对话加载失败</p>}
        {!loading && !error && conversations.length === 0 && <p className="px-3 py-4 text-center text-xs text-on-surface-variant">暂无历史对话</p>}
        {!loading && conversations.map((conversation) => {
          const active = conversation.id === activeId
          return (
            <button key={conversation.id} type="button" onClick={() => onSelect(conversation.id)} className={`w-full rounded-xl px-3 py-3 text-left transition-colors ${active ? 'bg-primary-fixed text-primary' : 'text-on-surface-variant hover:bg-white hover:text-on-surface'}`}>
              <span className="flex items-center gap-2.5"><span className="material-symbols-outlined text-[18px]">chat_bubble</span><span className="truncate text-sm font-medium">{conversation.title}</span></span>
              <span className="ml-7 mt-1 block text-[11px] opacity-70">{conversation.updatedAt}</span>
            </button>
          )
        })}
      </nav>

      <div className="mt-auto rounded-xl border border-blue-100 bg-blue-50/70 p-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-primary"><span className="material-symbols-outlined text-[17px]">verified_user</span>企业知识库已连接</div>
        <p className="mt-1.5 text-[11px] leading-5 text-on-surface-variant">回答将优先引用已索引的企业文档。</p>
      </div>
    </aside>
  )
}
