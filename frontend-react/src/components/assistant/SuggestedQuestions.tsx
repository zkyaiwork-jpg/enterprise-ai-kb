type SuggestedQuestionsProps = {
  questions: string[]
  onSelect: (question: string) => void
}

export function SuggestedQuestions({ questions, onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {questions.map((question) => (
        <button key={question} type="button" onClick={() => onSelect(question)} className="rounded-full border border-[#dce3ef] bg-white px-3.5 py-2 text-xs font-medium text-on-surface-variant hover:border-primary/40 hover:bg-blue-50 hover:text-primary">
          {question}
        </button>
      ))}
    </div>
  )
}
