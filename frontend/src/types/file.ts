export type FileTreeNodeType = 'directory' | 'file'

export interface FileTreeNode {
  id: string
  name: string
  path: string
  type: FileTreeNodeType
  children?: FileTreeNode[]
}
