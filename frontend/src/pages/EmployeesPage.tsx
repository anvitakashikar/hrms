import { useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../lib/api'
import type { Employee, UserSummary } from '../types'

interface EmployeesPageProps {
  user?: UserSummary | null
}

export default function EmployeesPage({
  user,
}: EmployeesPageProps) {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [error, setError] = useState<string | null>(null)

  const loadEmployees = async () => {
    try {
      setLoading(true)
      setError(null)

      const data = await apiFetch<Employee[]>('/employees')

      setEmployees(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load employees',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadEmployees()
  }, [])

  const filteredEmployees = useMemo(() => {
    const query = search.trim().toLowerCase()

    if (!query) {
      return employees
    }

    return employees.filter((employee) => {
      const name = [
        employee.first_name,
        employee.last_name,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      const email = String(
        employee.email ?? '',
      ).toLowerCase()

      const employeeId = String(
        employee.employee_code ?? '',
      ).toLowerCase()

      return (
        name.includes(query) ||
        email.includes(query) ||
        employeeId.includes(query)
      )
    })
  }, [employees, search])

  const activeCount = employees.length

  const searchCount = filteredEmployees.length

  return (
    <section className="page">
      {/* PAGE HEADER */}
      <div className="page-header">
        <div>
          <div className="eyebrow">HR Management</div>

          <h1>Employees</h1>

          <p>
            Manage employee records, organization details,
            and workforce information.
          </p>
        </div>

        <div className="page-header-actions">
          <button
            className="secondary-btn"
            type="button"
            onClick={loadEmployees}
          >
            ↻ Refresh
          </button>

          <button
            className="primary-btn"
            type="button"
          >
            + Add employee
          </button>
        </div>
      </div>

      {/* OVERVIEW */}
      <div className="section-heading">
        <div>
          <h2>Employee overview</h2>

          <p>
            Workforce information for{' '}
            {user?.first_name
              ? `${user.first_name} ${user.last_name ?? ''}`.trim()
              : 'your organization'}
            .
          </p>
        </div>
      </div>

      {/* KPI CARDS */}
      <div className="dashboard-grid">
        <div className="kpi-card">
          <div className="kpi-card-top">
            <span>Total employees</span>
            <span className="kpi-icon">♙</span>
          </div>

          <strong>{employees.length}</strong>

          <small>
            Employees currently registered
          </small>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-top">
            <span>Active employees</span>
            <span className="kpi-icon">✓</span>
          </div>

          <strong>{activeCount}</strong>

          <small>
            Active employee records
          </small>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-top">
            <span>Search results</span>
            <span className="kpi-icon">⌕</span>
          </div>

          <strong>{searchCount}</strong>

          <small>
            Matching your current search
          </small>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-top">
            <span>Directory status</span>
            <span className="kpi-icon">●</span>
          </div>

          <strong>
            {loading ? 'Syncing' : 'Ready'}
          </strong>

          <small>
            Employee directory
          </small>
        </div>
      </div>

      {/* LOWER DASHBOARD SECTION */}
      <div className="dashboard-lower">
        <div className="panel">
          <div className="panel-header">
            <div>
              <h3>Employee directory</h3>

              <p>
                Search and manage employee records.
              </p>
            </div>

            <span className="status-badge success">
              {employees.length} records
            </span>
          </div>

          <div className="snapshot-list">
            <div className="snapshot-row">
              <span>Directory</span>
              <strong>
                {loading ? 'Loading' : 'Available'}
              </strong>
            </div>

            <div className="snapshot-row">
              <span>Employees</span>
              <strong>{employees.length}</strong>
            </div>

            <div className="snapshot-row">
              <span>Filtered results</span>
              <strong>{searchCount}</strong>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <h3>Quick actions</h3>

              <p>
                Common employee management actions.
              </p>
            </div>
          </div>

          <div className="quick-actions">
            <button
              className="secondary-btn"
              type="button"
            >
              + Add employee
            </button>

            <button
              className="secondary-btn"
              type="button"
              onClick={loadEmployees}
            >
              ↻ Refresh directory
            </button>
          </div>
        </div>
      </div>

      {/* EMPLOYEE TABLE */}
      <div className="panel">
        <div className="panel-header">
          <div>
            <h3>All employees</h3>

            <p>
              View employee records and organization
              information.
            </p>
          </div>
        </div>

        <div className="toolbar">
          <div className="search-field">
            <span aria-hidden="true">⌕</span>

            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search by name, email, or employee ID..."
            />
          </div>

          <button
            className="secondary-btn"
            type="button"
            onClick={loadEmployees}
          >
            ↻ Refresh
          </button>
        </div>

        {error && (
          <div className="error-box">
            {error}
          </div>
        )}

        {loading ? (
          <div className="empty-state">
            <strong>Loading employees...</strong>

            <span>
              Retrieving employee records.
            </span>
          </div>
        ) : filteredEmployees.length === 0 ? (
          <div className="empty-state">
            <strong>No employees found</strong>

            <span>
              {search
                ? 'Try a different search.'
                : 'Employee records will appear here.'}
            </span>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Employee ID</th>
                  <th>Email</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {filteredEmployees.map((employee) => {
                  const name = [
                    employee.first_name,
                    employee.last_name,
                  ]
                    .filter(Boolean)
                    .join(' ')

                  const initials = (
                    `${employee.first_name?.[0] ?? ''}${employee.last_name?.[0] ?? ''}`
                  ).toUpperCase()

                  return (
                    <tr key={employee.id}>
                      <td>
                        <div className="employee-cell">
                          <div className="avatar-circle">
                            {initials || 'U'}
                          </div>

                          <div>
                            <strong>
                              {name ||
                                'Unnamed employee'}
                            </strong>
                          </div>
                        </div>
                      </td>

                      <td>
                        {employee.employee_code ?? '—'}
                      </td>

                      <td>
                        {employee.email ?? '—'}
                      </td>

                      <td>
                        <span className="status-badge success">
                          Active
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}
