import type { PropsWithChildren } from 'react'

import { Header } from './Header'
import { Sidebar } from './Sidebar'

export function AppLayout({ children }: PropsWithChildren) {
  return (
    <div className="min-h-screen bg-[#f5f7fb] text-slate-900">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="min-w-0 flex-1 px-5 py-6 sm:px-8 lg:px-10">{children}</main>
      </div>
    </div>
  )
}
