import { Link, useParams } from 'react-router-dom'

const projectSummary = {
  name: 'Local-Code-Wiki-RAG',
  repositoryUrl: 'https://github.com/leehaeun22/Local-Code-Wiki-RAG',
  status: 'Ready for documentation',
  metrics: [
    { label: 'Scanned files', value: '142' },
    { label: 'Generated docs', value: '24' },
    { label: 'Code chunks', value: '386' },
  ],
}

export function ProjectDetailPage() {
  const { projectId } = useParams()

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

      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-1 border-b border-slate-100 pb-5">
          <span className="text-sm text-slate-500">Project ID</span>
          <strong className="text-base text-slate-950">{projectId}</strong>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          {projectSummary.metrics.map((metric) => (
            <div key={metric.label} className="rounded-md bg-slate-50 p-4">
              <p className="text-sm text-slate-500">{metric.label}</p>
              <p className="mt-2 text-2xl font-semibold text-slate-950">{metric.value}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-950">Documentation queue</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            File tree, document viewer, and generated wiki pages will be connected in the next
            frontend screens.
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-950">Chat readiness</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            RAG search and chatbot answers are not connected yet. This area is reserved for the
            onboarding assistant UI.
          </p>
        </div>
      </div>
    </section>
  )
}
