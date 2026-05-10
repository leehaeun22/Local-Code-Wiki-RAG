export type FileTreeNodeType = 'directory' | 'file'

export interface FileTreeNode {
  name: string
  path: string
  type: FileTreeNodeType
  children: FileTreeNode[]
}

export interface RepositoryScanResult {
  project_id: string
  scanned_file_count: number
  task_id: string
}

export interface CodeChunkGenerationResult {
  project_id: string
  generated_chunk_count: number
  task_id: string
}

export interface CodeChunk {
  id: string
  project_id: string
  file_id: string
  chunk_index: number
  chunk_type: string
  start_line: number
  end_line: number
  content: string
  content_hash: string
  created_at: string
  updated_at: string
}
