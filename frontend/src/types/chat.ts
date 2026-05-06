export type ChatRole = 'user' | 'assistant'

export type AnswerLanguage = 'ko' | 'en'

export interface ChatReference {
  file_path: string
  start_line: number
  end_line: number
  summary: string
}

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  references?: ChatReference[]
}
