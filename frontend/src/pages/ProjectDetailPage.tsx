import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { projectApi } from '../api/projectApi'
import { ChatPanel } from '../components/chat/ChatPanel'
import { DocumentViewer } from '../components/document/DocumentViewer'
import { FileTree } from '../components/file/FileTree'

export function ProjectDetailPage() {
  const params = useParams()
  const projectId = params.projectId ?? ''
  const projectQuery = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectApi.getProject(projectId),
    enabled: Boolean(projectId),
  })
  const project = projectQuery.data

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
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            {project?.name ?? 'Loading project...'}
          </h1>
          <p className="mt-2 break-all text-sm text-slate-500">
            {project?.repository_url ?? 'Repository URL is loading.'}
          </p>
          {projectQuery.isError ? (
            <p className="mt-2 text-sm text-red-600">Failed to load project metadata.</p>
          ) : null}
        </div>
        <Link
          to="/"
          className="inline-flex h-10 items-center justify-center rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
        >
          Back to projects
        </Link>
      </div>

      <div className="grid min-h-[640px] gap-4 xl:grid-cols-[280px_minmax(0,1fr)_340px]">
        <FileTree projectId={projectId} projectLocalPath={project?.local_path ?? null} />

        <DocumentViewer projectId={projectId} />

        <ChatPanel projectId={projectId} />
      </div>
    </section>
  )
}
