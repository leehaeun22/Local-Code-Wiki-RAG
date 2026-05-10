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
  local_path: string | null
  last_commit_hash: string | null
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

export interface ProjectCloneResult {
  project_id: string
  local_path: string
  commit_hash: string
  task_id: string
}

export interface AnalysisStatus {
  project_id: string
  file_count: number
  chunk_count: number
  document_count: number
  has_files: boolean
  has_chunks: boolean
  has_documents: boolean
}
