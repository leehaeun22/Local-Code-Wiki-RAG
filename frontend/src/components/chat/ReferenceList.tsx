import type { ChatReference } from '../../types/chat'

interface ReferenceListProps {
  references: ChatReference[]
}

export function ReferenceList({ references }: ReferenceListProps) {
  if (references.length === 0) {
    return (
      <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800">
        참고 근거가 없습니다. 먼저 scan/chunk/document generation을 실행하세요.
      </div>
    )
  }

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-semibold text-slate-500">References</p>
      {references.map((reference) => (
        <div
          className="rounded-md border border-slate-200 bg-white p-3 text-xs"
          key={`${reference.file_path}-${reference.start_line}-${reference.end_line}-${reference.document_id ?? reference.chunk_id ?? ''}`}
        >
          <p className="break-all font-medium text-slate-800">
            {reference.file_path || 'Generated document'}
          </p>
          <p className="mt-1 text-slate-500">
            Lines {reference.start_line ?? '?'}-{reference.end_line ?? '?'}
            {typeof reference.score === 'number' ? ` | score ${reference.score.toFixed(3)}` : ''}
          </p>
          {reference.snippet ? (
            <p className="mt-2 max-h-24 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 font-mono leading-5 text-slate-600">
              {reference.snippet}
            </p>
          ) : null}
          {reference.summary ? (
            <p className="mt-2 leading-5 text-slate-600">{reference.summary}</p>
          ) : null}
        </div>
      ))}
    </div>
  )
}
