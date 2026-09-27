import { useEffect, useState } from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface AnalyticsPageProps {
  user: UserSummary | null
}

interface AnalyticsSummary {
  total_employees?: number
  active_employees?: number
  employees_on_leave?: number
  attendance_rate?: number
  leave_rate?: number
  pending_leave?: number
  pending_expenses?: number
  total_payroll?: number
}

interface DepartmentMetric {
  department?: string | null
  count?: number
  employees?: number
}

interface AttendanceMetric {
  date?: string
  present?: number
  absent?: number
  late?: number
}

export default function AnalyticsPage({
  user,
}: AnalyticsPageProps) {
  const [summary, setSummary] =
    useState<AnalyticsSummary | null>(null)

  const [departments, setDepartments] = useState<
    DepartmentMetric[]
  >([])

  const [attendance, setAttendance] = useState<
    AttendanceMetric[]
  >([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadAnalytics = async () => {
    try {
      setLoading(true)
      setError('')

      const [summaryResult, departmentResult, attendanceResult] =
        await Promise.allSettled([
          apiFetch<AnalyticsSummary>('/analytics/summary'),
          apiFetch<DepartmentMetric[]>(
            '/analytics/departments',
          ),
          apiFetch<AttendanceMetric[]>(
            '/analytics/attendance',
          ),
        ])

      if (summaryResult.status === 'fulfilled') {
        setSummary(summaryResult.value)
      }

      if (departmentResult.status === 'fulfilled') {
        setDepartments(departmentResult.value)
      }

      if (attendanceResult.status === 'fulfilled') {
        setAttendance(attendanceResult.value)
      }

      if (
        summaryResult.status === 'rejected' &&
        departmentResult.status === 'rejected' &&
        attendanceResult.status === 'rejected'
      ) {
        throw summaryResult.reason
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load analytics.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAnalytics()
  }, [])

  const formatNumber = (value?: number) =>
    typeof value === 'number'
      ? value.toLocaleString()
      : '—'

  const formatPercentage = (value?: number) =>
    typeof value === 'number'
      ? `${value.toFixed(1)}%`
      : '—'

  const maxDepartmentCount = Math.max(
    1,
    ...departments.map(
      (department) =>
        department.count ??
        department.employees ??
        0,
    ),
  )

  const maxAttendanceValue = Math.max(
    1,
    ...attendance.flatMap((item) => [
      item.present ?? 0,
      item.absent ?? 0,
      item.late ?? 0,
    ]),
  )

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="eyebrow">ADMINISTRATION</div>
          <h1>Analytics</h1>
          <p>
            Overview of workforce, attendance, leave, and
            payroll metrics.
          </p>
        </div>

        <button
          className="secondary-btn"
          type="button"
          onClick={loadAnalytics}
        >
          Refresh
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {loading ? (
        <div className="panel">
          <div className="empty-state">
            Loading analytics...
          </div>
        </div>
      ) : (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <span>Total Employees</span>
              <strong>
                {formatNumber(summary?.total_employees)}
              </strong>
            </div>

            <div className="stat-card">
              <span>Active Employees</span>
              <strong>
                {formatNumber(summary?.active_employees)}
              </strong>
            </div>

            <div className="stat-card">
              <span>Attendance Rate</span>
              <strong>
                {formatPercentage(
                  summary?.attendance_rate,
                )}
              </strong>
            </div>

            <div className="stat-card">
              <span>Employees on Leave</span>
              <strong>
                {formatNumber(summary?.employees_on_leave)}
              </strong>
            </div>

            <div className="stat-card">
              <span>Pending Leave</span>
              <strong>
                {formatNumber(summary?.pending_leave)}
              </strong>
            </div>

            <div className="stat-card">
              <span>Pending Expenses</span>
              <strong>
                {formatNumber(summary?.pending_expenses)}
              </strong>
            </div>

            <div className="stat-card">
              <span>Leave Rate</span>
              <strong>
                {formatPercentage(summary?.leave_rate)}
              </strong>
            </div>

            <div className="stat-card">
              <span>Total Payroll</span>
              <strong>
                {typeof summary?.total_payroll === 'number'
                  ? summary.total_payroll.toLocaleString()
                  : '—'}
              </strong>
            </div>
          </div>

          <div className="dashboard-grid">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>Employees by Department</h2>
                  <p>
                    Workforce distribution across departments.
                  </p>
                </div>
              </div>

              {departments.length === 0 ? (
                <div className="empty-state">
                  No department analytics available.
                </div>
              ) : (
                <div className="action-list">
                  {departments.map((department, index) => {
                    const count =
                      department.count ??
                      department.employees ??
                      0

                    const percentage =
                      (count / maxDepartmentCount) * 100

                    return (
                      <div
                        className="action-row"
                        key={`${department.department}-${index}`}
                      >
                        <div style={{ flex: 1 }}>
                          <strong>
                            {department.department ||
                              'Unassigned'}
                          </strong>

                          <div
                            style={{
                              height: 8,
                              borderRadius: 999,
                              background:
                                'var(--surface-muted, #edf0f3)',
                              marginTop: 8,
                              overflow: 'hidden',
                            }}
                          >
                            <div
                              style={{
                                width: `${percentage}%`,
                                height: '100%',
                                borderRadius: 999,
                                background:
                                  'var(--accent, #111827)',
                              }}
                            />
                          </div>
                        </div>

                        <strong>{count}</strong>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>Attendance Trend</h2>
                  <p>
                    Recent attendance metrics.
                  </p>
                </div>
              </div>

              {attendance.length === 0 ? (
                <div className="empty-state">
                  No attendance analytics available.
                </div>
              ) : (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Present</th>
                        <th>Absent</th>
                        <th>Late</th>
                      </tr>
                    </thead>

                    <tbody>
                      {attendance.map((item, index) => (
                        <tr
                          key={`${item.date}-${index}`}
                        >
                          <td>{item.date || '—'}</td>
                          <td>{item.present ?? 0}</td>
                          <td>{item.absent ?? 0}</td>
                          <td>{item.late ?? 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {attendance.length > 0 && (
            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>Attendance Overview</h2>
                  <p>
                    Relative attendance values for the available
                    dates.
                  </p>
                </div>
              </div>

              <div className="action-list">
                {attendance.map((item, index) => (
                  <div
                    className="action-row"
                    key={`attendance-${item.date}-${index}`}
                  >
                    <div style={{ minWidth: 100 }}>
                      <strong>
                        {item.date || 'Unknown date'}
                      </strong>
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        gap: 8,
                        alignItems: 'center',
                        flex: 1,
                      }}
                    >
                      <div
                        style={{
                          width: `${
                            ((item.present ?? 0) /
                              maxAttendanceValue) *
                            100
                          }%`,
                          minWidth:
                            item.present ? 8 : 0,
                          height: 10,
                          borderRadius: 999,
                          background:
                            'var(--accent, #111827)',
                        }}
                        title={`Present: ${
                          item.present ?? 0
                        }`}
                      />

                      <span className="muted">
                        Present {item.present ?? 0}
                      </span>

                      <span className="muted">
                        Absent {item.absent ?? 0}
                      </span>

                      <span className="muted">
                        Late {item.late ?? 0}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Analytics Access</h2>
                <p>
                  Current account context for this dashboard.
                </p>
              </div>
            </div>

            <div className="action-row">
              <div>
                <strong>{user?.email || '—'}</strong>
                <div className="muted">
                  Role: {user?.role || '—'}
                </div>
              </div>

              <span className="status-badge">
                Analytics
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  )
}