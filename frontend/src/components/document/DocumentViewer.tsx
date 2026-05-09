import { useEffect, useState } from 'react'
import axios from 'axios'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'

import { projectApi } from '../../api/projectApi'
import type { DocumentLanguage } from '../../types/document'

interface DocumentViewerProps {
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

export function DocumentViewer({ projectId }: DocumentViewerProps) {
  const queryClient = useQueryClient()
  const [language, setLanguage] = useState<DocumentLanguage>('ko')
  const [selectedDocumentId, setSelectedDocumentId] = useState('')
  const [actionError, setActionError] = useState('')

  const documentsQuery = useQuery({
    queryKey: ['project-documents', projectId],
    queryFn: () => projectApi.getDocuments(projectId),
  })
  const documents = documentsQuery.data ?? []
  const selectedDocumentIdFromList =
    selectedDocumentId || documents.find((document) => document.language === language)?.id || ''

  const documentQuery = useQuery({
    queryKey: ['project-document', projectId, selectedDocumentIdFromList],
    queryFn: () => projectApi.getDocument(projectId, selectedDocumentIdFromList),
    enabled: Boolean(selectedDocumentIdFromList),
  })

  const generateMutation = useMutation({
    mutationFn: () => projectApi.generateDocuments(projectId, { language }),
    onSuccess: (result) => {
      const firstDocument = result.documents[0]
      setSelectedDocumentId(firstDocument?.id ?? '')
      setActionError('')
      void queryClient.invalidateQueries({ queryKey: ['project-documents', projectId] })
    },
    onError: (error) => {
      setActionError(getErrorMessage(error))
    },
  })

  const prepareMutation = useMutation({
    mutationFn: () => projectApi.generateCodeChunks(projectId),
    onSuccess: async () => {
      setActionError('')
      await queryClient.invalidateQueries({ queryKey: ['project-documents', projectId] })
    },
    onError: (error) => {
      setActionError(getErrorMessage(error))
    },
  })

  const isWorking = generateMutation.isPending || prepareMutation.isPending

  useEffect(() => {
    if (!selectedDocumentId && selectedDocumentIdFromList) {
      setSelectedDocumentId(selectedDocumentIdFromList)
    }
  }, [selectedDocumentId, selectedDocumentIdFromList])

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
                }}
                value={language}
              >
                <option value="ko">ko</option>
                <option value="en">en</option>
              </select>
            </label>
            <button
              className="h-9 rounded-md border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
              disabled={isWorking}
              onClick={() => prepareMutation.mutate()}
              type="button"
            >
              {prepareMutation.isPending ? 'Preparing...' : 'Prepare Docs'}
            </button>
            <button
              className="h-9 rounded-md bg-slate-950 px-3 text-xs font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              disabled={isWorking}
              onClick={() => generateMutation.mutate()}
              type="button"
            >
              {generateMutation.isPending ? 'Generating...' : 'Generate'}
            </button>
          </div>
        </div>
        {actionError ? (
          <p className="mt-3 text-sm text-red-600">{actionError}</p>
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
          {!documentsQuery.isLoading && !documentsQuery.isError && documents.length === 0 ? (
            <p className="text-sm leading-6 text-slate-500">
              No documents yet. Generate markdown documentation from analyzed code.
            </p>
          ) : null}
          <div className="space-y-2">
            {documents
              .filter((document) => document.language === language)
              .map((document) => (
                <button
                  className={[
                    'w-full rounded-md px-3 py-2 text-left text-sm transition',
                    selectedDocumentIdFromList === document.id
                      ? 'bg-sky-50 font-medium text-sky-800'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-950',
                  ].join(' ')}
                  key={document.id}
                  onClick={() => setSelectedDocumentId(document.id)}
                  type="button"
                >
                  <span className="block">{document.title}</span>
                  <span className="mt-1 block text-xs text-slate-400">{document.document_type}</span>
                </button>
              ))}
          </div>
        </aside>

        <div className="min-w-0 p-6">
          {documentQuery.isLoading ? (
            <p className="text-sm text-slate-500">Loading document...</p>
          ) : null}
          {documentQuery.isError ? (
            <p className="text-sm text-red-600">Failed to load selected document.</p>
          ) : null}
          {!selectedDocumentIdFromList && !documentsQuery.isLoading ? (
            <p className="text-sm text-slate-500">Select or generate a document.</p>
          ) : null}
          {documentQuery.data ? (
            <div className="max-w-none space-y-4 text-sm leading-7 text-slate-700 [&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1 [&_code]:py-0.5 [&_h1]:text-2xl [&_h1]:font-semibold [&_h1]:text-slate-950 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-slate-950 [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:text-slate-950 [&_li]:ml-5 [&_li]:list-disc [&_pre]:overflow-auto [&_pre]:rounded-lg [&_pre]:bg-slate-950 [&_pre]:p-4 [&_pre]:text-slate-100">
              <ReactMarkdown>{documentQuery.data.content}</ReactMarkdown>
            </div>
          ) : null}
        </div>
      </div>
    </article>
  )
}
