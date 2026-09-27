import { useEffect, useMemo, useState } from 'react'

import { apiFetch } from '../lib/api'
import type { UserSummary } from '../types'

interface LeavePageProps {
  user: UserSummary | null
}

interface LeaveApplication {
  id: string
  leave_type?: string | null
  start_date?: string | null
  end_date?: string | null
  reason?: string | null
  status?: string | null
  calendar_days?: number | null
  chargeable_days?: number | null
}

export default function LeavePage({
  user,
}: LeavePageProps) {
  const [applications, setApplications] = useState<
    LeaveApplication[]
  >([])

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const [showForm, setShowForm] = useState(false)

  const [leaveType, setLeaveType] = useState('Annual')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [reason, setReason] = useState('')

  const loadApplications = async () => {
    setLoading(true)
    setError('')

    try {
      const data = await apiFetch<LeaveApplication[]>(
        '/leave/applications',
      )

      setApplications(data)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load leave applications',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadApplications()
  }, [])

  const pendingApplications = useMemo(
    () =>
      applications.filter(
        (application) =>
          application.status?.toLowerCase() ===
          'pending',
      ),
    [applications],
  )

  const approvedApplications = useMemo(
    () =>
      applications.filter(
        (application) =>
          application.status?.toLowerCase() ===
          'approved',
      ),
    [applications],
  )

  const rejectedApplications = useMemo(
    () =>
      applications.filter(
        (application) =>
          application.status?.toLowerCase() ===
          'rejected',
      ),
    [applications],
  )

  const totalLeaveDays = useMemo(
    () =>
      applications.reduce(
        (total, application) =>
          total +
          (application.chargeable_days ??
            application.calendar_days ??
            0),
        0,
      ),
    [applications],
  )

  const recentApplications = useMemo(
    () => applications.slice(0, 5),
    [applications],
  )

  const resetForm = () => {
    setLeaveType('Annual')
    setStartDate('')
    setEndDate('')
    setReason('')
  }

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault()

    if (
      !leaveType ||
      !startDate ||
      !endDate ||
      !reason.trim()
    ) {
      setError('Please fill in all required fields.')
      return
    }

    if (endDate < startDate) {
      setError(
        'End date must not be before start date.',
      )
      return
    }

    setSaving(true)
    setError('')

    try {
      await apiFetch<LeaveApplication>(
        '/leave/applications',
        {
          method: 'POST',
          body: JSON.stringify({
            leave_type: leaveType,
            start_date: startDate,
            end_date: endDate,
            reason: reason.trim(),
          }),
        },
      )

      resetForm()
      setShowForm(false)

      await loadApplications()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to submit leave request',
      )
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = async (id: string) => {
    setError('')

    try {
      await apiFetch(
        `/leave/applications/${id}/cancel`,
        {
          method: 'PATCH',
        },
      )

      await loadApplications()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to cancel leave request',
      )
    }
  }

  const calculateDays = (
    start?: string | null,
    end?: string | null,
  ) => {
    if (!start || !end) return 0

    const startValue = new Date(start)
    const endValue = new Date(end)

    return (
      Math.floor(
        (endValue.getTime() -
          startValue.getTime()) /
          (1000 * 60 * 60 * 24),
      ) + 1
    )
  }

  const getStatusClass = (
    status?: string | null,
  ) => {
    switch (status?.toLowerCase()) {
      case 'approved':
        return 'status-badge success'

      case 'rejected':
        return 'status-badge danger'

      case 'cancelled':
        return 'status-badge'

      default:
        return 'status-badge warning'
    }
  }

  return (
    <div className="page">
      {/* PAGE HEADER */}

      <div className="page-header">
        <div>
          <div className="eyebrow">
            My Workspace
          </div>

          <h1>Leave</h1>

          <p>
            Manage your leave requests and track
            their approval status.
          </p>
        </div>

        <button
          type="button"
          className="primary-btn"
          onClick={() => {
            setError('')
            setShowForm((value) => !value)
          }}
        >
          {showForm
            ? 'Close'
            : 'Apply for leave'}
        </button>
      </div>

      {error && (
        <div className="error-box">
          {error}
        </div>
      )}

      {/* =====================================================
          LEAVE DASHBOARD
          ===================================================== */}

      <section className="leave-dashboard-container">
        <div className="leave-dashboard-heading">
          <div>
            <span className="dashboard-label">
              LEAVE OVERVIEW
            </span>

            <h2>Your leave at a glance</h2>

            <p>
              Monitor your leave requests, approval
              status and requested leave days.
            </p>
          </div>

          <div className="dashboard-user">
            <span>Team member</span>

            <strong>
              {user?.first_name || 'Employee'}
            </strong>
          </div>
        </div>

        {/* KPI CARDS */}

        <div className="leave-kpi-grid">
          <div className="leave-kpi-card">
            <div className="leave-kpi-top">
              <span>Total requests</span>
              <span className="leave-kpi-icon">
                ▤
              </span>
            </div>

            <strong>
              {applications.length}
            </strong>

            <small>
              All submitted requests
            </small>
          </div>

          <div className="leave-kpi-card">
            <div className="leave-kpi-top">
              <span>Pending</span>
              <span className="leave-kpi-icon">
                ◷
              </span>
            </div>

            <strong>
              {pendingApplications.length}
            </strong>

            <small>
              Awaiting approval
            </small>
          </div>

          <div className="leave-kpi-card">
            <div className="leave-kpi-top">
              <span>Approved</span>
              <span className="leave-kpi-icon">
                ✓
              </span>
            </div>

            <strong>
              {approvedApplications.length}
            </strong>

            <small>
              Approved requests
            </small>
          </div>

          <div className="leave-kpi-card">
            <div className="leave-kpi-top">
              <span>Leave days</span>
              <span className="leave-kpi-icon">
                ◫
              </span>
            </div>

            <strong>
              {totalLeaveDays}
            </strong>

            <small>
              Total requested days
            </small>
          </div>
        </div>

        {/* LOWER DASHBOARD */}

        <div className="leave-dashboard-grid">
          {/* STATUS */}

          <div className="leave-dashboard-card">
            <div className="leave-card-header">
              <div>
                <h3>Leave status</h3>

                <p>
                  Current request breakdown
                </p>
              </div>
            </div>

            <div className="leave-status-list">
              <div className="leave-status-row">
                <span>
                  <i className="status-dot pending" />
                  Pending
                </span>

                <strong>
                  {pendingApplications.length}
                </strong>
              </div>

              <div className="leave-status-row">
                <span>
                  <i className="status-dot approved" />
                  Approved
                </span>

                <strong>
                  {approvedApplications.length}
                </strong>
              </div>

              <div className="leave-status-row">
                <span>
                  <i className="status-dot rejected" />
                  Rejected
                </span>

                <strong>
                  {rejectedApplications.length}
                </strong>
              </div>
            </div>
          </div>

          {/* RECENT REQUESTS */}

          <div className="leave-dashboard-card">
            <div className="leave-card-header">
              <div>
                <h3>Recent requests</h3>

                <p>
                  Your latest leave applications
                </p>
              </div>
            </div>

            {recentApplications.length === 0 ? (
              <div className="leave-dashboard-empty">
                No leave requests yet.
              </div>
            ) : (
              <div className="leave-recent-list">
                {recentApplications.map(
                  (application) => (
                    <div
                      className="leave-recent-row"
                      key={application.id}
                    >
                      <div>
                        <strong>
                          {application.leave_type ||
                            'Leave'}
                        </strong>

                        <span>
                          {application.start_date ||
                            '—'}
                          {' → '}
                          {application.end_date ||
                            '—'}
                        </span>
                      </div>

                      <span
                        className={getStatusClass(
                          application.status,
                        )}
                      >
                        {application.status ||
                          'pending'}
                      </span>
                    </div>
                  ),
                )}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* =====================================================
          APPLICATION FORM
          ===================================================== */}

      {showForm && (
        <div className="panel leave-form-panel">
          <div className="panel-header">
            <div>
              <h2>New leave request</h2>

              <p>
                Submit your leave request for
                approval.
              </p>
            </div>
          </div>

          <form
            className="workflow-form"
            onSubmit={handleSubmit}
          >
            <div className="form-grid">
              <div className="form-field">
                <label htmlFor="leave-type">
                  Leave type
                </label>

                <select
                  id="leave-type"
                  value={leaveType}
                  onChange={(event) =>
                    setLeaveType(
                      event.target.value,
                    )
                  }
                >
                  <option value="Annual">
                    Annual
                  </option>

                  <option value="Sick">
                    Sick
                  </option>

                  <option value="Casual">
                    Casual
                  </option>

                  <option value="Unpaid">
                    Unpaid
                  </option>
                </select>
              </div>

              <div className="form-field">
                <label htmlFor="leave-start">
                  Start date
                </label>

                <input
                  id="leave-start"
                  type="date"
                  value={startDate}
                  onChange={(event) =>
                    setStartDate(
                      event.target.value,
                    )
                  }
                  required
                />
              </div>

              <div className="form-field">
                <label htmlFor="leave-end">
                  End date
                </label>

                <input
                  id="leave-end"
                  type="date"
                  value={endDate}
                  onChange={(event) =>
                    setEndDate(
                      event.target.value,
                    )
                  }
                  required
                />
              </div>

              <div className="form-field full">
                <label htmlFor="leave-reason">
                  Reason
                </label>

                <textarea
                  id="leave-reason"
                  value={reason}
                  onChange={(event) =>
                    setReason(
                      event.target.value,
                    )
                  }
                  placeholder="Enter the reason for your leave"
                  required
                />
              </div>
            </div>

            <div className="row-actions">
              <button
                type="submit"
                className="primary-btn"
                disabled={saving}
              >
                {saving
                  ? 'Submitting...'
                  : 'Submit request'}
              </button>

              <button
                type="button"
                className="secondary-btn"
                disabled={saving}
                onClick={() => {
                  resetForm()
                  setShowForm(false)
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* =====================================================
          ALL LEAVE REQUESTS
          ===================================================== */}

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>My leave requests</h2>

            <p>
              {user?.first_name
                ? `Requests submitted by ${user.first_name}`
                : 'Your submitted leave requests'}
            </p>
          </div>

          <button
            type="button"
            className="secondary-btn"
            onClick={() =>
              void loadApplications()
            }
            disabled={loading}
          >
            {loading
              ? 'Refreshing...'
              : 'Refresh'}
          </button>
        </div>

        {loading ? (
          <div className="empty-state">
            Loading leave requests...
          </div>
        ) : applications.length === 0 ? (
          <div className="empty-state">
            <strong>
              No leave requests yet
            </strong>

            <p>
              You have not submitted any leave
              requests.
            </p>

            <button
              type="button"
              className="primary-btn"
              onClick={() => {
                setError('')
                setShowForm(true)
              }}
            >
              Apply for leave
            </button>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Leave type</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>Days</th>
                  <th>Reason</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {applications.map(
                  (application) => (
                    <tr
                      key={application.id}
                    >
                      <td>
                        {application.leave_type ||
                          '—'}
                      </td>

                      <td>
                        {application.start_date ||
                          '—'}
                      </td>

                      <td>
                        {application.end_date ||
                          '—'}
                      </td>

                      <td>
                        {application.chargeable_days ??
                          application.calendar_days ??
                          calculateDays(
                            application.start_date,
                            application.end_date,
                          )}
                      </td>

                      <td>
                        {application.reason ||
                          '—'}
                      </td>

                      <td>
                        <span
                          className={getStatusClass(
                            application.status,
                          )}
                        >
                          {application.status ||
                            'pending'}
                        </span>
                      </td>

                      <td>
                        {application.status?.toLowerCase() ===
                          'pending' ? (
                          <button
                            type="button"
                            className="text-btn"
                            onClick={() =>
                              void handleCancel(
                                application.id,
                              )
                            }
                          >
                            Cancel
                          </button>
                        ) : (
                          <span className="muted">
                            —
                          </span>
                        )}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}