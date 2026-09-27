import { useEffect, useMemo, useState } from 'react'

import { apiFetch } from '../lib/api'
import type { UserSummary } from '../types'

interface DashboardProps {
  user: UserSummary | null
}

interface DashboardData {
  total_employees?: number
  present_today?: number
  on_leave_today?: number
  pending_leave?: number
  pending_expenses?: number
  attendance_rate?: number
  leave_balance?: number
  total_leave_allowance?: number
}

interface Holiday {
  id: string
  name: string
  date: string
  description?: string | null
  is_optional?: boolean
}

interface Announcement {
  id: string
  title: string
  content?: string | null
  created_at?: string | null
}

interface LeaveRecord {
  id: string
  status?: string | null
  start_date?: string | null
  end_date?: string | null
  leave_type?: string | null
}

interface ExpenseRecord {
  id: string
  status?: string | null
  amount?: number | null
  description?: string | null
}

interface DashboardResponse {
  summary?: DashboardData
  holidays?: Holiday[]
  announcements?: Announcement[]
  leave?: LeaveRecord[]
  expenses?: ExpenseRecord[]
}

function formatDate(value?: string | null) {
  if (!value) return '—'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function getInitials(user: UserSummary | null) {
  const first = user?.first_name?.[0] || ''
  const last = user?.last_name?.[0] || ''

  return `${first}${last}`.toUpperCase() || 'U'
}

function getGreeting() {
  const hour = new Date().getHours()

  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'

  return 'Good evening'
}

function getDays(start?: string | null, end?: string | null) {
  if (!start || !end) return 0

  const startDate = new Date(start)
  const endDate = new Date(end)

  if (
    Number.isNaN(startDate.getTime()) ||
    Number.isNaN(endDate.getTime())
  ) {
    return 0
  }

  return Math.max(
    1,
    Math.ceil(
      (endDate.getTime() - startDate.getTime()) /
        (1000 * 60 * 60 * 24),
    ) + 1,
  )
}

export default function Dashboard({
  user,
}: DashboardProps) {
  const [data, setData] = useState<DashboardResponse>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true

    const loadDashboard = async () => {
      setLoading(true)
      setError('')

      try {
        const [
          summaryResult,
          holidaysResult,
          announcementsResult,
          leaveResult,
          expensesResult,
        ] = await Promise.allSettled([
          apiFetch<DashboardData>('/dashboard/summary'),
          apiFetch<Holiday[]>('/holidays'),
          apiFetch<Announcement[]>('/announcements'),
          apiFetch<LeaveRecord[]>('/leave.applications'),
          apiFetch<ExpenseRecord[]>('/expenses/claim'),
        ])

        if (!mounted) return

        const nextData: DashboardResponse = {}

        if (summaryResult.status === 'fulfilled') {
          nextData.summary = summaryResult.value
        }

        if (holidaysResult.status === 'fulfilled') {
          nextData.holidays = holidaysResult.value
        }

        if (announcementsResult.status === 'fulfilled') {
          nextData.announcements =
            announcementsResult.value
        }

        if (leaveResult.status === 'fulfilled') {
          nextData.leave = leaveResult.value
        }

        if (expensesResult.status === 'fulfilled') {
          nextData.expenses = expensesResult.value
        }

        setData(nextData)

        if (
          summaryResult.status === 'rejected' &&
          holidaysResult.status === 'rejected' &&
          announcementsResult.status === 'rejected'
        ) {
          setError('Unable to load dashboard data.')
        }
      } catch {
        if (mounted) {
          setError('Unable to load dashboard data.')
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    void loadDashboard()

    return () => {
      mounted = false
    }
  }, [])

  const summary = data.summary || {}

  const upcomingHolidays = useMemo(() => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    return [...(data.holidays || [])]
      .filter((holiday) => {
        const date = new Date(holiday.date)

        return (
          !Number.isNaN(date.getTime()) &&
          date >= today
        )
      })
      .sort(
        (a, b) =>
          new Date(a.date).getTime() -
          new Date(b.date).getTime(),
      )
      .slice(0, 3)
  }, [data.holidays])

  const recentAnnouncements = useMemo(() => {
    return [...(data.announcements || [])]
      .sort(
        (a, b) =>
          new Date(b.created_at || '').getTime() -
          new Date(a.created_at || '').getTime(),
      )
      .slice(0, 3)
  }, [data.announcements])

  const pendingLeave = useMemo(() => {
    return (data.leave || [])
      .filter(
        (item) =>
          item.status?.toLowerCase() === 'pending',
      )
      .slice(0, 3)
  }, [data.leave])

  const pendingExpenses = useMemo(() => {
    return (data.expenses || [])
      .filter(
        (item) =>
          item.status?.toLowerCase() === 'pending',
      )
      .slice(0, 3)
  }, [data.expenses])

  const leaveBalance =
    summary.leave_balance ??
    0

  const leaveAllowance =
    summary.total_leave_allowance ??
    0

  const leavePercentage =
    leaveAllowance > 0
      ? Math.min(
          100,
          Math.round(
            (leaveBalance / leaveAllowance) * 100,
          ),
        )
      : 0

  const attendanceRate =
    summary.attendance_rate ??
    (summary.present_today !== undefined &&
    summary.total_employees
      ? Math.round(
          (summary.present_today /
            summary.total_employees) *
            100,
        )
      : 0)

  return (
    <div className="page dashboard-page">
      {/* Header */}
      <section className="dashboard-welcome">
        <div className="dashboard-welcome-content">
          <div className="dashboard-avatar">
            {getInitials(user)}
          </div>

          <div>
            <div className="eyebrow">
              {getGreeting()}
            </div>

            <h1>
              {user?.first_name || 'there'} 👋
            </h1>

            <p>
              Here&apos;s what&apos;s happening with
              your work today.
            </p>
          </div>
        </div>

        <div className="dashboard-date">
          {new Date().toLocaleDateString('en-IN', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
          })}
        </div>
      </section>

      {error && (
        <div className="error-box">
          {error}
        </div>
      )}

      {/* Quick overview */}
      <section className="dashboard-overview-grid">
        <div className="dashboard-overview-card attendance-card">
          <div className="overview-card-header">
            <div>
              <span className="overview-label">
                Today&apos;s attendance
              </span>

              <strong>
                {loading
                  ? '—'
                  : `${attendanceRate}%`}
              </strong>
            </div>

            <div className="overview-icon">
              ✓
            </div>
          </div>

          <div className="progress-track">
            <div
              className="progress-fill"
              style={{
                width: `${attendanceRate}%`,
              }}
            />
          </div>

          <div className="overview-footer">
            <span>
              {summary.present_today ?? 0} present
            </span>

            <span>
              {summary.on_leave_today ?? 0} on leave
            </span>
          </div>
        </div>

        <div className="dashboard-overview-card leave-card">
          <div className="overview-card-header">
            <div>
              <span className="overview-label">
                Leave balance
              </span>

              <strong>
                {loading
                  ? '—'
                  : `${leaveBalance} days`}
              </strong>
            </div>

            <div className="overview-icon">
              ◫
            </div>
          </div>

          <div className="progress-track">
            <div
              className="progress-fill"
              style={{
                width: `${leavePercentage}%`,
              }}
            />
          </div>

          <div className="overview-footer">
            <span>
              {leaveAllowance
                ? `${leaveAllowance} days allocated`
                : 'Available leave'}
            </span>

            <span>
              {summary.pending_leave ?? 0} pending
            </span>
          </div>
        </div>

        <div className="dashboard-overview-card employee-card">
          <div className="overview-card-header">
            <div>
              <span className="overview-label">
                Team
              </span>

              <strong>
                {loading
                  ? '—'
                  : summary.total_employees ?? 0}
              </strong>
            </div>

            <div className="overview-icon">
              ♙
            </div>
          </div>

          <div className="overview-description">
            Employees currently registered in the
            organisation.
          </div>

          <div className="overview-footer">
            <span>
              Active workforce
            </span>
          </div>
        </div>

        <div className="dashboard-overview-card action-card">
          <div className="overview-card-header">
            <div>
              <span className="overview-label">
                Pending actions
              </span>

              <strong>
                {(summary.pending_leave ?? 0) +
                  (summary.pending_expenses ?? 0)}
              </strong>
            </div>

            <div className="overview-icon">
              !
            </div>
          </div>

          <div className="overview-description">
            Items waiting for your attention.
          </div>

          <div className="overview-footer">
            <span>
              {summary.pending_leave ?? 0} leave
            </span>

            <span>
              {summary.pending_expenses ?? 0} expenses
            </span>
          </div>
        </div>
      </section>

      {/* Main dashboard */}
      <section className="dashboard-main-grid">
        {/* Attendance */}
        <div className="panel dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">
                Attendance
              </span>

              <h2>Your work week</h2>
            </div>

            <span className="status-badge success">
              {summary.present_today
                ? 'Checked in'
                : 'Attendance'}
            </span>
          </div>

          <div className="week-attendance">
            {[
              'Mon',
              'Tue',
              'Wed',
              'Thu',
              'Fri',
            ].map((day, index) => {
              const isPast =
                index <
                new Date().getDay() - 1

              return (
                <div
                  className="week-day"
                  key={day}
                >
                  <span>{day}</span>

                  <div
                    className={
                      isPast
                        ? 'day-status completed'
                        : 'day-status'
                    }
                  >
                    {isPast ? '✓' : '—'}
                  </div>
                </div>
              )
            })}
          </div>

          <div className="attendance-summary">
            <div>
              <strong>
                {summary.present_today ?? 0}
              </strong>

              <span>Present today</span>
            </div>

            <div>
              <strong>
                {summary.on_leave_today ?? 0}
              </strong>

              <span>On leave</span>
            </div>

            <div>
              <strong>
                {attendanceRate}%
              </strong>

              <span>Attendance rate</span>
            </div>
          </div>
        </div>

        {/* Upcoming holidays */}
        <div className="panel dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">
                Calendar
              </span>

              <h2>Upcoming holidays</h2>
            </div>

            <span className="panel-icon">
              □
            </span>
          </div>

          {upcomingHolidays.length === 0 ? (
            <div className="empty-state compact">
              No upcoming holidays available.
            </div>
          ) : (
            <div className="holiday-list">
              {upcomingHolidays.map(
                (holiday) => (
                  <div
                    className="holiday-item"
                    key={holiday.id}
                  >
                    <div className="holiday-date">
                      <strong>
                        {new Date(
                          holiday.date,
                        ).toLocaleDateString(
                          'en-IN',
                          {
                            day: '2-digit',
                          },
                        )}
                      </strong>

                      <span>
                        {new Date(
                          holiday.date,
                        ).toLocaleDateString(
                          'en-IN',
                          {
                            month: 'short',
                          },
                        )}
                      </span>
                    </div>

                    <div>
                      <strong>
                        {holiday.name}
                      </strong>

                      <span>
                        {holiday.is_optional
                          ? 'Optional holiday'
                          : 'Company holiday'}
                      </span>
                    </div>
                  </div>
                ),
              )}
            </div>
          )}
        </div>
      </section>

      {/* Actions + announcements */}
      <section className="dashboard-main-grid">
        <div className="panel dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">
                Approvals
              </span>

              <h2>Pending actions</h2>
            </div>
          </div>

          <div className="action-list">
            <div className="action-row">
              <div className="action-row-icon">
                ◫
              </div>

              <div>
                <strong>Leave requests</strong>

                <span>
                  {summary.pending_leave ?? 0}{' '}
                  requests awaiting review
                </span>
              </div>

              <span className="action-count">
                {summary.pending_leave ?? 0}
              </span>
            </div>

            <div className="action-row">
              <div className="action-row-icon">
                ₹
              </div>

              <div>
                <strong>Expense claims</strong>

                <span>
                  {summary.pending_expenses ?? 0}{' '}
                  claims awaiting review
                </span>
              </div>

              <span className="action-count">
                {summary.pending_expenses ?? 0}
              </span>
            </div>

            <div className="action-row">
              <div className="action-row-icon">
                ▱
              </div>

              <div>
                <strong>Documents</strong>

                <span>
                  Keep your employee documents
                  updated.
                </span>
              </div>

              <span className="action-arrow">
                →
              </span>
            </div>
          </div>
        </div>

        <div className="panel dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">
                Company
              </span>

              <h2>Announcements</h2>
            </div>

            <span className="panel-icon">
              ◉
            </span>
          </div>

          {recentAnnouncements.length === 0 ? (
            <div className="empty-state compact">
              No recent announcements.
            </div>
          ) : (
            <div className="announcement-list">
              {recentAnnouncements.map(
                (announcement) => (
                  <div
                    className="dashboard-announcement"
                    key={announcement.id}
                  >
                    <div className="announcement-dot" />

                    <div>
                      <strong>
                        {announcement.title}
                      </strong>

                      <span>
                        {formatDate(
                          announcement.created_at,
                        )}
                      </span>

                      {announcement.content && (
                        <p>
                          {announcement.content}
                        </p>
                      )}
                    </div>
                  </div>
                ),
              )}
            </div>
          )}
        </div>
      </section>

      {/* Recent requests */}
      <section className="dashboard-main-grid">
        <div className="panel dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">
                Leave
              </span>

              <h2>Recent leave requests</h2>
            </div>
          </div>

          {pendingLeave.length === 0 ? (
            <div className="empty-state compact">
              No pending leave requests.
            </div>
          ) : (
            <div className="mini-request-list">
              {pendingLeave.map((leave) => (
                <div
                  className="mini-request"
                  key={leave.id}
                >
                  <div>
                    <strong>
                      {leave.leave_type ||
                        'Leave request'}
                    </strong>

                    <span>
                      {formatDate(
                        leave.start_date,
                      )}{' '}
                      –{' '}
                      {formatDate(
                        leave.end_date,
                      )}
                    </span>
                  </div>

                  <div className="request-days">
                    {getDays(
                      leave.start_date,
                      leave.end_date,
                    )}{' '}
                    day(s)
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="panel dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">
                Expenses
              </span>

              <h2>Recent expense claims</h2>
            </div>
          </div>

          {pendingExpenses.length === 0 ? (
            <div className="empty-state compact">
              No pending expense claims.
            </div>
          ) : (
            <div className="mini-request-list">
              {pendingExpenses.map(
                (expense) => (
                  <div
                    className="mini-request"
                    key={expense.id}
                  >
                    <div>
                      <strong>
                        {expense.description ||
                          'Expense claim'}
                      </strong>

                      <span>
                        Pending review
                      </span>
                    </div>

                    <div className="request-amount">
                      ₹
                      {Number(
                        expense.amount || 0,
                      ).toLocaleString('en-IN')}
                    </div>
                  </div>
                ),
              )}
            </div>
          )}
        </div>
      </section>

      {/* Quick actions */}
      <section className="panel quick-actions-panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow">
              Shortcuts
            </span>

            <h2>Quick actions</h2>
          </div>
        </div>

        <div className="quick-actions-grid">
          <a
            href="/leave"
            className="quick-action"
          >
            <span className="quick-action-icon">
              ◫
            </span>

            <span>
              <strong>Apply for leave</strong>
              <small>
                Submit a new leave request
              </small>
            </span>

            <span>→</span>
          </a>

          <a
            href="/expenses"
            className="quick-action"
          >
            <span className="quick-action-icon">
              ₹
            </span>

            <span>
              <strong>Submit expense</strong>
              <small>
                Add a new expense claim
              </small>
            </span>

            <span>→</span>
          </a>

          <a
            href="/documents"
            className="quick-action"
          >
            <span className="quick-action-icon">
              ▱
            </span>

            <span>
              <strong>Upload document</strong>
              <small>
                Add or replace a document
              </small>
            </span>

            <span>→</span>
          </a>

          <a
            href="/payroll"
            className="quick-action"
          >
            <span className="quick-action-icon">
              ▤
            </span>

            <span>
              <strong>View salary slips</strong>
              <small>
                Check your payroll history
              </small>
            </span>

            <span>→</span>
          </a>
        </div>
      </section>
    </div>
  )
}
