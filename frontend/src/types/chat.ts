export type ChatRole = 'user' | 'assistant'

export type AnswerLanguage = 'ko' | 'en'

export interface ChatReference {
  id?: string
  file_id?: string | null
  chunk_id?: string | null
  document_id?: string | null
  file_path: string | null
  start_line: number | null
  end_line: number | null
  snippet?: string | null
  score?: number | null
  summary: string
}

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  language?: AnswerLanguage
  references?: ChatReference[]
}

export interface ChatSession {
  id: string
  project_id: string
  user_id: string | null
  title: string
  created_at: string
  updated_at: string
}

export interface ChatSessionCreateRequest {
  title: string
}

export interface RagChatRequest {
  question: string
  session_id?: string | null
  language: AnswerLanguage
  top_k?: number
}

export interface RagChatResponse {
  session: ChatSession
  user_message: ChatMessage
  assistant_message: ChatMessage
}
