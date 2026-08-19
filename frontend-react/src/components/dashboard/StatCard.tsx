type StatCardProps = {
  label: string
  value: string
  icon: string
  iconClassName?: string
  status?: 'online' | 'offline'
}

export function StatCard({ label, value, icon, iconClassName = 'bg-[#e7efff] text-primary', status }: StatCardProps) {
  return (
    <article className="rounded-2xl border border-white bg-white p-5 shadow-ambient sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-on-surface-variant">{label}</p>
          <div className="mt-3 flex items-center gap-2">
            {status && <span className={`h-2.5 w-2.5 rounded-full ring-4 ${status === 'online' ? 'bg-emerald-500 ring-emerald-50' : 'bg-red-500 ring-red-50'}`} />}
            <p className="text-3xl font-semibold tracking-tight text-on-surface">{value}</p>
          </div>
        </div>
        <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${iconClassName}`}>
          <span className="material-symbols-outlined text-[22px]">{icon}</span>
        </span>
      </div>
    </article>
  )
}
