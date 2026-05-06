import { useState } from 'react'

import type { FileTreeNode as FileTreeNodeType } from '../../types/file'

const mockFileTree: FileTreeNodeType[] = [
  {
    id: 'frontend',
    name: 'frontend',
    path: 'frontend',
    type: 'directory',
    children: [
      {
        id: 'frontend-src',
        name: 'src',
        path: 'frontend/src',
        type: 'directory',
        children: [
          {
            id: 'frontend-src-app',
            name: 'app',
            path: 'frontend/src/app',
            type: 'directory',
            children: [
              {
                id: 'frontend-src-app-app',
                name: 'App.tsx',
                path: 'frontend/src/app/App.tsx',
                type: 'file',
              },
              {
                id: 'frontend-src-app-router',
                name: 'router.tsx',
                path: 'frontend/src/app/router.tsx',
                type: 'file',
              },
            ],
          },
          {
            id: 'frontend-src-pages',
            name: 'pages',
            path: 'frontend/src/pages',
            type: 'directory',
            children: [
              {
                id: 'frontend-src-pages-list',
                name: 'ProjectListPage.tsx',
                path: 'frontend/src/pages/ProjectListPage.tsx',
                type: 'file',
              },
              {
                id: 'frontend-src-pages-detail',
                name: 'ProjectDetailPage.tsx',
                path: 'frontend/src/pages/ProjectDetailPage.tsx',
                type: 'file',
              },
            ],
          },
          {
            id: 'frontend-src-components',
            name: 'components',
            path: 'frontend/src/components',
            type: 'directory',
            children: [
              {
                id: 'frontend-src-components-layout',
                name: 'layout',
                path: 'frontend/src/components/layout',
                type: 'directory',
                children: [
                  {
                    id: 'frontend-src-components-layout-app',
                    name: 'AppLayout.tsx',
                    path: 'frontend/src/components/layout/AppLayout.tsx',
                    type: 'file',
                  },
                  {
                    id: 'frontend-src-components-layout-sidebar',
                    name: 'Sidebar.tsx',
                    path: 'frontend/src/components/layout/Sidebar.tsx',
                    type: 'file',
                  },
                ],
              },
            ],
          },
        ],
      },
      {
        id: 'frontend-package',
        name: 'package.json',
        path: 'frontend/package.json',
        type: 'file',
      },
    ],
  },
  {
    id: 'backend',
    name: 'backend',
    path: 'backend',
    type: 'directory',
    children: [
      {
        id: 'backend-app',
        name: 'app',
        path: 'backend/app',
        type: 'directory',
        children: [
          {
            id: 'backend-app-main',
            name: 'main.py',
            path: 'backend/app/main.py',
            type: 'file',
          },
        ],
      },
    ],
  },
  {
    id: 'docs',
    name: 'docs',
    path: 'docs',
    type: 'directory',
    children: [
      {
        id: 'docs-architecture',
        name: 'architecture.md',
        path: 'docs/architecture.md',
        type: 'file',
      },
    ],
  },
]

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
  onToggle: (nodeId: string) => void
  onSelectFile: (path: string) => void
}) {
  const isDirectory = node.type === 'directory'
  const isExpanded = expandedIds.has(node.id)
  const isSelected = selectedPath === node.path

  const handleClick = () => {
    if (isDirectory) {
      onToggle(node.id)
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

      {isDirectory && isExpanded && node.children ? (
        <div>
          {node.children.map((child) => (
            <FileTreeItem
              key={child.id}
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

export function FileTree() {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    () => new Set(['frontend', 'frontend-src', 'frontend-src-pages']),
  )
  const [selectedPath, setSelectedPath] = useState('frontend/src/pages/ProjectListPage.tsx')

  const toggleDirectory = (nodeId: string) => {
    setExpandedIds((current) => {
      const next = new Set(current)

      if (next.has(nodeId)) {
        next.delete(nodeId)
      } else {
        next.add(nodeId)
      }

      return next
    })
  }

  return (
    <aside className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 p-4">
        <p className="text-sm font-semibold text-slate-950">File Tree</p>
        <p className="mt-1 text-xs text-slate-500">Mock repository structure</p>
      </div>
      <div className="space-y-1 p-3">
        {mockFileTree.map((node) => (
          <FileTreeItem
            key={node.id}
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
        <p className="mt-1 break-all text-sm font-medium text-slate-800">{selectedPath}</p>
      </div>
    </aside>
  )
}
