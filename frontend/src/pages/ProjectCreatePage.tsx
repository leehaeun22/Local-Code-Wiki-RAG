import { type FormEvent, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { projectApi } from '../api/projectApi'
import type { ProjectCreateRequest } from '../types/project'

type ProjectCreateErrors = Partial<Record<keyof ProjectCreateRequest, string>>

const initialForm: ProjectCreateRequest = {
  name: '',
  repository_url: '',
  branch: 'main',
  description: '',
  default_language: 'ko',
  llm_mode: 'cloud',
}

function validateForm(form: ProjectCreateRequest) {
  const errors: ProjectCreateErrors = {}

  if (!form.name.trim()) {
    errors.name = 'Project Name is required.'
  }

  if (!form.repository_url.trim()) {
    errors.repository_url = 'GitHub Repository URL is required.'
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
  const createProjectMutation = useMutation({
    mutationFn: projectApi.createProject,
    onSuccess: (project) => {
      navigate(`/projects/${project.id}`)
    },
  })

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

    createProjectMutation.mutate({
      ...form,
      description: form.description?.trim() || null,
    })
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
            onChange={(event) => updateForm('name', event.target.value)}
            placeholder="Local-Code-Wiki-RAG"
            type="text"
            value={form.name}
          />
          {errors.name ? (
            <p className="mt-2 text-sm text-red-600">{errors.name}</p>
          ) : null}
        </label>

        <label className="block">
          <span className="text-sm font-medium text-slate-700">GitHub Repository URL</span>
          <input
            className="mt-2 h-11 w-full rounded-md border border-slate-300 px-3 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            onChange={(event) => updateForm('repository_url', event.target.value)}
            placeholder="https://github.com/owner/repository"
            type="url"
            value={form.repository_url}
          />
          {errors.repository_url ? (
            <p className="mt-2 text-sm text-red-600">{errors.repository_url}</p>
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

        <label className="block">
          <span className="text-sm font-medium text-slate-700">Description</span>
          <textarea
            className="mt-2 min-h-24 w-full rounded-md border border-slate-300 px-3 py-3 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            onChange={(event) => updateForm('description', event.target.value)}
            placeholder="Optional onboarding context for this repository"
            value={form.description ?? ''}
          />
        </label>

        <div className="grid gap-5 md:grid-cols-2">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Default Language</span>
            <select
              className="mt-2 h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
              onChange={(event) =>
                updateForm('default_language', event.target.value as ProjectCreateRequest['default_language'])
              }
              value={form.default_language}
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
                updateForm('llm_mode', event.target.value as ProjectCreateRequest['llm_mode'])
              }
              value={form.llm_mode}
            >
              <option value="cloud">cloud</option>
              <option value="local">local</option>
            </select>
          </label>
        </div>

        <button
          className="inline-flex h-10 items-center justify-center rounded-md bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={createProjectMutation.isPending}
          type="submit"
        >
          {createProjectMutation.isPending ? 'Creating...' : 'Create project'}
        </button>
        {createProjectMutation.isError ? (
          <p className="text-sm text-red-600">
            Failed to create project. Check that the backend API is running.
          </p>
        ) : null}
      </form>
    </section>
  )
}
