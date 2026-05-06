import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Projects' },
  { to: '/projects/local-code-wiki-rag', label: 'Documents' },
  { to: '/projects/local-code-wiki-rag', label: 'Chat' },
  { to: '/projects/new', label: 'Settings' },
]

export function Sidebar() {
  return (
    <aside className="hidden min-h-[calc(100vh-4rem)] w-64 shrink-0 border-r border-slate-200 bg-white px-4 py-6 lg:block">
      <div className="mb-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p className="text-xs font-medium uppercase text-slate-500">Workspace</p>
        <p className="mt-2 text-sm font-semibold text-slate-950">RepoWiki Console</p>
      </div>
      <nav className="space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.label}
            to={link.to}
            className={({ isActive }) =>
              [
                'flex h-10 items-center rounded-md px-3 text-sm font-medium transition',
                isActive
                  ? 'bg-sky-50 text-sky-800'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-950',
              ].join(' ')
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
