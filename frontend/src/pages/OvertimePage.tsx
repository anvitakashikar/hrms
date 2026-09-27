import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface OvertimePageProps {
  user: UserSummary | null
}

interface OvertimeRecord {
  id: string
  employee_id?: string | null
  employee_name?: string | null
  work_date: string
  hours: number
  reason?: string | null
  status?: string | null
  approved_by?: string | null
}

export default function OvertimePage({
  user,
}: OvertimePageProps) {
  const [records, setRecords] = useState<OvertimeRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [workDate, setWorkDate] = useState('')
  const [hours, setHours] = useState('')
  const [reason, setReason] = useState('')

  const isReviewer =
    user?.role === 'admin' ||
    user?.role === 'hr' ||
    user?.role === 'manager'

  const loadOvertime = async () => {
    try {
      setLoading(true)
      setError('')

      const data = await apiFetch<OvertimeRecord[]>('/overtime')
      setRecords(data)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load overtime records.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadOvertime()
  }, [])

  const submitOvertime = async (event: FormEvent) => {
    event.preventDefault()

    try {
      setError('')
      setMessage('')

      await apiFetch('/overtime', {
        method: 'POST',
        body: JSON.stringify({
          work_date: workDate,
          hours: Number(hours),
          reason,
        }),
      })

      setWorkDate('')
      setHours('')
      setReason('')

      setMessage('Overtime request submitted successfully.')
      await loadOvertime()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to submit overtime request.',
      )
    }
  }

  const updateStatus = async (
    id: string,
    status: 'approved' | 'rejected',
  ) => {
    try {
      setError('')
      setMessage('')

      await apiFetch(`/overtime/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      })

      setMessage(
        status === 'approved'
          ? 'Overtime approved.'
          : 'Overtime rejected.',
      )

      await loadOvertime()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to update overtime request.',
      )
    }
  }

  const metrics = useMemo(() => {
    const pending = records.filter(
      (record) =>
        !record.status ||
        record.status.toLowerCase() === 'pending',
    )

    const approved = records.filter(
      (record) =>
        record.status?.toLowerCase() === 'approved',
    )

    const rejected = records.filter(
      (record) =>
        record.status?.toLowerCase() === 'rejected',
    )

    const totalHours = records.reduce(
      (total, record) =>
        total + (Number(record.hours) || 0),
      0,
    )

    const approvedHours = approved.reduce(
      (total, record) =>
        total + (Number(record.hours) || 0),
      0,
    )

    const pendingHours = pending.reduce(
      (total, record) =>
        total + (Number(record.hours) || 0),
      0,
    )

    return {
      totalRequests: records.length,
      totalHours,
      pendingCount: pending.length,
      approvedCount: approved.length,
      rejectedCount: rejected.length,
      approvedHours,
      pendingHours,
    }
  }, [records])

  const statusPercentage = (count: number) =>
    metrics.totalRequests > 0
      ? Math.round(
          (count / metrics.totalRequests) * 100,
        )
      : 0

  const recentRecords = records.slice(0, 5)

  return (
    <div className="page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <div className="eyebrow">TIME MANAGEMENT</div>
          <h1>Overtime</h1>
          <p>
            Track, submit, and review additional working
            hours across the organization.
          </p>
        </div>

        <button
          className="secondary-btn"
          type="button"
          onClick={loadOvertime}
        >
          Refresh
        </button>
      </div>

      {/* Alerts */}
      {error && <div className="error-box">{error}</div>}

      {message && (
        <div className="inline-message success">
          {message}
        </div>
      )}

      {/* Overview */}
      <section className="dashboard-section">
        <div className="section-heading">
          <div>
            <div className="eyebrow">OVERVIEW</div>
            <h2>Overtime overview</h2>
            <p>
              Monitor overtime requests and approval activity.
            </p>
          </div>

          <div className="section-user">
            <span>Signed in as</span>
            <strong>
              {user?.first_name} {user?.last_name}
            </strong>
          </div>
        </div>

        <div className="stat-grid">
          <div className="stat-card">
            <span>Total Requests</span>
            <strong>{metrics.totalRequests}</strong>
            <small>All overtime submissions</small>
          </div>

          <div className="stat-card">
            <span>Total Hours</span>
            <strong>
              {metrics.totalHours.toFixed(1)}
            </strong>
            <small>Across all requests</small>
          </div>

          <div className="stat-card">
            <span>Pending</span>
            <strong>{metrics.pendingCount}</strong>
            <small>
              {metrics.pendingHours.toFixed(1)} hours awaiting review
            </small>
          </div>

          <div className="stat-card">
            <span>Approved</span>
            <strong>{metrics.approvedCount}</strong>
            <small>
              {metrics.approvedHours.toFixed(1)} approved hours
            </small>
          </div>
        </div>
      </section>

      {/* Request Status */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">REQUEST STATUS</div>
            <h2>Approval status</h2>
            <p>
              Current distribution of overtime requests.
            </p>
          </div>
        </div>

        <div className="status-summary-list">
          <div className="status-summary-row">
            <div>
              <span>Pending</span>
              <strong>{metrics.pendingCount}</strong>
            </div>

            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: `${statusPercentage(
                    metrics.pendingCount,
                  )}%`,
                }}
              />
            </div>

            <small>
              {statusPercentage(metrics.pendingCount)}%
            </small>
          </div>

          <div className="status-summary-row">
            <div>
              <span>Approved</span>
              <strong>{metrics.approvedCount}</strong>
            </div>

            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: `${statusPercentage(
                    metrics.approvedCount,
                  )}%`,
                }}
              />
            </div>

            <small>
              {statusPercentage(metrics.approvedCount)}%
            </small>
          </div>

          <div className="status-summary-row">
            <div>
              <span>Rejected</span>
              <strong>{metrics.rejectedCount}</strong>
            </div>

            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: `${statusPercentage(
                    metrics.rejectedCount,
                  )}%`,
                }}
              />
            </div>

            <small>
              {statusPercentage(metrics.rejectedCount)}%
            </small>
          </div>
        </div>
      </section>

      {/* Recent Requests */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">RECENT ACTIVITY</div>
            <h2>Recent overtime requests</h2>
            <p>
              Latest overtime entries submitted by employees.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">
            Loading overtime records...
          </div>
        ) : recentRecords.length === 0 ? (
          <div className="empty-state">
            No recent overtime requests.
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Date</th>
                  <th>Hours</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {recentRecords.map((record) => (
                  <tr key={record.id}>
                    <td>
                      {record.employee_name ||
                        record.employee_id ||
                        '—'}
                    </td>

                    <td>{record.work_date}</td>

                    <td>
                      {Number(record.hours || 0).toFixed(1)}
                    </td>

                    <td>
                      <span className="status-badge">
                        {record.status || 'Pending'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Submit Overtime */}
      {!isReviewer && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <div className="eyebrow">REQUEST</div>
              <h2>Submit overtime</h2>
              <p>
                Record additional hours worked outside your
                regular schedule.
              </p>
            </div>
          </div>

          <form
            className="workflow-form"
            onSubmit={submitOvertime}
          >
            <div className="form-section">
              <div className="form-section-title">
                Overtime details
              </div>

              <div className="form-grid">
                <div className="form-field">
                  <label htmlFor="overtime-work-date">
                    Work date
                  </label>

                  <input
                    id="overtime-work-date"
                    type="date"
                    value={workDate}
                    onChange={(event) =>
                      setWorkDate(event.target.value)
                    }
                    required
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="overtime-hours">
                    Hours
                  </label>

                  <input
                    id="overtime-hours"
                    type="number"
                    min="0.5"
                    max="24"
                    step="0.5"
                    value={hours}
                    onChange={(event) =>
                      setHours(event.target.value)
                    }
                    placeholder="e.g. 2"
                    required
                  />
                </div>

                <div className="form-field full">
                  <label htmlFor="overtime-reason">
                    Reason
                  </label>

                  <textarea
                    id="overtime-reason"
                    value={reason}
                    onChange={(event) =>
                      setReason(event.target.value)
                    }
                    rows={4}
                    placeholder="Explain the reason for the overtime request"
                    required
                  />
                </div>
              </div>
            </div>

            <div className="form-actions">
              <button
                className="primary-btn"
                type="submit"
              >
                Submit Overtime
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Full Requests Table */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">REQUEST MANAGEMENT</div>
            <h2>Overtime requests</h2>
            <p>
              Review and manage submitted overtime entries.
            </p>
          </div>

          <span className="panel-count">
            {records.length} request
            {records.length === 1 ? '' : 's'}
          </span>
        </div>

        {loading ? (
          <div className="empty-state">
            Loading overtime records...
          </div>
        ) : records.length === 0 ? (
          <div className="empty-state">
            No overtime records available.
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Date</th>
                  <th>Hours</th>
                  <th>Reason</th>
                  <th>Status</th>
                  {isReviewer && <th>Actions</th>}
                </tr>
              </thead>

              <tbody>
                {records.map((record) => {
                  const isPending =
                    !record.status ||
                    record.status.toLowerCase() === 'pending'

                  return (
                    <tr key={record.id}>
                      <td>
                        {record.employee_name ||
                          record.employee_id ||
                          '—'}
                      </td>

                      <td>{record.work_date}</td>

                      <td>
                        {Number(record.hours || 0).toFixed(1)}
                      </td>

                      <td>{record.reason || '—'}</td>

                      <td>
                        <span className="status-badge">
                          {record.status || 'Pending'}
                        </span>
                      </td>

                      {isReviewer && (
                        <td>
                          {isPending && (
                            <div className="row-actions">
                              <button
                                className="text-btn"
                                type="button"
                                onClick={() =>
                                  updateStatus(
                                    record.id,
                                    'approved',
                                  )
                                }
                              >
                                Approve
                              </button>

                              <button
                                className="text-btn danger"
                                type="button"
                                onClick={() =>
                                  updateStatus(
                                    record.id,
                                    'rejected',
                                  )
                                }
                              >
                                Reject
                              </button>
                            </div>
                          )}
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}