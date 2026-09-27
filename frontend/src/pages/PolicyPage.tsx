import { useEffect, useState } from 'react'
import type {FormEvent} from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface PolicyPageProps {
  user: UserSummary | null
}

interface Policy {
  id: string
  title: string
  description?: string | null
  content?: string | null
  status?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export default function PolicyPage({ user }: PolicyPageProps) {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [content, setContent] = useState('')

  const canManage =
    user?.role === 'admin' || user?.role === 'hr'

  const loadPolicies = async () => {
    try {
      setLoading(true)
      setMessage('')

      const data = await apiFetch<Policy[]>('/policies')
      setPolicies(data)
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to load policies.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPolicies()
  }, [])

  const submitPolicy = async (event: FormEvent) => {
    event.preventDefault()

    try {
      await apiFetch('/policies', {
        method: 'POST',
        body: JSON.stringify({
          title,
          description: description || null,
          content,
        }),
      })

      setTitle('')
      setDescription('')
      setContent('')
      setMessage('Policy created successfully.')

      await loadPolicies()
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to create policy.',
      )
    }
  }

  return (
    <div className="page policies-page">
      <div className="page-header">
        <div>
          <div className="eyebrow">ORGANIZATION</div>
          <h1>Policies</h1>
          <p>
            View and manage organization policies and guidelines.
          </p>
        </div>

        <button
          className="secondary-btn"
          type="button"
          onClick={loadPolicies}
        >
          Refresh
        </button>
      </div>

      {message && <div className="error-box">{message}</div>}

      {canManage && (
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Create Policy</h2>
              <p>
                Publish a new policy for employees.
              </p>
            </div>
          </div>

          <form className="form-grid" onSubmit={submitPolicy}>
            <label>
              Policy title
              <input
                value={title}
                onChange={(event) =>
                  setTitle(event.target.value)
                }
                placeholder="e.g. Work From Home Policy"
                required
              />
            </label>

            <label>
              Short description
              <input
                value={description}
                onChange={(event) =>
                  setDescription(event.target.value)
                }
                placeholder="Briefly describe this policy"
              />
            </label>

            <label className="full">
              Policy content
              <textarea
                value={content}
                onChange={(event) =>
                  setContent(event.target.value)
                }
                placeholder="Enter the complete policy..."
                rows={8}
                required
              />
            </label>

            <div className="full">
              <button
                className="primary-btn"
                type="submit"
              >
                Publish Policy
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Company Policies</h2>
            <p>
              Policies currently available to employees.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">
            Loading policies...
          </div>
        ) : policies.length === 0 ? (
          <div className="empty-state">
            No policies have been published yet.
          </div>
        ) : (
          <div className="action-list">
            {policies.map((policy) => (
              <article className="action-row" key={policy.id}>
                <div>
                  <strong>{policy.title}</strong>

                  {policy.description && (
                    <p>{policy.description}</p>
                  )}

                  {policy.content && (
                    <div className="policy-content">
                      {policy.content}
                    </div>
                  )}
                </div>

                {policy.status && (
                  <span className="status-badge">
                    {policy.status}
                  </span>
                )}
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}