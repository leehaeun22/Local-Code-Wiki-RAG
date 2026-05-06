import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { ProjectCreateRequest } from '../types/project'

type ProjectCreateErrors = Partial<Record<keyof ProjectCreateRequest, string>>

const initialForm: ProjectCreateRequest = {
  projectName: '',
  repositoryUrl: '',
  branch: 'main',
  defaultLanguage: 'ko',
  llmMode: 'cloud',
}

function validateForm(form: ProjectCreateRequest) {
  const errors: ProjectCreateErrors = {}

  if (!form.projectName.trim()) {
    errors.projectName = 'Project Name is required.'
  }

  if (!form.repositoryUrl.trim()) {
    errors.repositoryUrl = 'GitHub Repository URL is required.'
  }

  if (!form.branch.trim()) {
    errors.branch = 'Branch is required.'
  }

  return errors
}

export function ProjectCreatePage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<ProjectCreateRequest>(initialForm)
  const [errors, setErrors] = useState<ProjectCreateErrors>({})

  const updateForm = <K extends keyof ProjectCreateRequest>(
    field: K,
    value: ProjectCreateRequest[K],
  ) => {
    setForm((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined }))
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const nextErrors = validateForm(form)
    setErrors(nextErrors)

    if (Object.keys(nextErrors).length > 0) {
      return
    }

    console.log('Project create request:', form)
    navigate('/projects/mock-project-id')
  }

  return (
    <section className="max-w-3xl space-y-6">
      <div>
        <p className="text-sm font-medium text-sky-700">Create project</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-950">Connect a GitHub repository</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Paste a GitHub URL to prepare the project card and future repository scan workflow.
        </p>
      </div>

      <form
        className="space-y-5 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
        onSubmit={handleSubmit}
      >
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Project Name</span>
          <input
            className="mt-2 h-11 w-full rounded-md border border-slate-300 px-3 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            onChange={(event) => updateForm('projectName', event.target.value)}
            placeholder="Local-Code-Wiki-RAG"
            type="text"
            value={form.projectName}
          />
          {errors.projectName ? (
            <p className="mt-2 text-sm text-red-600">{errors.projectName}</p>
          ) : null}
        </label>

        <label className="block">
          <span className="text-sm font-medium text-slate-700">GitHub Repository URL</span>
          <input
            className="mt-2 h-11 w-full rounded-md border border-slate-300 px-3 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            onChange={(event) => updateForm('repositoryUrl', event.target.value)}
            placeholder="https://github.com/owner/repository"
            type="url"
            value={form.repositoryUrl}
          />
          {errors.repositoryUrl ? (
            <p className="mt-2 text-sm text-red-600">{errors.repositoryUrl}</p>
          ) : null}
        </label>

        <label className="block">
          <span className="text-sm font-medium text-slate-700">Branch</span>
          <input
            className="mt-2 h-11 w-full rounded-md border border-slate-300 px-3 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            onChange={(event) => updateForm('branch', event.target.value)}
            placeholder="main"
            type="text"
            value={form.branch}
          />
          {errors.branch ? <p className="mt-2 text-sm text-red-600">{errors.branch}</p> : null}
        </label>

        <div className="grid gap-5 md:grid-cols-2">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Default Language</span>
            <select
              className="mt-2 h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
              onChange={(event) =>
                updateForm('defaultLanguage', event.target.value as ProjectCreateRequest['defaultLanguage'])
              }
              value={form.defaultLanguage}
            >
              <option value="ko">ko</option>
              <option value="en">en</option>
            </select>
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">LLM Mode</span>
            <select
              className="mt-2 h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
              onChange={(event) =>
                updateForm('llmMode', event.target.value as ProjectCreateRequest['llmMode'])
              }
              value={form.llmMode}
            >
              <option value="cloud">cloud</option>
              <option value="local">local</option>
            </select>
          </label>
        </div>

        <button
          className="inline-flex h-10 items-center justify-center rounded-md bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
          type="submit"
        >
          Create project
        </button>
      </form>
    </section>
  )
}
