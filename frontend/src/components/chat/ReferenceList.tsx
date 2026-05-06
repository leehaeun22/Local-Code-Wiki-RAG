import type { ChatReference } from '../../types/chat'

interface ReferenceListProps {
  references: ChatReference[]
}

export function ReferenceList({ references }: ReferenceListProps) {
  if (references.length === 0) {
    return null
  }

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-semibold text-slate-500">References</p>
      {references.map((reference) => (
        <div
          className="rounded-md border border-slate-200 bg-white p-3 text-xs"
          key={`${reference.file_path}-${reference.start_line}-${reference.end_line}`}
        >
          <p className="break-all font-medium text-slate-800">
            {reference.file_path || 'Unknown file'}
          </p>
          <p className="mt-1 text-slate-500">
            Lines {reference.start_line ?? '?'}-{reference.end_line ?? '?'}
            {typeof reference.score === 'number' ? ` · score ${reference.score.toFixed(3)}` : ''}
          </p>
          {reference.snippet ? (
            <p className="mt-2 max-h-24 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 font-mono leading-5 text-slate-600">
              {reference.snippet}
            </p>
          ) : null}
          <p className="mt-2 leading-5 text-slate-600">{reference.summary}</p>
        </div>
      ))}
    </div>
  )
}
