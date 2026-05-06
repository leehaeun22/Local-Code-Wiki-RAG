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
