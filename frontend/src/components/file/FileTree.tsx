import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { projectApi } from '../../api/projectApi'
import type { FileTreeNode as FileTreeNodeType } from '../../types/file'

function FileTreeItem({
  node,
  depth,
  expandedIds,
  selectedPath,
  onToggle,
  onSelectFile,
}: {
  node: FileTreeNodeType
  depth: number
  expandedIds: Set<string>
  selectedPath: string
  onToggle: (nodePath: string) => void
  onSelectFile: (path: string) => void
}) {
  const isDirectory = node.type === 'directory'
  const isExpanded = expandedIds.has(node.path)
  const isSelected = selectedPath === node.path

  const handleClick = () => {
    if (isDirectory) {
      onToggle(node.path)
      return
    }

    onSelectFile(node.path)
  }

  return (
    <div>
      <button
        className={[
          'flex h-8 w-full items-center gap-2 rounded-md pr-2 text-left text-sm transition',
          isSelected
            ? 'bg-sky-50 font-medium text-sky-800'
            : 'text-slate-600 hover:bg-slate-50 hover:text-slate-950',
        ].join(' ')}
        onClick={handleClick}
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
        type="button"
      >
        <span className="w-4 shrink-0 text-xs text-slate-400">
          {isDirectory ? (isExpanded ? 'v' : '>') : '-'}
        </span>
        <span className="truncate">{node.name}</span>
      </button>

      {isDirectory && isExpanded ? (
        <div>
          {node.children.map((child) => (
            <FileTreeItem
              key={child.path}
              depth={depth + 1}
              expandedIds={expandedIds}
              node={child}
              onSelectFile={onSelectFile}
              onToggle={onToggle}
              selectedPath={selectedPath}
            />
          ))}
        </div>
      ) : null}
    </div>
  )
}

interface FileTreeProps {
  projectId: string
}

export function FileTree({ projectId }: FileTreeProps) {
  const queryClient = useQueryClient()
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set())
  const [selectedPath, setSelectedPath] = useState('')

  const {
    data: fileTree = [],
    isError,
    isLoading,
  } = useQuery({
    queryKey: ['project-file-tree', projectId],
    queryFn: () => projectApi.getFileTree(projectId),
  })

  const scanMutation = useMutation({
    mutationFn: () => projectApi.scanProject(projectId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['project-file-tree', projectId] })
    },
  })

  const toggleDirectory = (nodePath: string) => {
    setExpandedIds((current) => {
      const next = new Set(current)

      if (next.has(nodePath)) {
        next.delete(nodePath)
      } else {
        next.add(nodePath)
      }

      return next
    })
  }

  return (
    <aside className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-950">File Tree</p>
            <p className="mt-1 text-xs text-slate-500">Repository scan result</p>
          </div>
          <button
            className="h-8 rounded-md bg-slate-950 px-3 text-xs font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            disabled={scanMutation.isPending}
            onClick={() => scanMutation.mutate()}
            type="button"
          >
            {scanMutation.isPending ? 'Scanning...' : 'Scan'}
          </button>
        </div>
        {scanMutation.isError ? (
          <p className="mt-3 text-xs leading-5 text-red-600">
            Scan failed. Clone the repository first and check the backend logs.
          </p>
        ) : null}
      </div>

      <div className="space-y-1 p-3">
        {isLoading ? <p className="px-2 py-3 text-sm text-slate-500">Loading file tree...</p> : null}
        {isError ? (
          <p className="px-2 py-3 text-sm leading-6 text-red-600">
            Failed to load file tree. Check that the backend API is running.
          </p>
        ) : null}
        {!isLoading && !isError && fileTree.length === 0 ? (
          <p className="px-2 py-3 text-sm leading-6 text-slate-500">
            No files scanned yet. Run scan after cloning the repository.
          </p>
        ) : null}
        {fileTree.map((node) => (
          <FileTreeItem
            key={node.path}
            depth={0}
            expandedIds={expandedIds}
            node={node}
            onSelectFile={setSelectedPath}
            onToggle={toggleDirectory}
            selectedPath={selectedPath}
          />
        ))}
      </div>

      <div className="border-t border-slate-100 p-4">
        <p className="text-xs font-medium text-slate-500">Selected file</p>
        <p className="mt-1 break-all text-sm font-medium text-slate-800">
          {selectedPath || 'Select a file from the tree.'}
        </p>
      </div>
    </aside>
  )
}
