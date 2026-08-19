import type { ComponentPropsWithoutRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import type { ChatSource } from '../../api/chat'
import { SourceCard } from './SourceCard'


export type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
  error?: boolean
}


const markdownComponents = {
  h1: ({ children }: ComponentPropsWithoutRef<'h1'>) => <h1 className="mb-3 mt-1 text-2xl font-semibold leading-tight text-on-surface">{children}</h1>,
  h2: ({ children }: ComponentPropsWithoutRef<'h2'>) => <h2 className="mb-2.5 mt-5 text-xl font-semibold leading-tight text-on-surface">{children}</h2>,
  h3: ({ children }: ComponentPropsWithoutRef<'h3'>) => <h3 className="mb-2 mt-4 text-base font-semibold text-on-surface">{children}</h3>,
  p: ({ children }: ComponentPropsWithoutRef<'p'>) => <p className="my-2 leading-7 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }: ComponentPropsWithoutRef<'ul'>) => <ul className="my-3 list-disc space-y-1.5 pl-6">{children}</ul>,
  ol: ({ children }: ComponentPropsWithoutRef<'ol'>) => <ol className="my-3 list-decimal space-y-1.5 pl-6">{children}</ol>,
  li: ({ children }: ComponentPropsWithoutRef<'li'>) => <li className="pl-1 leading-6 marker:text-primary">{children}</li>,
  strong: ({ children }: ComponentPropsWithoutRef<'strong'>) => <strong className="font-semibold text-on-surface">{children}</strong>,
  blockquote: ({ children }: ComponentPropsWithoutRef<'blockquote'>) => <blockquote className="my-4 border-l-4 border-primary/40 bg-[#f5f8ff] py-2 pl-4 pr-3 text-on-surface-variant">{children}</blockquote>,
  pre: ({ children }: ComponentPropsWithoutRef<'pre'>) => <pre className="my-4 overflow-x-auto rounded-xl bg-[#20242e] p-4 text-[13px] leading-6 text-[#edf2ff]">{children}</pre>,
  code: ({ children, className }: ComponentPropsWithoutRef<'code'>) => (
    <code className={className ? `${className} font-mono` : 'rounded-md bg-surface-container px-1.5 py-0.5 font-mono text-[0.9em] text-primary'}>{children}</code>
  ),
  a: ({ children, href }: ComponentPropsWithoutRef<'a'>) => <a href={href} target="_blank" rel="noreferrer noopener" className="font-medium text-primary underline decoration-primary/30 underline-offset-2 hover:decoration-primary">{children}</a>,
  hr: () => <hr className="my-5 border-[#e2e6ef]" />,
}


export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-white shadow-sm ${message.error ? 'bg-error' : 'bg-primary'}`}>
          <span className="material-symbols-outlined text-[20px]">{message.error ? 'error' : 'auto_awesome'}</span>
        </span>
      )}

      <div className={`max-w-[760px] ${isUser ? 'rounded-2xl rounded-tr-md bg-primary px-5 py-3.5 text-white' : 'min-w-0 flex-1'}`}>
        {!isUser && <p className={`mb-2 text-xs font-semibold ${message.error ? 'text-error' : 'text-primary'}`}>企业AI助手</p>}

        {isUser ? (
          <div className="whitespace-pre-line text-sm leading-7">{message.content}</div>
        ) : (
          <div className={`rounded-2xl rounded-tl-md border bg-white px-5 py-4 text-sm leading-7 shadow-[0_2px_8px_rgba(28,39,63,0.04)] ${message.error ? 'border-red-100 text-red-700' : 'border-[#e5e9f2] text-on-surface'}`}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml components={markdownComponents}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 rounded-2xl bg-[#f6f9ff] p-4">
            <p className="flex items-center gap-2 text-xs font-semibold text-on-surface"><span className="material-symbols-outlined text-[17px] text-primary">library_books</span>回答依据</p>
            <div className="mt-3 flex flex-col gap-3 xl:flex-row">
              {message.sources.map((source, index) => (
                <SourceCard key={`${source.filename ?? 'source'}-${source.chunk_index ?? index}`} source={source} />
              ))}
            </div>
          </div>
        )}
      </div>

      {isUser && <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#e7efff] text-sm font-semibold text-primary">张</span>}
    </div>
  )
}
