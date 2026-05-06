export function Header() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8 lg:px-10">
        <div>
          <p className="text-sm font-semibold text-slate-950">Local-Code-Wiki-RAG</p>
          <p className="text-xs text-slate-500">Developer onboarding workspace</p>
        </div>
        <div className="rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600">
          Mock mode
        </div>
      </div>
    </header>
  )
}
