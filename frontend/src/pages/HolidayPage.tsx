import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import { apiFetch } from '../lib/api'
import type { UserSummary } from '../types'

interface HolidayPageProps {
  user: UserSummary | null
}

interface Holiday {
  id: string
  name: string
  date: string
  description?: string | null
  is_optional?: boolean
}

export default function HolidayPage({
  user,
}: HolidayPageProps) {
  const [holidays, setHolidays] = useState<Holiday[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [showForm, setShowForm] = useState(false)

  const [name, setName] = useState('')
  const [date, setDate] = useState('')
  const [description, setDescription] = useState('')
  const [isOptional, setIsOptional] = useState(false)

  const canManage =
    user?.role === 'admin' || user?.role === 'hr'

  const loadHolidays = async () => {
    setLoading(true)
    setError('')

    try {
      const data = await apiFetch<Holiday[]>('/holidays')

      setHolidays(data)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load holidays.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadHolidays()
  }, [])

  const resetForm = () => {
    setName('')
    setDate('')
    setDescription('')
    setIsOptional(false)
  }

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault()

    if (!name.trim() || !date) {
      setError(
        'Please enter the holiday name and date.',
      )
      return
    }

    setSaving(true)
    setError('')
    setMessage('')

    try {
      await apiFetch<Holiday>('/holidays', {
        method: 'POST',
        body: JSON.stringify({
          name: name.trim(),
          date,
          description: description.trim() || null,
          is_optional: isOptional,
        }),
      })

      resetForm()
      setShowForm(false)

      setMessage('Holiday added successfully.')

      await loadHolidays()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to create holiday.',
      )
    } finally {
      setSaving(false)
    }
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const upcomingHolidays = holidays.filter(
    (holiday) => new Date(holiday.date) >= today,
  )

  const optionalHolidays = holidays.filter(
    (holiday) => holiday.is_optional,
  )

  return (
    <div className="page">

      {/* =====================================================
          PAGE HEADER
          ===================================================== */}

      <div className="page-header">
        <div>
          <div className="eyebrow">
            TIME MANAGEMENT
          </div>

          <h1>Holidays</h1>

          <p>
            View the organization holiday calendar and
            upcoming holidays.
          </p>
        </div>

        <div className="toolbar-actions">

          <button
            className="secondary-btn"
            type="button"
            onClick={() => void loadHolidays()}
            disabled={loading}
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
              {showForm ? 'Close' : 'Add Holiday'}
            </button>
          )}

        </div>
      </div>


      {/* =====================================================
          MESSAGES
          ===================================================== */}

      {error && (
        <div className="error-box">
          {error}
        </div>
      )}

      {message && (
        <div className="inline-message success">
          {message}
        </div>
      )}


      {/* =====================================================
          HOLIDAY DASHBOARD
          ===================================================== */}

      <div className="stat-grid holiday-dashboard">

        <div className="stat-card">
          <span>Total Holidays</span>

          <strong>
            {holidays.length}
          </strong>

          <small>
            Organization holidays
          </small>
        </div>


        <div className="stat-card">
          <span>Upcoming</span>

          <strong>
            {upcomingHolidays.length}
          </strong>

          <small>
            Holidays from today onwards
          </small>
        </div>


        <div className="stat-card">
          <span>Optional</span>

          <strong>
            {optionalHolidays.length}
          </strong>

          <small>
            Optional holidays
          </small>
        </div>

      </div>


      {/* =====================================================
          ADD HOLIDAY FORM
          ===================================================== */}

      {showForm && canManage && (
        <div className="panel">

          <div className="panel-header">
            <div>
              <h2>Add Holiday</h2>

              <p>
                Add a public or optional holiday to your
                organization's calendar.
              </p>
            </div>
          </div>

          <form
            className="workflow-form"
            onSubmit={handleSubmit}
          >

            <div className="form-grid">

              {/* Holiday name */}

              <div className="form-field">
                <label htmlFor="holiday-name">
                  Holiday name
                </label>

                <input
                  id="holiday-name"
                  type="text"
                  value={name}
                  onChange={(event) =>
                    setName(event.target.value)
                  }
                  placeholder="e.g. Diwali"
                  required
                />
              </div>


              {/* Date */}

              <div className="form-field">
                <label htmlFor="holiday-date">
                  Date
                </label>

                <input
                  id="holiday-date"
                  type="date"
                  value={date}
                  onChange={(event) =>
                    setDate(event.target.value)
                  }
                  required
                />
              </div>


              {/* Holiday type */}

              <div className="form-field">
                <label htmlFor="holiday-type">
                  Holiday type
                </label>

                <select
                  id="holiday-type"
                  value={
                    isOptional
                      ? 'optional'
                      : 'public'
                  }
                  onChange={(event) =>
                    setIsOptional(
                      event.target.value ===
                        'optional',
                    )
                  }
                >
                  <option value="public">
                    Public Holiday
                  </option>

                  <option value="optional">
                    Optional Holiday
                  </option>
                </select>
              </div>


              {/* Description */}

              <div className="form-field full">
                <label htmlFor="holiday-description">
                  Description
                </label>

                <textarea
                  id="holiday-description"
                  rows={4}
                  value={description}
                  onChange={(event) =>
                    setDescription(
                      event.target.value,
                    )
                  }
                  placeholder="Add any additional information about this holiday..."
                />
              </div>

            </div>


            {/* Form actions */}

            <div className="row-actions">

              <button
                className="primary-btn"
                type="submit"
                disabled={saving}
              >
                {saving
                  ? 'Adding...'
                  : 'Add Holiday'}
              </button>

              <button
                className="secondary-btn"
                type="button"
                onClick={() => {
                  resetForm()
                  setShowForm(false)
                  setError('')
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
          HOLIDAY CALENDAR
          ===================================================== */}

      <div className="panel">

        <div className="panel-header">
          <div>
            <h2>Holiday Calendar</h2>

            <p>
              Organization holidays and optional holidays.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">
            Loading holidays...
          </div>
        ) : holidays.length === 0 ? (
          <div className="empty-state">
            No holidays have been added yet.
          </div>
        ) : (
          <div className="table-wrap">

            <table className="data-table">

              <thead>
                <tr>
                  <th>Holiday</th>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Type</th>
                </tr>
              </thead>

              <tbody>

                {holidays.map((holiday) => (
                  <tr key={holiday.id}>

                    <td>
                      <strong>
                        {holiday.name}
                      </strong>
                    </td>

                    <td>
                      {holiday.date}
                    </td>

                    <td>
                      {holiday.description || '—'}
                    </td>

                    <td>
                      <span
                        className={
                          holiday.is_optional
                            ? 'status-badge warning'
                            : 'status-badge'
                        }
                      >
                        {holiday.is_optional
                          ? 'Optional'
                          : 'Public Holiday'}
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