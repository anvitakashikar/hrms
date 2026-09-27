import { useEffect, useMemo, useState } from 'react'

import { apiFetch } from '../lib/api'
import type { UserSummary } from '../types'

interface ExpensesPageProps {
  user: UserSummary | null
}

interface ExpenseClaim {
  id: string
  category?: string | null
  amount?: number | null
  currency?: string | null
  description?: string | null
  expense_date?: string | null
  status?: string | null
}

export default function ExpensesPage({
  user,
}: ExpensesPageProps) {
  const [expenses, setExpenses] = useState<ExpenseClaim[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const [showForm, setShowForm] = useState(false)

  const [category, setCategory] = useState('Travel')
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState('INR')
  const [description, setDescription] = useState('')
  const [expenseDate, setExpenseDate] = useState('')

  const loadExpenses = async () => {
    setLoading(true)
    setError('')

    try {
      const data = await apiFetch<ExpenseClaim[]>(
        '/expenses/claims',
      )

      setExpenses(data)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load expenses',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadExpenses()
  }, [])

  const pendingExpenses = useMemo(
    () =>
      expenses.filter(
        (expense) =>
          expense.status?.toLowerCase() === 'pending' ||
          expense.status?.toLowerCase() === 'submitted',
      ),
    [expenses],
  )

  const approvedExpenses = useMemo(
    () =>
      expenses.filter(
        (expense) =>
          expense.status?.toLowerCase() === 'approved',
      ),
    [expenses],
  )

  const rejectedExpenses = useMemo(
    () =>
      expenses.filter(
        (expense) =>
          expense.status?.toLowerCase() === 'rejected',
      ),
    [expenses],
  )

  const totalAmount = useMemo(
    () =>
      expenses.reduce(
        (total, expense) =>
          total + (expense.amount ?? 0),
        0,
      ),
    [expenses],
  )

  const approvedAmount = useMemo(
    () =>
      approvedExpenses.reduce(
        (total, expense) =>
          total + (expense.amount ?? 0),
        0,
      ),
    [approvedExpenses],
  )

  const recentExpenses = useMemo(
    () => expenses.slice(0, 5),
    [expenses],
  )

  const resetForm = () => {
    setCategory('Travel')
    setAmount('')
    setCurrency('INR')
    setDescription('')
    setExpenseDate('')
  }

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault()

    if (
      !category ||
      !amount ||
      !currency ||
      !description.trim() ||
      !expenseDate
    ) {
      setError('Please fill in all required fields.')
      return
    }

    const numericAmount = Number(amount)

    if (
      !Number.isFinite(numericAmount) ||
      numericAmount <= 0
    ) {
      setError(
        'Expense amount must be greater than zero.',
      )
      return
    }

    if (currency.trim().length !== 3) {
      setError(
        'Currency must be a three-letter code such as INR, USD or EUR.',
      )
      return
    }

    setSaving(true)
    setError('')

    try {
      await apiFetch<ExpenseClaim>(
        '/expenses/claims',
        {
          method: 'POST',
          body: JSON.stringify({
            category,
            amount: numericAmount,
            currency: currency
              .trim()
              .toUpperCase(),
            description: description.trim(),
            expense_date: expenseDate,
          }),
        },
      )

      resetForm()
      setShowForm(false)

      await loadExpenses()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to submit expense claim',
      )
    } finally {
      setSaving(false)
    }
  }

  const getStatusClass = (
    status?: string | null,
  ) => {
    switch (status?.toLowerCase()) {
      case 'approved':
        return 'status-badge success'

      case 'rejected':
        return 'status-badge danger'

      default:
        return 'status-badge warning'
    }
  }

  const formatAmount = (
    value?: number | null,
    valueCurrency?: string | null,
  ) => {
    if (value == null) return '—'

    return `${valueCurrency || ''} ${value.toFixed(2)}`
  }

  return (
    <div className="page">
      {/* PAGE HEADER */}

      <div className="page-header">
        <div>
          <div className="eyebrow">
            My Workspace
          </div>

          <h1>Expenses</h1>

          <p>
            Manage your expense claims and track
            reimbursement status.
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
            : 'Add expense'}
        </button>
      </div>

      {error && (
        <div className="error-box">
          {error}
        </div>
      )}

      {/* =====================================================
          EXPENSE DASHBOARD
          ===================================================== */}

      <section className="expenses-dashboard-container">
        <div className="expenses-dashboard-heading">
          <div>
            <span className="dashboard-label">
              EXPENSE OVERVIEW
            </span>

            <h2>Your expenses at a glance</h2>

            <p>
              Monitor submitted claims, approval
              status and expense amounts.
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

        <div className="expenses-kpi-grid">
          <div className="expenses-kpi-card">
            <div className="expenses-kpi-top">
              <span>Total claims</span>

              <span className="expenses-kpi-icon">
                ▤
              </span>
            </div>

            <strong>
              {expenses.length}
            </strong>

            <small>
              All submitted claims
            </small>
          </div>

          <div className="expenses-kpi-card">
            <div className="expenses-kpi-top">
              <span>Pending</span>

              <span className="expenses-kpi-icon">
                ◷
              </span>
            </div>

            <strong>
              {pendingExpenses.length}
            </strong>

            <small>
              Awaiting processing
            </small>
          </div>

          <div className="expenses-kpi-card">
            <div className="expenses-kpi-top">
              <span>Approved</span>

              <span className="expenses-kpi-icon">
                ✓
              </span>
            </div>

            <strong>
              {approvedExpenses.length}
            </strong>

            <small>
              Approved claims
            </small>
          </div>

          <div className="expenses-kpi-card">
            <div className="expenses-kpi-top">
              <span>Total claimed</span>

              <span className="expenses-kpi-icon">
                ₹
              </span>
            </div>

            <strong>
              ₹{totalAmount.toFixed(2)}
            </strong>

            <small>
              Across submitted claims
            </small>
          </div>
        </div>

        {/* LOWER DASHBOARD */}

        <div className="expenses-dashboard-grid">
          {/* STATUS */}

          <div className="expenses-dashboard-card">
            <div className="expenses-card-header">
              <div>
                <h3>Claim status</h3>

                <p>
                  Current expense breakdown
                </p>
              </div>
            </div>

            <div className="expenses-status-list">
              <div className="expenses-status-row">
                <span>
                  <i className="expense-status-dot pending" />
                  Pending
                </span>

                <strong>
                  {pendingExpenses.length}
                </strong>
              </div>

              <div className="expenses-status-row">
                <span>
                  <i className="expense-status-dot approved" />
                  Approved
                </span>

                <strong>
                  {approvedExpenses.length}
                </strong>
              </div>

              <div className="expenses-status-row">
                <span>
                  <i className="expense-status-dot rejected" />
                  Rejected
                </span>

                <strong>
                  {rejectedExpenses.length}
                </strong>
              </div>
            </div>

            <div className="expenses-approved-summary">
              <span>Approved amount</span>

              <strong>
                ₹{approvedAmount.toFixed(2)}
              </strong>
            </div>
          </div>

          {/* RECENT CLAIMS */}

          <div className="expenses-dashboard-card">
            <div className="expenses-card-header">
              <div>
                <h3>Recent claims</h3>

                <p>
                  Your latest expense submissions
                </p>
              </div>
            </div>

            {recentExpenses.length === 0 ? (
              <div className="expenses-dashboard-empty">
                No expense claims yet.
              </div>
            ) : (
              <div className="expenses-recent-list">
                {recentExpenses.map(
                  (expense) => (
                    <div
                      className="expenses-recent-row"
                      key={expense.id}
                    >
                      <div>
                        <strong>
                          {expense.category ||
                            'Expense'}
                        </strong>

                        <span>
                          {expense.expense_date ||
                            '—'}
                        </span>
                      </div>

                      <div className="expenses-recent-right">
                        <strong>
                          {formatAmount(
                            expense.amount,
                            expense.currency,
                          )}
                        </strong>

                        <span
                          className={getStatusClass(
                            expense.status,
                          )}
                        >
                          {expense.status ||
                            'submitted'}
                        </span>
                      </div>
                    </div>
                  ),
                )}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* =====================================================
          EXPENSE FORM
          ===================================================== */}

      {showForm && (
        <div className="panel expenses-form-panel">
          <div className="panel-header">
            <div>
              <h2>New expense claim</h2>

              <p>
                Enter the details of your business
                expense.
              </p>
            </div>
          </div>

          <form
            className="workflow-form"
            onSubmit={handleSubmit}
          >
            <div className="form-grid">
              <div className="form-field">
                <label htmlFor="expense-category">
                  Category
                </label>

                <select
                  id="expense-category"
                  value={category}
                  onChange={(event) =>
                    setCategory(
                      event.target.value,
                    )
                  }
                >
                  <option value="Travel">
                    Travel
                  </option>

                  <option value="Meals">
                    Meals
                  </option>

                  <option value="Accommodation">
                    Accommodation
                  </option>

                  <option value="Office">
                    Office
                  </option>

                  <option value="Training">
                    Training
                  </option>

                  <option value="Other">
                    Other
                  </option>
                </select>
              </div>

              <div className="form-field">
                <label htmlFor="expense-amount">
                  Amount
                </label>

                <input
                  id="expense-amount"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={amount}
                  onChange={(event) =>
                    setAmount(
                      event.target.value,
                    )
                  }
                  placeholder="250.00"
                  required
                />
              </div>

              <div className="form-field">
                <label htmlFor="expense-currency">
                  Currency
                </label>

                <select
                  id="expense-currency"
                  value={currency}
                  onChange={(event) =>
                    setCurrency(
                      event.target.value,
                    )
                  }
                >
                  <option value="INR">
                    INR
                  </option>

                  <option value="USD">
                    USD
                  </option>

                  <option value="EUR">
                    EUR
                  </option>

                  <option value="GBP">
                    GBP
                  </option>
                </select>
              </div>

              <div className="form-field">
                <label htmlFor="expense-date">
                  Expense date
                </label>

                <input
                  id="expense-date"
                  type="date"
                  value={expenseDate}
                  onChange={(event) =>
                    setExpenseDate(
                      event.target.value,
                    )
                  }
                  required
                />
              </div>

              <div className="form-field full">
                <label htmlFor="expense-description">
                  Description
                </label>

                <textarea
                  id="expense-description"
                  value={description}
                  onChange={(event) =>
                    setDescription(
                      event.target.value,
                    )
                  }
                  placeholder="Describe the expense"
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
                  : 'Submit expense'}
              </button>

              <button
                type="button"
                className="secondary-btn"
                onClick={() => {
                  resetForm()
                  setShowForm(false)
                }}
                disabled={saving}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* =====================================================
          ALL EXPENSE CLAIMS
          ===================================================== */}

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>My expense claims</h2>

            <p>
              {user?.first_name
                ? `Claims submitted by ${user.first_name}`
                : 'Your submitted expense claims'}
            </p>
          </div>

          <button
            type="button"
            className="secondary-btn"
            onClick={() =>
              void loadExpenses()
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
            Loading expense claims...
          </div>
        ) : expenses.length === 0 ? (
          <div className="empty-state">
            <strong>
              No expense claims yet
            </strong>

            <p>
              You have not submitted any expense
              claims.
            </p>

            <button
              type="button"
              className="primary-btn"
              onClick={() => {
                setError('')
                setShowForm(true)
              }}
            >
              Add expense
            </button>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Amount</th>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {expenses.map((expense) => (
                  <tr key={expense.id}>
                    <td>
                      {expense.category ||
                        '—'}
                    </td>

                    <td>
                      {formatAmount(
                        expense.amount,
                        expense.currency,
                      )}
                    </td>

                    <td>
                      {expense.expense_date ||
                        '—'}
                    </td>

                    <td>
                      {expense.description ||
                        '—'}
                    </td>

                    <td>
                      <span
                        className={getStatusClass(
                          expense.status,
                        )}
                      >
                        {expense.status ||
                          'submitted'}
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