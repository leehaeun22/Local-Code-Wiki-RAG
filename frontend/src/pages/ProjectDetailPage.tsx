import { Link, useParams } from 'react-router-dom'

import { ChatPanel } from '../components/chat/ChatPanel'
import { FileTree } from '../components/file/FileTree'

const projectSummary = {
  name: 'Local-Code-Wiki-RAG',
  repositoryUrl: 'https://github.com/leehaeun22/Local-Code-Wiki-RAG',
  status: 'Ready',
}

export function ProjectDetailPage() {
  const { projectId } = useParams()

  if (!projectId) {
    return (
      <section className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">
        Project ID is missing.
      </section>
    )
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-sky-700">Project detail</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">{projectSummary.name}</h1>
          <p className="mt-2 break-all text-sm text-slate-500">{projectSummary.repositoryUrl}</p>
        </div>
        <Link
          to="/"
          className="inline-flex h-10 items-center justify-center rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
        >
          Back to projects
        </Link>
      </div>

      <div className="grid min-h-[640px] gap-4 xl:grid-cols-[280px_minmax(0,1fr)_340px]">
        <FileTree projectId={projectId} />

        <article className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-950">Document Viewer</p>
                <p className="mt-1 text-xs text-slate-500">Project ID: {projectId}</p>
              </div>
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                {projectSummary.status}
              </span>
            </div>
          </div>
          <div className="space-y-5 p-6">
            <div>
              <h2 className="text-2xl font-semibold text-slate-950">ProjectListPage.tsx</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                This mock document explains how the project list page presents registered
                repositories, scan state, generated document counts, and navigation into the
                repository workspace.
              </p>
            </div>
            <div className="rounded-lg bg-slate-950 p-4 font-mono text-sm leading-6 text-slate-100">
              <p>frontend/src/pages/ProjectListPage.tsx</p>
              <p className="text-slate-400">Mock summary generated from repository analysis.</p>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {['Files scanned', 'Documents', 'Chunks'].map((label, index) => (
                <div key={label} className="rounded-md border border-slate-200 p-4">
                  <p className="text-xs font-medium text-slate-500">{label}</p>
                  <p className="mt-2 text-xl font-semibold text-slate-950">
                    {['142', '24', '386'][index]}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </article>

        <ChatPanel />
      </div>
    </section>
  )
}
