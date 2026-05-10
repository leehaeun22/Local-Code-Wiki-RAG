export type DocumentLanguage = 'ko' | 'en'

export type DocumentType =
  | 'overview'
  | 'folder_structure'
  | 'api_documentation'
  | 'onboarding_guide'

export interface ProjectDocument {
  id: string
  document_id?: string
  project_id: string
  file_id: string | null
  generated_from_commit_id: string | null
  generated_from_commit_hash: string | null
  document_type: DocumentType
  title: string
  content: string
  language: DocumentLanguage
  created_at: string
  updated_at: string
}

export interface DocumentGenerateRequest {
  language: DocumentLanguage
  document_types?: DocumentType[]
}

export interface DocumentGenerationResult {
  project_id: string
  generated_document_count: number
  documents: ProjectDocument[]
}
