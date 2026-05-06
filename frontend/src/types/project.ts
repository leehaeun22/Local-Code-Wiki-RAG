export type ProjectStatus = 'Ready' | 'Scanning' | 'Failed'

export interface Project {
  id: string
  name: string
  repositoryUrl: string
  description: string
  status: ProjectStatus
  documentCount: number
  updatedAt: string
}

export type DefaultLanguage = 'ko' | 'en'

export type LlmMode = 'cloud' | 'local'

export interface ProjectCreateRequest {
  projectName: string
  repositoryUrl: string
  branch: string
  defaultLanguage: DefaultLanguage
  llmMode: LlmMode
}
