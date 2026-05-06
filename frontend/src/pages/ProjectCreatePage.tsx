export function ProjectCreatePage() {
  return (
    <section className="max-w-3xl space-y-6">
      <div>
        <p className="text-sm font-medium text-sky-700">Create project</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-950">Connect a GitHub repository</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Paste a GitHub URL to prepare the project card and future repository scan workflow.
        </p>
      </div>

      <form className="space-y-5 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <label className="block">
          <span className="text-sm font-medium text-slate-700">GitHub repository URL</span>
          <input
            className="mt-2 h-11 w-full rounded-md border border-slate-300 px-3 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            defaultValue="https://github.com/leehaeun22/Local-Code-Wiki-RAG"
            type="url"
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium text-slate-700">Notes</span>
          <textarea
            className="mt-2 min-h-28 w-full rounded-md border border-slate-300 px-3 py-3 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            placeholder="Optional onboarding context for this repository"
          />
        </label>

        <button
          className="inline-flex h-10 items-center justify-center rounded-md bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
          type="button"
        >
          Add mock repository
        </button>
      </form>
    </section>
  )
}
