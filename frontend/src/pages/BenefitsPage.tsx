import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface BenefitsPageProps {
  user: UserSummary | null
}

interface Benefit {
  id: string
  name: string
  description?: string | null
  provider?: string | null
  amount?: number | null
  status?: string | null
  effective_date?: string | null
}

export default function BenefitsPage({
  user,
}: BenefitsPageProps) {
  const [benefits, setBenefits] = useState<Benefit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [showForm, setShowForm] = useState(false)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [provider, setProvider] = useState('')
  const [amount, setAmount] = useState('')
  const [effectiveDate, setEffectiveDate] = useState('')

  const canManage =
    user?.role === 'admin' || user?.role === 'hr'

  const loadBenefits = async () => {
    try {
      setLoading(true)
      setError('')

      const data = await apiFetch<Benefit[]>('/benefits')
      setBenefits(data)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load benefits.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadBenefits()
  }, [])

  const createBenefit = async (event: FormEvent) => {
    event.preventDefault()

    try {
      setError('')
      setMessage('')

      await apiFetch('/benefits', {
        method: 'POST',
        body: JSON.stringify({
          name,
          description,
          provider: provider || null,
          amount: amount ? Number(amount) : null,
          effective_date: effectiveDate || null,
        }),
      })

      setName('')
      setDescription('')
      setProvider('')
      setAmount('')
      setEffectiveDate('')
      setShowForm(false)

      setMessage('Benefit program created successfully.')
      await loadBenefits()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to create benefit.',
      )
    }
  }

  const metrics = useMemo(() => {
    const active = benefits.filter(
      (benefit) =>
        !benefit.status ||
        benefit.status.toLowerCase() === 'active',
    )

    const inactive = benefits.filter(
      (benefit) =>
        benefit.status?.toLowerCase() === 'inactive',
    )

    const withProviders = benefits.filter(
      (benefit) => Boolean(benefit.provider),
    )

    const totalAmount = benefits.reduce(
      (total, benefit) =>
        total + (Number(benefit.amount) || 0),
      0,
    )

    return {
      total: benefits.length,
      active: active.length,
      inactive: inactive.length,
      withProviders: withProviders.length,
      totalAmount,
    }
  }, [benefits])

  const activePercentage =
    metrics.total > 0
      ? Math.round((metrics.active / metrics.total) * 100)
      : 0

  const inactivePercentage =
    metrics.total > 0
      ? Math.round((metrics.inactive / metrics.total) * 100)
      : 0

  const recentBenefits = benefits.slice(0, 5)

  return (
    <div className="page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <div className="eyebrow">HR MANAGEMENT</div>
          <h1>Benefits & Tax</h1>
          <p>
            Manage employee benefit programs, providers,
            and benefit information.
          </p>
        </div>

        <div className="toolbar-actions">
          <button
            className="secondary-btn"
            type="button"
            onClick={loadBenefits}
          >
            Refresh
          </button>

          {canManage && (
            <button
              className="primary-btn"
              type="button"
              onClick={() => {
                setShowForm((current) => !current)
                setError('')
                setMessage('')
              }}
            >
              {showForm ? 'Cancel' : 'Add Benefit'}
            </button>
          )}
        </div>
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
            <h2>Benefits overview</h2>
            <p>
              Monitor available benefit programs and their
              current status.
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
            <span>Total Benefits</span>
            <strong>{metrics.total}</strong>
            <small>Available benefit programs</small>
          </div>

          <div className="stat-card">
            <span>Active</span>
            <strong>{metrics.active}</strong>
            <small>
              {activePercentage}% of all programs
            </small>
          </div>

          <div className="stat-card">
            <span>Inactive</span>
            <strong>{metrics.inactive}</strong>
            <small>
              {inactivePercentage}% of all programs
            </small>
          </div>

          <div className="stat-card">
            <span>Providers</span>
            <strong>{metrics.withProviders}</strong>
            <small>
              Programs with provider information
            </small>
          </div>
        </div>
      </section>

      {/* Program Status */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">PROGRAM STATUS</div>
            <h2>Benefit status</h2>
            <p>
              Distribution of active and inactive programs.
            </p>
          </div>
        </div>

        <div className="status-summary-list">
          <div className="status-summary-row">
            <div>
              <span>Active</span>
              <strong>{metrics.active}</strong>
            </div>

            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: `${activePercentage}%`,
                }}
              />
            </div>

            <small>{activePercentage}%</small>
          </div>

          <div className="status-summary-row">
            <div>
              <span>Inactive</span>
              <strong>{metrics.inactive}</strong>
            </div>

            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: `${inactivePercentage}%`,
                }}
              />
            </div>

            <small>{inactivePercentage}%</small>
          </div>
        </div>
      </section>

      {/* Recent Benefits */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">RECENT ACTIVITY</div>
            <h2>Recent benefit programs</h2>
            <p>
              Recently listed employee benefit programs.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">
            Loading benefits...
          </div>
        ) : recentBenefits.length === 0 ? (
          <div className="empty-state">
            No benefit programs have been added yet.
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Benefit</th>
                  <th>Provider</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {recentBenefits.map((benefit) => (
                  <tr key={benefit.id}>
                    <td>
                      <strong>{benefit.name}</strong>
                    </td>

                    <td>
                      {benefit.provider || '—'}
                    </td>

                    <td>
                      {benefit.amount !== null &&
                      benefit.amount !== undefined
                        ? benefit.amount.toLocaleString()
                        : '—'}
                    </td>

                    <td>
                      <span className="status-badge">
                        {benefit.status || 'Active'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Add Benefit Form */}
      {showForm && canManage && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <div className="eyebrow">CONFIGURATION</div>
              <h2>Add benefit</h2>
              <p>
                Create a new benefit program for employees.
              </p>
            </div>
          </div>

          <form
            className="workflow-form"
            onSubmit={createBenefit}
          >
            <div className="form-section">
              <div className="form-section-title">
                Benefit details
              </div>

              <div className="form-grid">
                <div className="form-field">
                  <label htmlFor="benefit-name">
                    Benefit name
                  </label>

                  <input
                    id="benefit-name"
                    value={name}
                    onChange={(event) =>
                      setName(event.target.value)
                    }
                    placeholder="e.g. Health Insurance"
                    required
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="benefit-provider">
                    Provider
                  </label>

                  <input
                    id="benefit-provider"
                    value={provider}
                    onChange={(event) =>
                      setProvider(event.target.value)
                    }
                    placeholder="Provider name"
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="benefit-amount">
                    Amount
                  </label>

                  <input
                    id="benefit-amount"
                    type="number"
                    min="0"
                    step="0.01"
                    value={amount}
                    onChange={(event) =>
                      setAmount(event.target.value)
                    }
                    placeholder="0.00"
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="benefit-effective-date">
                    Effective date
                  </label>

                  <input
                    id="benefit-effective-date"
                    type="date"
                    value={effectiveDate}
                    onChange={(event) =>
                      setEffectiveDate(event.target.value)
                    }
                  />
                </div>

                <div className="form-field full">
                  <label htmlFor="benefit-description">
                    Description
                  </label>

                  <textarea
                    id="benefit-description"
                    rows={4}
                    value={description}
                    onChange={(event) =>
                      setDescription(event.target.value)
                    }
                    placeholder="Describe the benefit program..."
                  />
                </div>
              </div>
            </div>

            <div className="form-actions">
              <button
                className="secondary-btn"
                type="button"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </button>

              <button
                className="primary-btn"
                type="submit"
              >
                Create Benefit
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Full Benefits Table */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">BENEFIT MANAGEMENT</div>
            <h2>Benefit programs</h2>
            <p>
              View benefit programs, providers, amounts, and
              effective dates.
            </p>
          </div>

          <span className="panel-count">
            {benefits.length} program
            {benefits.length === 1 ? '' : 's'}
          </span>
        </div>

        {loading ? (
          <div className="empty-state">
            Loading benefits...
          </div>
        ) : benefits.length === 0 ? (
          <div className="empty-state">
            No benefit programs have been added yet.
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Benefit</th>
                  <th>Provider</th>
                  <th>Amount</th>
                  <th>Effective Date</th>
                  <th>Status</th>
                  <th>Description</th>
                </tr>
              </thead>

              <tbody>
                {benefits.map((benefit) => (
                  <tr key={benefit.id}>
                    <td>
                      <strong>{benefit.name}</strong>
                    </td>

                    <td>
                      {benefit.provider || '—'}
                    </td>

                    <td>
                      {benefit.amount !== null &&
                      benefit.amount !== undefined
                        ? benefit.amount.toLocaleString()
                        : '—'}
                    </td>

                    <td>
                      {benefit.effective_date || '—'}
                    </td>

                    <td>
                      <span className="status-badge">
                        {benefit.status || 'Active'}
                      </span>
                    </td>

                    <td>
                      {benefit.description || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}