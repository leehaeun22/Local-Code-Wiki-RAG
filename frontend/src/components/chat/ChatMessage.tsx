import type { ChatMessage as ChatMessageType } from '../../types/chat'
import { ReferenceList } from './ReferenceList'

interface ChatMessageProps {
  message: ChatMessageType
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={['flex', isUser ? 'justify-end' : 'justify-start'].join(' ')}>
      <div
        className={[
          'max-w-full rounded-lg p-3',
          isUser ? 'bg-slate-950 text-white' : 'bg-slate-50 text-slate-700',
        ].join(' ')}
      >
        <p className={['text-xs font-semibold', isUser ? 'text-slate-300' : 'text-slate-500'].join(' ')}>
          {isUser ? 'You' : 'Assistant'}
        </p>
        <p className="mt-1 whitespace-pre-wrap text-sm leading-6">{message.content}</p>
        {!isUser && message.references ? <ReferenceList references={message.references} /> : null}
      </div>
    </div>
  )
}
