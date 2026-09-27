import { useEffect, useMemo, useState } from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface PayrollPageProps {
  user: UserSummary | null
}

interface PayrollSummary {
  total_employees?: number
  total_payroll?: number
  pending_payroll?: number
  processed_payroll?: number
  current_month?: string
}

export default function PayrollPage({ user }: PayrollPageProps) {
  const [summary, setSummary] = useState<PayrollSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadPayroll()
  }, [])

  async function loadPayroll() {
    try {
      setLoading(true)
      setError('')

      const data = await apiFetch<PayrollSummary>('/payroll/summary')
      setSummary(data)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to load payroll information.',
      )
    } finally {
      setLoading(false)
    }
  }

  const totalEmployees = summary?.total_employees ?? 0
  const totalPayroll = summary?.total_payroll ?? 0
  const processedPayroll = summary?.processed_payroll ?? 0
  const pendingPayroll = summary?.pending_payroll ?? 0

  const processedPercentage = useMemo(() => {
    const total = processedPayroll + pendingPayroll

    if (!total) {
      return 0
    }

    return Math.round((processedPayroll / total) * 100)
  }, [processedPayroll, pendingPayroll])

  const pendingPercentage = useMemo(() => {
    const total = processedPayroll + pendingPayroll

    if (!total) {
      return 0
    }

    return Math.round((pendingPayroll / total) * 100)
  }, [processedPayroll, pendingPayroll])

  const cards = [
    {
      label: 'Total Employees',
      value: totalEmployees,
      icon: '♙',
      description: 'Employees included in payroll',
    },
    {
      label: 'Total Payroll',
      value: `₹${totalPayroll.toLocaleString()}`,
      icon: '₹',
      description: summary?.current_month
        ? `For ${summary.current_month}`
        : 'Current payroll period',
    },
    {
      label: 'Processed',
      value: processedPayroll,
      icon: '✓',
      description: `${processedPercentage}% of payroll processed`,
    },
    {
      label: 'Pending',
      value: pendingPayroll,
      icon: '◷',
      description: `${pendingPercentage}% of payroll pending`,
    },
  ]

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="eyebrow">FINANCE</div>
          <h1>Payroll</h1>
          <p>
            Monitor payroll processing, employee coverage, and current payroll
            status.
          </p>
        </div>

        <button
          className="secondary-btn"
          type="button"
          onClick={loadPayroll}
          disabled={loading}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {loading ? (
        <div className="panel">
          <div className="empty-state">Loading payroll...</div>
        </div>
      ) : (
        <>
          <div className="payroll-dashboard-container">
            <div className="payroll-dashboard-heading">
              <div>
                <div className="dashboard-label">PAYROLL OVERVIEW</div>
                <h2>
                  {summary?.current_month
                    ? `${summary.current_month} payroll`
                    : 'Current payroll'}
                </h2>
                <p>
                  Welcome back, {user?.first_name || 'there'}. Here is the
                  current payroll processing overview.
                </p>
              </div>
            </div>

            <div className="payroll-kpi-grid">
              {cards.map((card) => (
                <div className="payroll-kpi-card" key={card.label}>
                  <div className="payroll-kpi-top">
                    <span className="payroll-kpi-icon">{card.icon}</span>
                    <span>{card.label}</span>
                  </div>

                  <strong>{card.value}</strong>

                  <small>{card.description}</small>
                </div>
              ))}
            </div>

            <div className="payroll-dashboard-grid">
              <section className="payroll-dashboard-card">
                <div className="payroll-card-header">
                  <div>
                    <h3>Processing Status</h3>
                    <p>Current payroll processing breakdown.</p>
                  </div>
                </div>

                <div className="payroll-status-list">
                  <div className="payroll-status-row">
                    <div className="payroll-status-label">
                      <span className="payroll-status-dot processed" />
                      <span>Processed</span>
                    </div>

                    <div className="payroll-status-value">
                      <strong>{processedPayroll}</strong>
                      <small>{processedPercentage}%</small>
                    </div>
                  </div>

                  <div className="payroll-progress">
                    <div
                      className="payroll-progress-bar processed"
                      style={{
                        width: `${processedPercentage}%`,
                      }}
                    />
                  </div>

                  <div className="payroll-status-row">
                    <div className="payroll-status-label">
                      <span className="payroll-status-dot pending" />
                      <span>Pending</span>
                    </div>

                    <div className="payroll-status-value">
                      <strong>{pendingPayroll}</strong>
                      <small>{pendingPercentage}%</small>
                    </div>
                  </div>

                  <div className="payroll-progress">
                    <div
                      className="payroll-progress-bar pending"
                      style={{
                        width: `${pendingPercentage}%`,
                      }}
                    />
                  </div>
                </div>
              </section>

              <section className="payroll-dashboard-card">
                <div className="payroll-card-header">
                  <div>
                    <h3>Payroll Snapshot</h3>
                    <p>Key information for the current payroll period.</p>
                  </div>
                </div>

                <div className="payroll-snapshot-list">
                  <div className="payroll-snapshot-row">
                    <span>Payroll period</span>
                    <strong>
                      {summary?.current_month || 'Current period'}
                    </strong>
                  </div>

                  <div className="payroll-snapshot-row">
                    <span>Employees covered</span>
                    <strong>{totalEmployees}</strong>
                  </div>

                  <div className="payroll-snapshot-row">
                    <span>Total payroll</span>
                    <strong>
                      ₹{totalPayroll.toLocaleString()}
                    </strong>
                  </div>

                  <div className="payroll-snapshot-row">
                    <span>Processing status</span>
                    <strong>
                      {pendingPayroll === 0
                        ? 'Completed'
                        : 'In progress'}
                    </strong>
                  </div>
                </div>
              </section>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Payroll Summary</h2>
                <p>
                  {summary?.current_month
                    ? `Payroll information for ${summary.current_month}.`
                    : 'Current payroll information.'}
                </p>
              </div>
            </div>

            {!summary ? (
              <div className="empty-state">
                No payroll information is available.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>Value</th>
                    </tr>
                  </thead>

                  <tbody>
                    <tr>
                      <td>Total Employees</td>
                      <td>{totalEmployees}</td>
                    </tr>

                    <tr>
                      <td>Total Payroll</td>
                      <td>
                        ₹{totalPayroll.toLocaleString()}
                      </td>
                    </tr>

                    <tr>
                      <td>Processed Payroll</td>
                      <td>{processedPayroll}</td>
                    </tr>

                    <tr>
                      <td>Pending Payroll</td>
                      <td>{pendingPayroll}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}