export function Header() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="flex h-16 items-center justify-between px-5 sm:px-8 lg:px-10">
        <div>
          <p className="text-base font-semibold text-slate-950">Local Code Wiki RAG</p>
          <p className="text-xs text-slate-500">Repository wiki and onboarding chat workspace</p>
        </div>
        <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
          Development mode
        </div>
      </div>
    </header>
  )
}
