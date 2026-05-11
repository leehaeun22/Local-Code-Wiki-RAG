import type { ChatReference } from '../../types/chat'

interface ReferenceListProps {
  references: ChatReference[]
}

export function ReferenceList({ references }: ReferenceListProps) {
  const sortedReferences = [...references].sort((left, right) => {
    const leftScore = typeof left.score === 'number' ? left.score : -1
    const rightScore = typeof right.score === 'number' ? right.score : -1

    if (leftScore !== rightScore) {
      return rightScore - leftScore
    }

    return (left.file_path ?? '').localeCompare(right.file_path ?? '')
  })

  if (references.length === 0) {
    return (
      <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800">
        참고 근거가 없습니다.
      </div>
    )
  }

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-semibold text-slate-500">References</p>
      {sortedReferences.map((reference) => (
        <div
          className="rounded-md border border-slate-200 bg-white p-3 text-xs shadow-sm"
          key={`${reference.reference_type ?? 'unknown'}-${reference.file_path}-${reference.start_line}-${reference.end_line}-${reference.document_id ?? reference.chunk_id ?? ''}`}
        >
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={[
                'inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide',
                reference.reference_type === 'document'
                  ? 'bg-emerald-50 text-emerald-700'
                  : 'bg-sky-50 text-sky-700',
              ].join(' ')}
            >
              {reference.reference_type === 'document' ? 'document' : 'code chunk'}
            </span>
            {typeof reference.score === 'number' ? (
              <span className="text-[11px] font-medium text-slate-500">
                score {reference.score.toFixed(3)}
              </span>
            ) : null}
          </div>
          <p className="mt-2 break-all font-medium text-slate-800">
            {reference.file_path || 'Generated document'}
          </p>
          {reference.reference_type === 'document' ? (
            <p className="mt-1 text-slate-500">
              Document ID {reference.document_id ?? '?'}
            </p>
          ) : (
            <p className="mt-1 text-slate-500">
              Lines {reference.start_line ?? '?'}-{reference.end_line ?? '?'}
            </p>
          )}
          {reference.snippet ? (
            <details className="mt-2">
              <summary className="cursor-pointer text-slate-600">Snippet</summary>
              <p className="mt-2 max-h-28 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 font-mono leading-5 text-slate-600">
                {reference.snippet}
              </p>
            </details>
          ) : null}
          {reference.summary ? (
            <p className="mt-2 leading-5 text-slate-600">{reference.summary}</p>
          ) : null}
        </div>
      ))}
    </div>
  )
}
