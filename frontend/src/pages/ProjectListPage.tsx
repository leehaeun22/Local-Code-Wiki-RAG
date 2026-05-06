import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { projectApi } from '../api/projectApi'

export function ProjectListPage() {
  const {
    data: projects = [],
    isError,
    isLoading,
  } = useQuery({
    queryKey: ['projects'],
    queryFn: projectApi.getProjects,
  })

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-sky-700">Projects</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">Repository wiki projects</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Track repository scans, generated wiki pages, and chat readiness from one workspace.
          </p>
        </div>
        <Link
          to="/projects/new"
          className="inline-flex h-10 items-center justify-center rounded-md bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
        >
          New project
        </Link>
      </div>

      {isLoading ? (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm">
          Loading projects...
        </div>
      ) : null}

      {isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">
          Failed to load projects. Check that the backend API is running.
        </div>
      ) : null}

      {!isLoading && !isError && projects.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm">
          No projects yet. Create a project to connect a GitHub repository.
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {projects.map((project) => (
          <Link
            key={project.id}
            to={`/projects/${project.id}`}
            className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-sky-300 hover:shadow-md"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-950">{project.name}</h2>
                <p className="mt-1 break-all text-sm text-slate-500">{project.repository_url}</p>
              </div>
              <span className="shrink-0 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                {project.settings?.llm_mode ?? 'cloud'}
              </span>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-600">
              {project.description || 'No description provided.'}
            </p>
            <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-sm text-slate-500">
              <span>Branch {project.branch}</span>
              <span>Updated {new Date(project.updated_at).toLocaleDateString()}</span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  )
}
