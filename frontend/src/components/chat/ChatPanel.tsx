import { useState } from 'react'
import axios from 'axios'
import { useMutation, useQuery } from '@tanstack/react-query'

import { projectApi } from '../../api/projectApi'
import type { AnswerLanguage, ChatMessage as ChatMessageType, ChatSession } from '../../types/chat'
import { ChatInput } from './ChatInput'
import { ChatMessage } from './ChatMessage'

const initialMessages: ChatMessageType[] = [
  {
    id: 'assistant-welcome',
    role: 'assistant',
    content: 'Ask questions about this repository. Answers will use generated RAG context.',
    references: [],
  },
]

interface ChatPanelProps {
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

  return 'Failed to get an answer.'
}

export function ChatPanel({ projectId }: ChatPanelProps) {
  const [language, setLanguage] = useState<AnswerLanguage>('ko')
  const [messages, setMessages] = useState<ChatMessageType[]>(initialMessages)
  const [session, setSession] = useState<ChatSession | null>(null)
  const [errorMessage, setErrorMessage] = useState('')
  const analysisStatusQuery = useQuery({
    queryKey: ['project-analysis-status', projectId],
    queryFn: () => projectApi.getAnalysisStatus(projectId),
  })
  const analysisStatus = analysisStatusQuery.data

  const chatMutation = useMutation({
    mutationFn: async (question: string) => {
      const nextSession =
        session ??
        (await projectApi.createChatSession(projectId, {
          title: question.slice(0, 80) || 'New chat',
        }))

      if (!session) {
        setSession(nextSession)
      }

      return projectApi.sendChatMessage(projectId, {
        question,
        session_id: nextSession.id,
        language,
        top_k: 5,
      })
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error))
    },
    onSuccess: (response) => {
      setSession(response.session)
      setMessages((current) => [...current, response.assistant_message])
      setErrorMessage('')
    },
  })

  const handleQuestionSubmit = (question: string) => {
    const userMessage: ChatMessageType = {
      id: `pending-user-${Date.now()}`,
      role: 'user',
      content: question,
      language,
    }

    setMessages((current) => [...current, userMessage])
    setErrorMessage('')
    chatMutation.mutate(question)
  }

  return (
    <aside className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-950">RAG Chat</p>
            <p className="mt-1 text-xs text-slate-500">Answers with source references</p>
          </div>
          <label className="text-xs font-medium text-slate-500">
            Answer
            <select
              className="mt-1 block h-8 rounded-md border border-slate-300 bg-white px-2 text-xs text-slate-700 outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
              onChange={(event) => setLanguage(event.target.value as AnswerLanguage)}
              value={language}
            >
              <option value="ko">ko</option>
              <option value="en">en</option>
            </select>
          </label>
        </div>
      </div>
      <div className="flex h-[calc(100%-81px)] min-h-[520px] flex-col">
        <div className="flex-1 space-y-3 overflow-auto p-4">
          {analysisStatus && !analysisStatus.has_chunks && !analysisStatus.has_documents ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              참고 근거가 없습니다. 먼저 scan/chunk/document generation을 실행하세요.
            </div>
          ) : null}
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          {chatMutation.isPending ? (
            <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-500">
              Generating answer...
            </div>
          ) : null}
          {errorMessage ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {errorMessage}
            </div>
          ) : null}
        </div>
        <div className="border-t border-slate-100 p-4">
          <ChatInput disabled={chatMutation.isPending} onSubmit={handleQuestionSubmit} />
        </div>
      </div>
    </aside>
  )
}
