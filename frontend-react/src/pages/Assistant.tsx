import { useEffect, useMemo, useRef, useState } from 'react'

import { getChatHistory, sendMessage as sendChatMessage, type ChatHistorySession } from '../api/chat'
import { ChatInput } from '../components/assistant/ChatInput'
import { ChatMessage, type Message } from '../components/assistant/ChatMessage'
import { ChatSidebar, type Conversation } from '../components/assistant/ChatSidebar'
import { SuggestedQuestions } from '../components/assistant/SuggestedQuestions'


const quickQuestions = ['员工请假流程', '查看产品资料', '查询项目文档']


function sessionMessages(session: ChatHistorySession): Message[] {
  return session.messages.flatMap((record) => [
    {
      id: `history-${record.id}-question`,
      role: 'user' as const,
      content: record.question,
    },
    {
      id: `history-${record.id}-answer`,
      role: 'assistant' as const,
      content: record.answer,
      sources: record.sources ?? [],
    },
  ])
}


function formatHistoryTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}


export function Assistant() {
  const [activeConversation, setActiveConversation] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [historySessions, setHistorySessions] = useState<ChatHistorySession[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [historyError, setHistoryError] = useState(false)
  const [loading, setLoading] = useState(false)
  const requestVersion = useRef(0)
  const userInteracted = useRef(false)

  useEffect(() => {
    let active = true

    async function loadInitialHistory() {
      setHistoryLoading(true)
      setHistoryError(false)
      try {
        const response = await getChatHistory()
        if (!active) return
        const sessions = response.sessions ?? []
        setHistorySessions(sessions)
        if (!userInteracted.current && sessions.length > 0) {
          setActiveConversation(sessions[0].session_id)
          setMessages(sessionMessages(sessions[0]))
        }
      } catch {
        if (active) setHistoryError(true)
      } finally {
        if (active) setHistoryLoading(false)
      }
    }

    void loadInitialHistory()
    return () => { active = false }
  }, [])

  const conversations = useMemo<Conversation[]>(() => historySessions.map((session) => ({
    id: session.session_id,
    title: session.title,
    updatedAt: formatHistoryTime(session.updated_at),
  })), [historySessions])

  const refreshHistory = async () => {
    try {
      const response = await getChatHistory()
      setHistorySessions(response.sessions ?? [])
      setHistoryError(false)
    } catch {
      setHistoryError(true)
    }
  }

  const startNewChat = () => {
    userInteracted.current = true
    requestVersion.current += 1
    setActiveConversation(null)
    setMessages([])
    setLoading(false)
  }

  const handleSendMessage = async (content: string) => {
    if (loading) return

    userInteracted.current = true
    const sessionId = activeConversation ?? crypto.randomUUID()
    if (!activeConversation) setActiveConversation(sessionId)

    const requestId = ++requestVersion.current
    setMessages((current) => [...current, { id: `user-${requestId}`, role: 'user', content }])
    setLoading(true)

    try {
      const response = await sendChatMessage(content, sessionId)
      if (requestVersion.current !== requestId) return

      setMessages((current) => [...current, {
        id: `assistant-${response.id}`,
        role: 'assistant',
        content: response.answer || 'AI未返回有效回答，请稍后重试。',
        sources: response.sources ?? [],
      }])
      await refreshHistory()
    } catch (error) {
      if (requestVersion.current !== requestId) return
      const detail = error instanceof Error ? error.message : ''
      setMessages((current) => [...current, {
        id: `assistant-error-${requestId}`,
        role: 'assistant',
        content: `AI回答失败，请稍后重试。${detail ? `\n\n错误信息：${detail}` : ''}`,
        error: true,
      }])
    } finally {
      if (requestVersion.current === requestId) setLoading(false)
    }
  }

  const selectConversation = (id: string) => {
    const session = historySessions.find((item) => item.session_id === id)
    if (!session) return
    userInteracted.current = true
    requestVersion.current += 1
    setActiveConversation(id)
    setMessages(sessionMessages(session))
    setLoading(false)
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-white bg-white shadow-ambient">
      <div className="grid min-h-[calc(100vh-152px)] lg:grid-cols-[240px_minmax(0,1fr)]">
        <div className="hidden lg:block">
          <ChatSidebar
            conversations={conversations}
            activeId={activeConversation}
            onSelect={selectConversation}
            onNewChat={startNewChat}
            loading={historyLoading}
            error={historyError}
          />
        </div>

        <div className="flex min-w-0 flex-col bg-[#f8faff]">
          <header className="flex items-center justify-between border-b border-[#e7eaf3] bg-white px-5 py-4 sm:px-7">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white"><span className="material-symbols-outlined text-[21px]">smart_toy</span></span>
              <div><h1 className="text-base font-semibold text-on-surface">企业AI助手</h1><p className="mt-0.5 text-xs text-on-surface-variant">基于企业知识库智能回答问题</p></div>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />RAG 问答</span>
          </header>

          <div className="flex-1 overflow-y-auto px-4 py-7 sm:px-7">
            <div className="mx-auto max-w-4xl">
              {messages.length === 0 ? (
                <div className="flex min-h-[360px] flex-col items-center justify-center text-center">
                  <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-fixed to-blue-100 text-primary"><span className="material-symbols-outlined text-3xl">auto_awesome</span></span>
                  <h2 className="mt-5 text-2xl font-semibold text-on-surface">您好，我是企业AI助手</h2>
                  <p className="mt-2 text-sm text-on-surface-variant">可以帮助您查询企业知识。</p>
                  <div className="mt-7"><SuggestedQuestions questions={quickQuestions} onSelect={(question) => void handleSendMessage(question)} /></div>
                </div>
              ) : (
                <div className="space-y-7">
                  {messages.map((message) => <ChatMessage key={message.id} message={message} />)}
                  {loading && (
                    <div className="flex items-center gap-3 text-sm text-on-surface-variant">
                      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-white"><span className="material-symbols-outlined text-[19px]">auto_awesome</span></span>
                      <span className="rounded-2xl border border-[#e5e9f2] bg-white px-4 py-3">AI正在思考...</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          <footer className="border-t border-[#e7eaf3] bg-white px-4 py-4 sm:px-7">
            <div className="mx-auto max-w-4xl">
              {messages.length > 0 && <div className="mb-3"><SuggestedQuestions questions={quickQuestions} onSelect={(question) => void handleSendMessage(question)} /></div>}
              <ChatInput onSend={(question) => void handleSendMessage(question)} disabled={loading} />
              <p className="mt-2 text-center text-[11px] text-on-surface-variant">AI生成内容仅供参考，重要信息请核对引用原文</p>
            </div>
          </footer>
        </div>
      </div>
    </section>
  )
}
