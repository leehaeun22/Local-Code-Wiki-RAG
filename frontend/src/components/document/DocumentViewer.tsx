import { useEffect, useState, type ComponentPropsWithoutRef } from 'react'
import axios from 'axios'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'

import { projectApi } from '../../api/projectApi'
import type { DocumentLanguage, ProjectDocument } from '../../types/document'

interface DocumentViewerProps {
  disabled?: boolean
  projectId: string
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

function getDocumentId(document: ProjectDocument): string {
  return document.id || document.document_id || ''
}

function isRealDocumentId(documentId: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    documentId,
  )
}

function getRealDocumentId(document: ProjectDocument): string {
  const documentId = getDocumentId(document)
  return isRealDocumentId(documentId) ? documentId : ''
}

const markdownComponents = {
  code({ className, children, ...props }: ComponentPropsWithoutRef<'code'>) {
    const isBlock = Boolean(className)

    if (isBlock) {
      return (
        <code
          {...props}
          className="block whitespace-pre-wrap bg-transparent px-0 py-0 font-mono text-[13px] leading-6 text-slate-100"
        >
          {children}
        </code>
      )
    }

    return (
      <code
        {...props}
        className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[13px] text-slate-800"
      >
        {children}
      </code>
    )
  },
  pre({ children, ...props }: ComponentPropsWithoutRef<'pre'>) {
    return (
      <pre
        {...props}
        className="overflow-x-auto rounded-xl bg-slate-950 p-4 font-mono text-[13px] leading-6 text-slate-100 shadow-inner"
      >
        {children}
      </pre>
    )
  },
}

export function DocumentViewer({ disabled = false, projectId }: DocumentViewerProps) {
  const queryClient = useQueryClient()
  const [language, setLanguage] = useState<DocumentLanguage>('ko')
  const [selectedDocumentId, setSelectedDocumentId] = useState('')
  const [actionError, setActionError] = useState('')
  const [missingDocumentMessage, setMissingDocumentMessage] = useState('')

  const documentsQuery = useQuery({
    queryKey: ['project-documents', projectId],
    queryFn: () => projectApi.getDocuments(projectId),
  })
  const fileTreeQuery = useQuery({
    queryKey: ['project-file-tree', projectId],
    queryFn: () => projectApi.getFileTree(projectId),
  })
  const codeChunksQuery = useQuery({
    queryKey: ['project-code-chunks', projectId],
    queryFn: () => projectApi.getCodeChunks(projectId),
  })

  const documents = documentsQuery.data ?? []
  const fileTree = fileTreeQuery.data ?? []
  const codeChunks = codeChunksQuery.data ?? []
  const hasScannedFiles = fileTree.length > 0
  const hasCodeChunks = codeChunks.length > 0
  const visibleDocuments = documents.filter(
    (document) => document.language === language && Boolean(getRealDocumentId(document)),
  )
  const documentIds = visibleDocuments.map((document) => getRealDocumentId(document))
  const isSelectedIdValid =
    Boolean(selectedDocumentId) &&
    isRealDocumentId(selectedDocumentId) &&
    documentIds.includes(selectedDocumentId)
  const selectedDocumentIdFromList = isSelectedIdValid ? selectedDocumentId : ''

  const documentQuery = useQuery({
    queryKey: ['project-document', projectId, selectedDocumentIdFromList],
    queryFn: async () => {
      console.debug('DocumentViewer detail request', {
        selectedDocumentId,
        documentIds,
        isSelectedIdValid,
      })
      return projectApi.getDocument(projectId, selectedDocumentIdFromList)
    },
    enabled: visibleDocuments.length > 0 && isSelectedIdValid,
    retry: false,
  })

  const generateMutation = useMutation({
    mutationFn: () => projectApi.generateDocuments(projectId, { language }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['project-analysis-status', projectId] })
      const refreshedDocuments = await queryClient.fetchQuery({
        queryKey: ['project-documents', projectId],
        queryFn: () => projectApi.getDocuments(projectId),
      })
      const firstDocumentId =
        refreshedDocuments
          .filter((document) => document.language === language)
          .map((document) => getRealDocumentId(document))
          .find(Boolean) ?? ''

      setSelectedDocumentId(firstDocumentId)
      setActionError('')
      setMissingDocumentMessage('')
    },
    onError: (error) => {
      setActionError(getErrorMessage(error))
    },
  })

  const prepareMutation = useMutation({
    mutationFn: () => projectApi.generateCodeChunks(projectId),
    onSuccess: async () => {
      setActionError('')
      setMissingDocumentMessage('')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['project-analysis-status', projectId] }),
        queryClient.invalidateQueries({ queryKey: ['project-code-chunks', projectId] }),
        queryClient.invalidateQueries({ queryKey: ['project-documents', projectId] }),
      ])
    },
    onError: (error) => {
      setActionError(getErrorMessage(error))
    },
  })

  const isWorking = disabled || generateMutation.isPending || prepareMutation.isPending
  const canPrepareDocs = hasScannedFiles && !isWorking
  const canGenerateDocs = hasCodeChunks && !isWorking

  const workflowNotice = !hasScannedFiles
    ? '1단계: Clone and Scan을 먼저 실행하세요.'
    : !hasCodeChunks
      ? '2단계: Prepare Docs로 code chunks를 생성하세요.'
      : '3단계: Generate로 Wiki 문서를 생성하세요.'

  useEffect(() => {
    if (!missingDocumentMessage && !selectedDocumentId && visibleDocuments[0]) {
      setSelectedDocumentId(getRealDocumentId(visibleDocuments[0]))
    }
  }, [missingDocumentMessage, selectedDocumentId, visibleDocuments])

  useEffect(() => {
    if (visibleDocuments.length === 0) {
      if (selectedDocumentId) {
        setSelectedDocumentId('')
      }
      return
    }

    if (!missingDocumentMessage && selectedDocumentId && !isSelectedIdValid) {
      setSelectedDocumentId(getRealDocumentId(visibleDocuments[0]))
    }
  }, [isSelectedIdValid, missingDocumentMessage, selectedDocumentId, visibleDocuments])

  useEffect(() => {
    if (!documentQuery.isError || !axios.isAxiosError(documentQuery.error)) {
      return
    }

    if (documentQuery.error.response?.status === 404) {
      setSelectedDocumentId('')
      setMissingDocumentMessage('문서를 찾을 수 없습니다. 다시 Generate를 실행하세요.')
    }
  }, [documentQuery.error, documentQuery.isError])

  useEffect(() => {
    if (selectedDocumentIdFromList || visibleDocuments.length === 0) {
      setMissingDocumentMessage('')
    }
  }, [selectedDocumentIdFromList, visibleDocuments.length])

  return (
    <article className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-950">Document Viewer</p>
            <p className="mt-1 text-xs text-slate-500">Project ID: {projectId}</p>
          </div>
          <div className="flex items-end gap-2">
            <label className="text-xs font-medium text-slate-500">
              Language
              <select
                className="mt-1 block h-9 rounded-md border border-slate-300 bg-white px-2 text-xs text-slate-700 outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
                onChange={(event) => {
                  setLanguage(event.target.value as DocumentLanguage)
                  setSelectedDocumentId('')
                  setMissingDocumentMessage('')
                }}
                value={language}
              >
                <option value="ko">ko</option>
                <option value="en">en</option>
              </select>
            </label>
            <button
              className="h-9 rounded-md border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
              disabled={!canPrepareDocs}
              onClick={() => prepareMutation.mutate()}
              type="button"
              title={
                hasScannedFiles
                  ? 'Generate code chunks from scanned files.'
                  : 'Run Clone and Scan before Prepare Docs.'
              }
            >
              {prepareMutation.isPending ? 'Preparing...' : 'Prepare Docs'}
            </button>
            <button
              className="h-9 rounded-md bg-slate-950 px-3 text-xs font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              disabled={!canGenerateDocs}
              onClick={() => generateMutation.mutate()}
              type="button"
              title={
                hasCodeChunks
                  ? 'Generate wiki documents from prepared chunks.'
                  : 'Run Prepare Docs before Generate.'
              }
            >
              {generateMutation.isPending ? 'Generating...' : 'Generate'}
            </button>
          </div>
        </div>
        <div className="mt-3 rounded-md bg-slate-50 p-3 text-xs leading-5 text-slate-600">
          <p className="font-medium text-slate-700">{workflowNotice}</p>
          <p className="mt-1">
            Scan files: {hasScannedFiles ? 'ready' : 'missing'} · Code chunks:{' '}
            {hasCodeChunks ? `${codeChunks.length} ready` : 'missing'}
          </p>
        </div>
        {actionError ? <p className="mt-3 text-sm text-red-600">{actionError}</p> : null}
        {missingDocumentMessage ? (
          <p className="mt-3 text-sm text-red-600">{missingDocumentMessage}</p>
        ) : null}
      </div>

      <div className="grid min-h-[560px] lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="border-b border-slate-100 p-4 lg:border-r lg:border-b-0">
          {documentsQuery.isLoading ? (
            <p className="text-sm text-slate-500">Loading documents...</p>
          ) : null}
          {documentsQuery.isError ? (
            <p className="text-sm text-red-600">Failed to load documents.</p>
          ) : null}
          {!documentsQuery.isLoading && !documentsQuery.isError && visibleDocuments.length === 0 ? (
            <p className="text-sm leading-6 text-slate-500">
              아직 생성된 문서가 없습니다. Clone and Scan, Prepare Docs, Generate 순서로 실행하세요.
            </p>
          ) : null}
          <div className="space-y-2">
            {visibleDocuments.map((document) => {
              const documentId = getRealDocumentId(document)

              return (
                <button
                  className={[
                    'w-full rounded-md px-3 py-2 text-left text-sm transition',
                    selectedDocumentIdFromList === documentId
                      ? 'bg-sky-50 font-medium text-sky-800'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-950',
                  ].join(' ')}
                  key={documentId}
                  onClick={() => {
                    setSelectedDocumentId(documentId)
                    setMissingDocumentMessage('')
                  }}
                  type="button"
                >
                  <span className="block">{document.title}</span>
                  <span className="mt-1 block text-xs text-slate-400">{document.document_type}</span>
                </button>
              )
            })}
          </div>
        </aside>

        <div className="min-w-0 p-6">
          {generateMutation.isPending ? (
            <p className="mb-4 rounded-md bg-slate-50 p-3 text-sm text-slate-500">
              Generating documents from prepared chunks...
            </p>
          ) : null}
          {documentQuery.isLoading ? (
            <p className="text-sm text-slate-500">Loading document...</p>
          ) : null}
          {documentQuery.isError ? (
            <p className="text-sm text-red-600">
              {axios.isAxiosError(documentQuery.error) && documentQuery.error.response?.status === 404
                ? '문서를 찾을 수 없습니다. 다시 Generate를 실행하세요.'
                : 'Failed to load selected document.'}
            </p>
          ) : null}
          {!selectedDocumentIdFromList && !documentsQuery.isLoading ? (
            <p className="text-sm text-slate-500">
              분석 데이터가 부족합니다. 먼저 repository scan과 Prepare Docs(chunk generation)를 실행하세요.
            </p>
          ) : null}
          {documentQuery.data ? (
            <div className="max-w-none space-y-4 text-sm leading-7 text-slate-700 [&_h1]:text-2xl [&_h1]:font-semibold [&_h1]:text-slate-950 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-slate-950 [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:text-slate-950 [&_li]:ml-5 [&_li]:list-disc">
              <ReactMarkdown components={markdownComponents}>{documentQuery.data.content}</ReactMarkdown>
            </div>
          ) : null}
        </div>
      </div>
    </article>
  )
}
