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
