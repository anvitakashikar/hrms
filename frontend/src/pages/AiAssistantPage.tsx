import { FormEvent, useState } from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface AiAssistantPageProps {
  user: UserSummary | null
}

interface AssistantResponse {
  response?: string
  answer?: string
  message?: string
}

export default function AiAssistantPage({
  user,
}: AiAssistantPageProps) {
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const askAssistant = async (event: FormEvent) => {
    event.preventDefault()

    if (!question.trim()) {
      return
    }

    try {
      setLoading(true)
      setMessage('')
      setResponse('')

      const data = await apiFetch<AssistantResponse>(
        '/ai-assistant/chat',
        {
          method: 'POST',
          body: JSON.stringify({
            message: question.trim(),
          }),
        },
      )

      setResponse(
        data.response ||
          data.answer ||
          data.message ||
          'No response was returned.',
      )
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to contact the AI assistant.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="eyebrow">NIMBUS AI</div>
          <h1>AI Assistant</h1>
          <p>
            Ask questions about HR processes, policies and
            employee workflows.
          </p>
        </div>
      </div>

      {message && (
        <div className="error-box">
          {message}
        </div>
      )}

      <div className="panel ai-assistant-panel">
        <div className="panel-header">
          <div>
            <h2>How can I help?</h2>
            <p>
              Ask an HR-related question and the assistant will
              respond.
            </p>
          </div>
        </div>

        <form onSubmit={askAssistant}>
          <div className="ai-input-row">
            <textarea
              value={question}
              onChange={(event) =>
                setQuestion(event.target.value)
              }
              placeholder="For example: How do I apply for leave?"
              rows={4}
              disabled={loading}
            />

            <button
              className="primary-btn"
              type="submit"
              disabled={loading || !question.trim()}
            >
              {loading ? 'Thinking...' : 'Ask AI'}
            </button>
          </div>
        </form>

        {response && (
          <div className="ai-response">
            <div className="ai-response-header">
              <span className="pill">AI Assistant</span>
            </div>

            <div className="ai-response-content">
              {response}
            </div>
          </div>
        )}

        {!response && !loading && (
          <div className="empty-state">
            Your assistant response will appear here.
          </div>
        )}
      </div>
    </div>
  )
}