import { type FormEvent, useState } from 'react'

interface ChatInputProps {
  onSubmit: (question: string) => void
  disabled?: boolean
}

export function ChatInput({ disabled = false, onSubmit }: ChatInputProps) {
  const [question, setQuestion] = useState('')

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const nextQuestion = question.trim()

    if (!nextQuestion || disabled) {
      return
    }

    onSubmit(nextQuestion)
    setQuestion('')
  }

  return (
    <form className="flex gap-2" onSubmit={handleSubmit}>
      <input
        className="h-10 min-w-0 flex-1 rounded-md border border-slate-300 px-3 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
        onChange={(event) => setQuestion(event.target.value)}
        placeholder="Ask about this repository"
        disabled={disabled}
        type="text"
        value={question}
      />
      <button
        className="h-10 rounded-md bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        disabled={disabled}
        type="submit"
      >
        {disabled ? 'Sending...' : 'Send'}
      </button>
    </form>
  )
}
