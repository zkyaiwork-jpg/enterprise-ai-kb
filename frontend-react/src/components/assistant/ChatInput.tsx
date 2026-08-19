import { useState, type FormEvent, type KeyboardEvent } from 'react'

type ChatInputProps = {
  onSend: (message: string) => void
  disabled?: boolean
  value?: string
}

export function ChatInput({ onSend, disabled = false, value = '' }: ChatInputProps) {
  const [input, setInput] = useState(value)

  const submit = () => {
    const message = input.trim()
    if (!message || disabled) return
    onSend(message)
    setInput('')
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    submit()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl border border-[#dce3ef] bg-white p-2 shadow-[0_8px_30px_rgba(33,55,95,0.08)] focus-within:border-primary/50">
      <textarea
        value={input}
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={handleKeyDown}
        rows={2}
        placeholder="请输入您的问题..."
        className="max-h-32 min-h-[48px] w-full resize-none border-0 bg-transparent px-3 py-2 text-sm leading-6 text-on-surface outline-none placeholder:text-[#8c93a5]"
      />
      <div className="flex items-center justify-between border-t border-[#edf0f5] px-2 pt-2">
        <span className="flex items-center gap-1.5 text-[11px] text-on-surface-variant"><span className="material-symbols-outlined text-[16px]">shield</span>回答基于企业知识库</span>
        <button type="submit" disabled={disabled || !input.trim()} className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-[#0044ad] disabled:cursor-not-allowed disabled:bg-[#b7c3d8]"><span className="material-symbols-outlined text-[18px]">send</span>发送</button>
      </div>
    </form>
  )
}
