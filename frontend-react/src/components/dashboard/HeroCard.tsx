import { Link } from 'react-router-dom'

export function HeroCard({ userName }: { userName: string }) {
  return (
    <section className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-[#eaf2ff] via-[#f3f7ff] to-white px-7 py-9 shadow-ambient sm:px-10 sm:py-11">
      <div className="absolute -right-16 -top-20 h-64 w-64 rounded-full bg-[#cfe0ff]/55" />
      <div className="absolute -bottom-24 right-28 h-52 w-52 rounded-full bg-white/60" />

      <div className="relative max-w-2xl">
        <span className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-primary shadow-sm">
          <span className="material-symbols-outlined">auto_awesome</span>
        </span>
        <h1 className="text-3xl font-semibold tracking-tight text-on-surface sm:text-4xl">你好，{userName} 👋</h1>
        <p className="mt-4 max-w-xl text-base leading-7 text-on-surface-variant sm:text-lg">
          欢迎使用企业AI知识库助手，<br className="hidden sm:block" />
          让企业知识快速沉淀和高效调用。
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to="/assistant"
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#0044ad]"
          >
            <span className="material-symbols-outlined text-[20px]">forum</span>
            开始问答
          </Link>
          <Link
            to="/knowledge"
            className="inline-flex items-center gap-2 rounded-xl border border-white bg-white/90 px-5 py-3 text-sm font-semibold text-primary shadow-sm transition-colors hover:bg-white"
          >
            <span className="material-symbols-outlined text-[20px]">upload_file</span>
            上传文档
          </Link>
        </div>
      </div>
    </section>
  )
}
