import {useEffect, useState } from 'react'
import type {FormEvent} from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface LifecyclePageProps {
  user: UserSummary | null
}

interface LifecycleRecord {
  id: string
  employee_id?: string | null
  employee_name?: string | null
  event_type?: string | null
  event_date?: string | null
  reason?: string | null
  notes?: string | null
  status?: string | null
}

export default function LifecyclePage({
  user,
}: LifecyclePageProps) {
  const [records, setRecords] = useState<LifecycleRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)

  const [employeeId, setEmployeeId] = useState('')
  const [eventType, setEventType] = useState('promotion')
  const [eventDate, setEventDate] = useState('')
  const [reason, setReason] = useState('')
  const [notes, setNotes] = useState('')

  const canManage =
    user?.role === 'admin' || user?.role === 'hr'

  const loadLifecycle = async () => {
    try {
      setLoading(true)
      setError('')

      const data = await apiFetch<LifecycleRecord[]>(
        '/lifecycle',
      )

      setRecords(data)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load lifecycle records.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLifecycle()
  }, [])

  const createRecord = async (event: FormEvent) => {
    event.preventDefault()

    try {
      await apiFetch('/lifecycle', {
        method: 'POST',
        body: JSON.stringify({
          employee_id: employeeId,
          event_type: eventType,
          event_date: eventDate,
          reason: reason || null,
          notes: notes || null,
        }),
      })

      setEmployeeId('')
      setEventType('promotion')
      setEventDate('')
      setReason('')
      setNotes('')
      setShowForm(false)

      await loadLifecycle()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to create lifecycle record.',
      )
    }
  }

  const getStatusClass = (status?: string | null) => {
    const value = status?.toLowerCase()

    if (value === 'completed' || value === 'active') {
      return 'success'
    }

    if (value === 'pending') {
      return 'warning'
    }

    if (value === 'cancelled' || value === 'rejected') {
      return 'danger'
    }

    return ''
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="eyebrow">HR MANAGEMENT</div>
          <h1>Employee Lifecycle</h1>
          <p>
            Track important employee lifecycle events from
            joining through separation.
          </p>
        </div>

        <div className="toolbar-actions">
          <button
            className="secondary-btn"
            type="button"
            onClick={loadLifecycle}
          >
            Refresh
          </button>

          {canManage && (
            <button
              className="primary-btn"
              type="button"
              onClick={() => setShowForm((current) => !current)}
            >
              {showForm ? 'Cancel' : 'Add Event'}
            </button>
          )}
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      {showForm && canManage && (
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Record Lifecycle Event</h2>
              <p>
                Add a promotion, transfer, resignation, or
                other employee lifecycle event.
              </p>
            </div>
          </div>

          <form
            className="form-grid"
            onSubmit={createRecord}
          >
            <label>
              Employee ID
              <input
                value={employeeId}
                onChange={(event) =>
                  setEmployeeId(event.target.value)
                }
                placeholder="Employee ID"
                required
              />
            </label>

            <label>
              Event type
              <select
                value={eventType}
                onChange={(event) =>
                  setEventType(event.target.value)
                }
              >
                <option value="joining">Joining</option>
                <option value="probation">Probation</option>
                <option value="confirmation">
                  Confirmation
                </option>
                <option value="promotion">Promotion</option>
                <option value="transfer">Transfer</option>
                <option value="role_change">
                  Role Change
                </option>
                <option value="salary_revision">
                  Salary Revision
                </option>
                <option value="resignation">
                  Resignation
                </option>
                <option value="termination">
                  Termination
                </option>
                <option value="retirement">
                  Retirement
                </option>
                <option value="exit">Exit</option>
              </select>
            </label>

            <label>
              Event date
              <input
                type="date"
                value={eventDate}
                onChange={(event) =>
                  setEventDate(event.target.value)
                }
                required
              />
            </label>

            <label>
              Reason
              <input
                value={reason}
                onChange={(event) =>
                  setReason(event.target.value)
                }
                placeholder="Reason"
              />
            </label>

            <label className="full">
              Notes
              <textarea
                rows={4}
                value={notes}
                onChange={(event) =>
                  setNotes(event.target.value)
                }
                placeholder="Additional notes..."
              />
            </label>

            <div className="full">
              <button
                className="primary-btn"
                type="submit"
              >
                Save Lifecycle Event
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-card">
          <span>Total Events</span>
          <strong>{records.length}</strong>
        </div>

        <div className="stat-card">
          <span>Promotions</span>
          <strong>
            {
              records.filter(
                (record) =>
                  record.event_type?.toLowerCase() ===
                  'promotion',
              ).length
            }
          </strong>
        </div>

        <div className="stat-card">
          <span>Transfers</span>
          <strong>
            {
              records.filter(
                (record) =>
                  record.event_type?.toLowerCase() ===
                  'transfer',
              ).length
            }
          </strong>
        </div>

        <div className="stat-card">
          <span>Exits</span>
          <strong>
            {
              records.filter((record) =>
                [
                  'exit',
                  'resignation',
                  'termination',
                  'retirement',
                ].includes(
                  record.event_type?.toLowerCase() || '',
                ),
              ).length
            }
          </strong>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Lifecycle History</h2>
            <p>
              Employee movements and lifecycle events.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">
            Loading lifecycle records...
          </div>
        ) : records.length === 0 ? (
          <div className="empty-state">
            No lifecycle events have been recorded yet.
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Event</th>
                  <th>Date</th>
                  <th>Reason</th>
                  <th>Notes</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {records.map((record) => (
                  <tr key={record.id}>
                    <td>
                      <strong>
                        {record.employee_name ||
                          record.employee_id ||
                          '—'}
                      </strong>
                    </td>

                    <td>
                      {record.event_type
                        ? record.event_type
                            .replace(/_/g, ' ')
                            .replace(/\b\w/g, (letter) =>
                              letter.toUpperCase(),
                            )
                        : '—'}
                    </td>

                    <td>{record.event_date || '—'}</td>

                    <td>{record.reason || '—'}</td>

                    <td>{record.notes || '—'}</td>

                    <td>
                      <span
                        className={`status-badge ${getStatusClass(
                          record.status,
                        )}`}
                      >
                        {record.status || 'Recorded'}
                      </span>
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