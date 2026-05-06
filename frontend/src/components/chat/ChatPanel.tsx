import { useState } from 'react'

import type { AnswerLanguage, ChatMessage as ChatMessageType, ChatReference } from '../../types/chat'
import { ChatInput } from './ChatInput'
import { ChatMessage } from './ChatMessage'

const mockReferences: ChatReference[] = [
  {
    file_path: 'frontend/src/pages/ProjectDetailPage.tsx',
    start_line: 32,
    end_line: 96,
    summary: 'Defines the project detail workspace that combines file tree, document viewer, and chat panel.',
  },
  {
    file_path: 'frontend/src/components/file/FileTree.tsx',
    start_line: 135,
    end_line: 186,
    summary: 'Manages expanded folders and selected file path for the mock repository tree.',
  },
]

const initialMessages: ChatMessageType[] = [
  {
    id: 'assistant-welcome',
    role: 'assistant',
    content:
      'Ask questions about the repository structure, onboarding flow, or generated documentation.',
    references: mockReferences.slice(0, 1),
  },
]

function createMockAnswer(question: string, language: AnswerLanguage): ChatMessageType {
  const content =
    language === 'ko'
      ? `"${question}"에 대한 mock RAG 답변입니다.\n현재 화면은 선택된 코드 문서와 파일 트리 맥락을 참고해 온보딩 질문에 답변하도록 설계되어 있습니다.`
      : `Mock RAG answer for "${question}".\nThis panel is designed to answer onboarding questions using the selected code document and file tree context.`

  return {
    id: `assistant-${Date.now()}`,
    role: 'assistant',
    content,
    references: mockReferences,
  }
}

export function ChatPanel() {
  const [language, setLanguage] = useState<AnswerLanguage>('ko')
  const [messages, setMessages] = useState<ChatMessageType[]>(initialMessages)

  const handleQuestionSubmit = (question: string) => {
    const userMessage: ChatMessageType = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
    }

    setMessages((current) => [...current, userMessage, createMockAnswer(question, language)])
  }

  return (
    <aside className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-950">RAG Chat</p>
            <p className="mt-1 text-xs text-slate-500">Mock assistant with source references</p>
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
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
        </div>
        <div className="border-t border-slate-100 p-4">
          <ChatInput onSubmit={handleQuestionSubmit} />
        </div>
      </div>
    </aside>
  )
}
