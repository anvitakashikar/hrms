import {useEffect, useState } from 'react'
import type {FormEvent} from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface CompliancePageProps {
  user: UserSummary | null
}

interface ComplianceRecord {
  id: string
  title: string
  description?: string | null
  category?: string | null
  due_date?: string | null
  status?: string | null
  owner?: string | null
}

export default function CompliancePage({
  user,
}: CompliancePageProps) {
  const [records, setRecords] = useState<ComplianceRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)

  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [owner, setOwner] = useState('')

  const canManage =
    user?.role === 'admin' || user?.role === 'hr'

  const loadCompliance = async () => {
    try {
      setLoading(true)
      setError('')

      const data = await apiFetch<ComplianceRecord[]>(
        '/compliance',
      )

      setRecords(data)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load compliance records.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCompliance()
  }, [])

  const createRecord = async (event: FormEvent) => {
    event.preventDefault()

    try {
      await apiFetch('/compliance', {
        method: 'POST',
        body: JSON.stringify({
          title,
          category: category || null,
          description: description || null,
          due_date: dueDate || null,
          owner: owner || null,
        }),
      })

      setTitle('')
      setCategory('')
      setDescription('')
      setDueDate('')
      setOwner('')
      setShowForm(false)

      await loadCompliance()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to create compliance record.',
      )
    }
  }

  const getStatusClass = (status?: string | null) => {
    const value = status?.toLowerCase()

    if (
      value === 'compliant' ||
      value === 'completed' ||
      value === 'active'
    ) {
      return 'success'
    }

    if (
      value === 'pending' ||
      value === 'due'
    ) {
      return 'warning'
    }

    if (
      value === 'non_compliant' ||
      value === 'non-compliant' ||
      value === 'overdue' ||
      value === 'expired'
    ) {
      return 'danger'
    }

    return ''
  }

  const today = new Date()

  const overdueCount = records.filter((record) => {
    if (!record.due_date) return false

    const dueDateValue = new Date(record.due_date)

    return (
      dueDateValue < today &&
      !['completed', 'compliant'].includes(
        record.status?.toLowerCase() || '',
      )
    )
  }).length

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="eyebrow">ADMINISTRATION</div>
          <h1>Compliance</h1>
          <p>
            Track HR compliance requirements, deadlines, and
            responsibilities.
          </p>
        </div>

        <div className="toolbar-actions">
          <button
            className="secondary-btn"
            type="button"
            onClick={loadCompliance}
          >
            Refresh
          </button>

          {canManage && (
            <button
              className="primary-btn"
              type="button"
              onClick={() => setShowForm((current) => !current)}
            >
              {showForm ? 'Cancel' : 'Add Requirement'}
            </button>
          )}
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      {showForm && canManage && (
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Add Compliance Requirement</h2>
              <p>
                Record a compliance requirement or upcoming
                HR obligation.
              </p>
            </div>
          </div>

          <form
            className="form-grid"
            onSubmit={createRecord}
          >
            <label>
              Requirement
              <input
                value={title}
                onChange={(event) =>
                  setTitle(event.target.value)
                }
                placeholder="e.g. Annual compliance review"
                required
              />
            </label>

            <label>
              Category
              <input
                value={category}
                onChange={(event) =>
                  setCategory(event.target.value)
                }
                placeholder="e.g. Labour Law"
              />
            </label>

            <label>
              Due date
              <input
                type="date"
                value={dueDate}
                onChange={(event) =>
                  setDueDate(event.target.value)
                }
              />
            </label>

            <label>
              Owner
              <input
                value={owner}
                onChange={(event) =>
                  setOwner(event.target.value)
                }
                placeholder="Responsible person"
              />
            </label>

            <label className="full">
              Description
              <textarea
                rows={4}
                value={description}
                onChange={(event) =>
                  setDescription(event.target.value)
                }
                placeholder="Describe the requirement..."
              />
            </label>

            <div className="full">
              <button
                className="primary-btn"
                type="submit"
              >
                Save Requirement
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-card">
          <span>Total Requirements</span>
          <strong>{records.length}</strong>
        </div>

        <div className="stat-card">
          <span>Compliant</span>
          <strong>
            {
              records.filter((record) =>
                ['compliant', 'completed'].includes(
                  record.status?.toLowerCase() || '',
                ),
              ).length
            }
          </strong>
        </div>

        <div className="stat-card">
          <span>Pending</span>
          <strong>
            {
              records.filter((record) =>
                ['pending', 'due'].includes(
                  record.status?.toLowerCase() || '',
                ),
              ).length
            }
          </strong>
        </div>

        <div className="stat-card">
          <span>Overdue</span>
          <strong>{overdueCount}</strong>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Compliance Requirements</h2>
            <p>
              Current compliance obligations and their status.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">
            Loading compliance records...
          </div>
        ) : records.length === 0 ? (
          <div className="empty-state">
            No compliance requirements have been recorded.
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Requirement</th>
                  <th>Category</th>
                  <th>Due Date</th>
                  <th>Owner</th>
                  <th>Status</th>
                  <th>Description</th>
                </tr>
              </thead>

              <tbody>
                {records.map((record) => (
                  <tr key={record.id}>
                    <td>
                      <strong>{record.title}</strong>
                    </td>

                    <td>{record.category || '—'}</td>

                    <td>{record.due_date || '—'}</td>

                    <td>{record.owner || '—'}</td>

                    <td>
                      <span
                        className={`status-badge ${getStatusClass(
                          record.status,
                        )}`}
                      >
                        {record.status || 'Pending'}
                      </span>
                    </td>

                    <td>
                      {record.description || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}