export interface ApiResponse<T> {
  success: boolean
  data: T
  message: string
}

export interface ProjectSetting {
  id: string
  default_language: DefaultLanguage
  llm_mode: LlmMode
  llm_provider_id: string
  embedding_provider_id: string
}

export interface Project {
  id: string
  owner_id: string
  name: string
  repository_url: string
  branch: string
  description: string | null
  settings: ProjectSetting | null
  created_at: string
  updated_at: string
}

export type DefaultLanguage = 'ko' | 'en'

export type LlmMode = 'cloud' | 'local'

export interface ProjectCreateRequest {
  name: string
  repository_url: string
  branch: string
  description?: string | null
  default_language: DefaultLanguage
  llm_mode: LlmMode
}

export type ProjectUpdateRequest = Partial<ProjectCreateRequest>
