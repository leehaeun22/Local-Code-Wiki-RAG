import { Link, useParams } from 'react-router-dom'
import axios from 'axios'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { projectApi } from '../api/projectApi'
import { ChatPanel } from '../components/chat/ChatPanel'
import { DocumentViewer } from '../components/document/DocumentViewer'
import { FileTree } from '../components/file/FileTree'

type AnalysisStep = 'idle' | 'clone' | 'scan' | 'chunks' | 'documents' | 'complete'

const ANALYSIS_STEP_LABELS: Record<AnalysisStep, string> = {
  idle: 'Clone, scan, Prepare Docs, Generate를 한 번에 실행합니다.',
  clone: 'Repository clone 중...',
  scan: '파일 scan 중...',
  chunks: 'code chunks 생성 중...',
  documents: 'wiki 문서 생성 중...',
  complete: '분석 완료',
}

const ANALYSIS_STEP_NAMES: Partial<Record<AnalysisStep, string>> = {
  clone: 'Repository clone',
  scan: '파일 scan',
  chunks: 'code chunks 생성',
  documents: 'wiki 문서 생성',
}

class AnalysisPipelineError extends Error {
  step: AnalysisStep

  constructor(step: AnalysisStep, error: unknown) {
    super(getErrorMessage(error))
    this.name = 'AnalysisPipelineError'
    this.step = step
  }
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const responseDetail = error.response?.data?.detail
    const responseMessage = error.response?.data?.message

    if (typeof responseDetail === 'string' && responseDetail.trim()) {
      return responseDetail
    }

    if (typeof responseMessage === 'string' && responseMessage.trim()) {
      return responseMessage
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message
  }

  return 'Request failed.'
}

export function ProjectDetailPage() {
  const params = useParams()
  const projectId = params.projectId ?? ''
  const queryClient = useQueryClient()
  const [analysisStep, setAnalysisStep] = useState<AnalysisStep>('idle')
  const [analysisError, setAnalysisError] = useState('')

  const projectQuery = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectApi.getProject(projectId),
    enabled: Boolean(projectId),
  })
  const project = projectQuery.data

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      const runStep = async (step: AnalysisStep, action: () => Promise<unknown>) => {
        setAnalysisStep(step)

        try {
          await action()
        } catch (error) {
          throw new AnalysisPipelineError(step, error)
        }
      }

      setAnalysisError('')
      await runStep('clone', () => projectApi.cloneProject(projectId))
      await runStep('scan', () => projectApi.scanProject(projectId))
      await runStep('chunks', () => projectApi.generateCodeChunks(projectId))
      await runStep('documents', () =>
        projectApi.generateDocuments(projectId, {
          language: project?.settings?.default_language ?? 'ko',
        }),
      )
    },
    onError: (error) => {
      if (error instanceof AnalysisPipelineError) {
        setAnalysisError(`${ANALYSIS_STEP_NAMES[error.step]} 실패: ${error.message}`)
        return
      }

      setAnalysisError(`Repository 분석 실패: ${getErrorMessage(error)}`)
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['project', projectId] }),
        queryClient.invalidateQueries({ queryKey: ['project-file-tree', projectId] }),
        queryClient.invalidateQueries({ queryKey: ['project-code-chunks', projectId] }),
        queryClient.invalidateQueries({ queryKey: ['project-documents', projectId] }),
        queryClient.invalidateQueries({ queryKey: ['project-document', projectId] }),
      ])
      await Promise.all([
        queryClient.fetchQuery({
          queryKey: ['project-file-tree', projectId],
          queryFn: () => projectApi.getFileTree(projectId),
        }),
        queryClient.fetchQuery({
          queryKey: ['project-documents', projectId],
          queryFn: () => projectApi.getDocuments(projectId),
        }),
      ])
      setAnalysisStep('complete')
      setAnalysisError('')
    },
  })

  const isAnalyzing = analyzeMutation.isPending

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

      <div className="rounded-lg border border-sky-200 bg-sky-50 p-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-sky-950">Analyze Repository</p>
            <p className="mt-1 text-sm text-sky-800">{ANALYSIS_STEP_LABELS[analysisStep]}</p>
          </div>
          <button
            className="h-10 rounded-md bg-sky-700 px-4 text-sm font-semibold text-white transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-sky-300"
            disabled={isAnalyzing || !project}
            onClick={() => analyzeMutation.mutate()}
            type="button"
          >
            {isAnalyzing ? 'Analyzing...' : 'Analyze Repository'}
          </button>
        </div>
        {analysisError ? (
          <p className="mt-3 rounded-md bg-red-50 p-3 text-sm text-red-700">{analysisError}</p>
        ) : null}
      </div>

      <div className="grid min-h-[640px] gap-4 xl:grid-cols-[280px_minmax(0,1fr)_340px]">
        <FileTree
          disabled={isAnalyzing}
          projectId={projectId}
          projectLocalPath={project?.local_path ?? null}
        />

        <DocumentViewer disabled={isAnalyzing} projectId={projectId} />

        <ChatPanel projectId={projectId} />
      </div>
    </section>
  )
}
