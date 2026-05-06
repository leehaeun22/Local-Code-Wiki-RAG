import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Projects' },
  { to: '/projects/new', label: 'New project' },
]

export function Sidebar() {
  return (
    <aside className="hidden min-h-[calc(100vh-4rem)] w-64 shrink-0 border-r border-slate-200 bg-white px-4 py-6 lg:block">
      <nav className="space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
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
