import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface PerformancePageProps {
  user: UserSummary | null
}

interface PerformanceReview {
  id: string
  employee_id?: string | null
  employee_name?: string | null
  review_period?: string | null
  rating?: number | null
  status?: string | null
  comments?: string | null
}

export default function PerformancePage({
  user,
}: PerformancePageProps) {
  const [reviews, setReviews] = useState<PerformanceReview[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')

  const [employeeId, setEmployeeId] = useState('')
  const [period, setPeriod] = useState('')
  const [rating, setRating] = useState('')
  const [comments, setComments] = useState('')

  const canManage =
    user?.role === 'admin' ||
    user?.role === 'hr' ||
    user?.role === 'manager'

  const loadReviews = async () => {
    try {
      setLoading(true)
      setMessage('')

      const data = await apiFetch<PerformanceReview[]>(
        '/performance/reviews',
      )

      setReviews(data)
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to load performance reviews.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadReviews()
  }, [])

  const createReview = async (event: FormEvent) => {
    event.preventDefault()

    try {
      setMessage('')

      await apiFetch('/performance/reviews', {
        method: 'POST',
        body: JSON.stringify({
          employee_id: employeeId,
          review_period: period,
          rating: rating ? Number(rating) : null,
          comments: comments || null,
        }),
      })

      setEmployeeId('')
      setPeriod('')
      setRating('')
      setComments('')
      setMessage('Performance review created successfully.')

      await loadReviews()
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to create performance review.',
      )
    }
  }

  const totalReviews = reviews.length

  const completedReviews = useMemo(
    () =>
      reviews.filter(
        (review) =>
          review.status?.toLowerCase() === 'completed' ||
          review.status?.toLowerCase() === 'approved',
      ).length,
    [reviews],
  )

  const pendingReviews = useMemo(
    () =>
      reviews.filter((review) => {
        const status = review.status?.toLowerCase()

        return (
          !status ||
          status === 'draft' ||
          status === 'pending' ||
          status === 'in progress'
        )
      }).length,
    [reviews],
  )

  const ratedReviews = useMemo(
    () => reviews.filter((review) => review.rating != null),
    [reviews],
  )

  const averageRating = useMemo(() => {
    if (ratedReviews.length === 0) {
      return 0
    }

    const total = ratedReviews.reduce(
      (sum, review) => sum + (review.rating ?? 0),
      0,
    )

    return total / ratedReviews.length
  }, [ratedReviews])

  const recentReviews = useMemo(
    () => reviews.slice(0, 5),
    [reviews],
  )

  const statusCounts = useMemo(() => {
    const completed = completedReviews
    const pending = pendingReviews
    const other = Math.max(
      totalReviews - completed - pending,
      0,
    )

    return {
      completed,
      pending,
      other,
    }
  }, [completedReviews, pendingReviews, totalReviews])

  const completedPercentage = totalReviews
    ? Math.round((statusCounts.completed / totalReviews) * 100)
    : 0

  const pendingPercentage = totalReviews
    ? Math.round((statusCounts.pending / totalReviews) * 100)
    : 0

  const cards = [
    {
      label: 'Total Reviews',
      value: totalReviews,
      icon: '◎',
      description: 'Performance reviews recorded',
    },
    {
      label: 'Completed',
      value: completedReviews,
      icon: '✓',
      description: `${completedPercentage}% of all reviews`,
    },
    {
      label: 'Pending',
      value: pendingReviews,
      icon: '◷',
      description: `${pendingPercentage}% requiring attention`,
    },
    {
      label: 'Average Rating',
      value:
        ratedReviews.length > 0
          ? `${averageRating.toFixed(1)} / 5`
          : '—',
      icon: '★',
      description:
        ratedReviews.length > 0
          ? `Based on ${ratedReviews.length} rated reviews`
          : 'No ratings available',
    },
  ]

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="eyebrow">PEOPLE DEVELOPMENT</div>
          <h1>Performance</h1>
          <p>
            Track employee performance reviews, ratings, goals, and
            feedback.
          </p>
        </div>

        <button
          className="secondary-btn"
          type="button"
          onClick={loadReviews}
          disabled={loading}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {message && (
        <div
          className={
            message.toLowerCase().includes('success')
              ? 'success-box'
              : 'error-box'
          }
        >
          {message}
        </div>
      )}

      {loading ? (
        <div className="panel">
          <div className="empty-state">
            Loading performance information...
          </div>
        </div>
      ) : (
        <>
          <div className="performance-dashboard-container">
            <div className="performance-dashboard-heading">
              <div>
                <div className="dashboard-label">
                  PERFORMANCE OVERVIEW
                </div>

                <h2>
                  Employee performance
                </h2>

                <p>
                  Welcome back, {user?.first_name || 'there'}. Here is
                  the current performance review overview.
                </p>
              </div>
            </div>

            <div className="performance-kpi-grid">
              {cards.map((card) => (
                <div
                  className="performance-kpi-card"
                  key={card.label}
                >
                  <div className="performance-kpi-top">
                    <span className="performance-kpi-icon">
                      {card.icon}
                    </span>

                    <span>{card.label}</span>
                  </div>

                  <strong>{card.value}</strong>

                  <small>{card.description}</small>
                </div>
              ))}
            </div>

            <div className="performance-dashboard-grid">
              <section className="performance-dashboard-card">
                <div className="performance-card-header">
                  <div>
                    <h3>Review Status</h3>
                    <p>
                      Current distribution of performance reviews.
                    </p>
                  </div>
                </div>

                {totalReviews === 0 ? (
                  <div className="performance-dashboard-empty">
                    No performance reviews have been recorded yet.
                  </div>
                ) : (
                  <div className="performance-status-list">
                    <div className="performance-status-row">
                      <div className="performance-status-label">
                        <span className="performance-status-dot completed" />
                        <span>Completed</span>
                      </div>

                      <div className="performance-status-value">
                        <strong>
                          {statusCounts.completed}
                        </strong>
                        <small>
                          {completedPercentage}%
                        </small>
                      </div>
                    </div>

                    <div className="performance-progress">
                      <div
                        className="performance-progress-bar completed"
                        style={{
                          width: `${completedPercentage}%`,
                        }}
                      />
                    </div>

                    <div className="performance-status-row">
                      <div className="performance-status-label">
                        <span className="performance-status-dot pending" />
                        <span>Pending / Draft</span>
                      </div>

                      <div className="performance-status-value">
                        <strong>
                          {statusCounts.pending}
                        </strong>
                        <small>
                          {pendingPercentage}%
                        </small>
                      </div>
                    </div>

                    <div className="performance-progress">
                      <div
                        className="performance-progress-bar pending"
                        style={{
                          width: `${pendingPercentage}%`,
                        }}
                      />
                    </div>

                    {statusCounts.other > 0 && (
                      <div className="performance-status-row">
                        <div className="performance-status-label">
                          <span className="performance-status-dot other" />
                          <span>Other</span>
                        </div>

                        <div className="performance-status-value">
                          <strong>
                            {statusCounts.other}
                          </strong>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </section>

              <section className="performance-dashboard-card">
                <div className="performance-card-header">
                  <div>
                    <h3>Performance Snapshot</h3>
                    <p>
                      Key information from the review records.
                    </p>
                  </div>
                </div>

                <div className="performance-snapshot-list">
                  <div className="performance-snapshot-row">
                    <span>Total reviews</span>
                    <strong>{totalReviews}</strong>
                  </div>

                  <div className="performance-snapshot-row">
                    <span>Rated reviews</span>
                    <strong>{ratedReviews.length}</strong>
                  </div>

                  <div className="performance-snapshot-row">
                    <span>Average rating</span>
                    <strong>
                      {ratedReviews.length > 0
                        ? `${averageRating.toFixed(1)} / 5`
                        : '—'}
                    </strong>
                  </div>

                  <div className="performance-snapshot-row">
                    <span>Reviews requiring attention</span>
                    <strong>{pendingReviews}</strong>
                  </div>
                </div>
              </section>
            </div>

            <section className="performance-dashboard-card">
              <div className="performance-card-header">
                <div>
                  <h3>Recent Reviews</h3>
                  <p>
                    Latest performance reviews recorded in the system.
                  </p>
                </div>
              </div>

              {recentReviews.length === 0 ? (
                <div className="performance-dashboard-empty">
                  No recent reviews available.
                </div>
              ) : (
                <div className="performance-recent-list">
                  {recentReviews.map((review) => (
                    <div
                      className="performance-recent-row"
                      key={review.id}
                    >
                      <div className="performance-recent-main">
                        <strong>
                          {review.employee_name ||
                            review.employee_id ||
                            'Unknown employee'}
                        </strong>

                        <span>
                          {review.review_period || 'No review period'}
                        </span>
                      </div>

                      <div className="performance-recent-rating">
                        <strong>
                          {review.rating != null
                            ? `${review.rating}/5`
                            : 'Not rated'}
                        </strong>

                        <span>
                          {review.status || 'Draft'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>

          {canManage && (
            <div className="panel performance-form-panel">
              <div className="panel-header">
                <div>
                  <h2>Create Performance Review</h2>
                  <p>
                    Record a performance review and feedback for an
                    employee.
                  </p>
                </div>
              </div>

              <form
                className="workflow-form"
                onSubmit={createReview}
              >
                <div className="form-section">
                  <div className="form-section-heading">
                    <h3>Review Information</h3>
                    <p>
                      Enter the employee and review period details.
                    </p>
                  </div>

                  <div className="form-grid">
                    <div className="form-field">
                      <label htmlFor="performance-employee">
                        Employee ID
                      </label>

                      <input
                        id="performance-employee"
                        value={employeeId}
                        onChange={(event) =>
                          setEmployeeId(event.target.value)
                        }
                        placeholder="Enter employee ID"
                        required
                      />
                    </div>

                    <div className="form-field">
                      <label htmlFor="performance-period">
                        Review period
                      </label>

                      <input
                        id="performance-period"
                        value={period}
                        onChange={(event) =>
                          setPeriod(event.target.value)
                        }
                        placeholder="e.g. Q3 2026"
                        required
                      />
                    </div>

                    <div className="form-field">
                      <label htmlFor="performance-rating">
                        Rating
                      </label>

                      <input
                        id="performance-rating"
                        type="number"
                        min="1"
                        max="5"
                        step="0.5"
                        value={rating}
                        onChange={(event) =>
                          setRating(event.target.value)
                        }
                        placeholder="1 – 5"
                      />

                      <span className="form-hint">
                        Optional. Use a rating from 1 to 5.
                      </span>
                    </div>
                  </div>
                </div>

                <div className="form-section">
                  <div className="form-section-heading">
                    <h3>Feedback</h3>
                    <p>
                      Add comments or observations about the
                      employee's performance.
                    </p>
                  </div>

                  <div className="form-field">
                    <label htmlFor="performance-comments">
                      Comments
                    </label>

                    <textarea
                      id="performance-comments"
                      value={comments}
                      onChange={(event) =>
                        setComments(event.target.value)
                      }
                      rows={6}
                      placeholder="Write performance feedback..."
                    />
                  </div>
                </div>

                <div className="form-actions">
                  <button
                    className="primary-btn"
                    type="submit"
                  >
                    Create Review
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Performance Reviews</h2>
                <p>
                  Review history and employee feedback.
                </p>
              </div>
            </div>

            {reviews.length === 0 ? (
              <div className="empty-state">
                No performance reviews available.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Employee</th>
                      <th>Review Period</th>
                      <th>Rating</th>
                      <th>Comments</th>
                      <th>Status</th>
                    </tr>
                  </thead>

                  <tbody>
                    {reviews.map((review) => (
                      <tr key={review.id}>
                        <td>
                          {review.employee_name ||
                            review.employee_id ||
                            '—'}
                        </td>

                        <td>
                          {review.review_period || '—'}
                        </td>

                        <td>
                          {review.rating ?? '—'}
                        </td>

                        <td>
                          {review.comments || '—'}
                        </td>

                        <td>
                          <span className="status-badge">
                            {review.status || 'Draft'}
                          </span>
                        </td>
                      </tr>
                    ))}
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