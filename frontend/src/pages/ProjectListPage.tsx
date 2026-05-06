import { Link } from 'react-router-dom'

import type { Project } from '../types/project'

const mockProjects: Project[] = [
  {
    id: 'local-code-wiki-rag',
    name: 'Local-Code-Wiki-RAG',
    repositoryUrl: 'https://github.com/leehaeun22/Local-Code-Wiki-RAG',
    description: 'Repository documentation and RAG chatbot for developer onboarding.',
    status: 'Ready',
    documentCount: 24,
    updatedAt: '2026-05-06',
  },
  {
    id: 'commerce-admin',
    name: 'Commerce Admin',
    repositoryUrl: 'https://github.com/example/commerce-admin',
    description: 'Admin dashboard sample prepared for file tree and document viewer screens.',
    status: 'Scanning',
    documentCount: 8,
    updatedAt: '2026-05-05',
  },
]

export function ProjectListPage() {
  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-sky-700">Projects</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">Repository workspace</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Registered repositories will appear here with scan progress, generated documents, and
            onboarding chat access.
          </p>
        </div>
        <Link
          to="/projects/new"
          className="inline-flex h-10 items-center justify-center rounded-md bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
        >
          New project
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {mockProjects.map((project) => (
          <Link
            key={project.id}
            to={`/projects/${project.id}`}
            className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-sky-300 hover:shadow-md"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-950">{project.name}</h2>
                <p className="mt-1 break-all text-sm text-slate-500">{project.repositoryUrl}</p>
              </div>
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                {project.status}
              </span>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-600">{project.description}</p>
            <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-sm text-slate-500">
              <span>{project.documentCount} docs</span>
              <span>Updated {project.updatedAt}</span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  )
}
