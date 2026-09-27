import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface ProfilePageProps {
  user: UserSummary | null
}

interface ProfileData {
  id?: string
  employee_id?: string | null
  first_name?: string | null
  last_name?: string | null
  email?: string | null
  phone?: string | null
  role?: string | null
  department?: string | null
  designation?: string | null
  joining_date?: string | null
  address?: string | null
}

export default function ProfilePage({
  user,
}: ProfilePageProps) {
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [employeeId, setEmployeeId] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [role, setRole] = useState('')
  const [department, setDepartment] = useState('')
  const [designation, setDesignation] = useState('')
  const [joiningDate, setJoiningDate] = useState('')
  const [address, setAddress] = useState('')

  const loadProfile = async () => {
    try {
      setLoading(true)
      setError('')

      const data = await apiFetch<ProfileData>('/profile')

      setProfile(data)

      setEmployeeId(data.employee_id || '')
      setFirstName(data.first_name || '')
      setLastName(data.last_name || '')
      setEmail(data.email || user?.email || '')
      setPhone(data.phone || '')
      setRole(data.role || user?.role || '')
      setDepartment(data.department || '')
      setDesignation(data.designation || '')
      setJoiningDate(data.joining_date || '')
      setAddress(data.address || '')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load profile.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProfile()
  }, [])

  const startEditing = () => {
    setError('')
    setMessage('')
    setEditing(true)
  }

  const cancelEditing = () => {
    if (profile) {
      setEmployeeId(profile.employee_id || '')
      setFirstName(profile.first_name || '')
      setLastName(profile.last_name || '')
      setEmail(profile.email || user?.email || '')
      setPhone(profile.phone || '')
      setRole(profile.role || user?.role || '')
      setDepartment(profile.department || '')
      setDesignation(profile.designation || '')
      setJoiningDate(profile.joining_date || '')
      setAddress(profile.address || '')
    }

    setError('')
    setMessage('')
    setEditing(false)
  }

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault()

    try {
      setSaving(true)
      setError('')
      setMessage('')

      const data = await apiFetch<ProfileData>('/profile', {
        method: 'PATCH',
        body: JSON.stringify({
          employee_id: employeeId,
          first_name: firstName,
          last_name: lastName,
          email,
          phone,
          role,
          department,
          designation,
          joining_date: joiningDate || null,
          address,
        }),
      })

      setProfile(data)

      setEmployeeId(data.employee_id || '')
      setFirstName(data.first_name || '')
      setLastName(data.last_name || '')
      setEmail(data.email || '')
      setPhone(data.phone || '')
      setRole(data.role || '')
      setDepartment(data.department || '')
      setDesignation(data.designation || '')
      setJoiningDate(data.joining_date || '')
      setAddress(data.address || '')

      setMessage('Profile updated successfully.')
      setEditing(false)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to update profile.',
      )
    } finally {
      setSaving(false)
    }
  }

  const fullName =
    [firstName, lastName]
      .filter(Boolean)
      .join(' ') ||
    user?.email ||
    'User'

  return (
    <div className="page profile-page">
      <div className="page-header">
        <div>
          <div className="eyebrow">MY WORKSPACE</div>
          <h1>Profile</h1>
          <p>
            View and manage your personal HRMS profile
            information.
          </p>
        </div>

        <button
          className="secondary-btn"
          type="button"
          onClick={loadProfile}
          disabled={loading || saving}
        >
          Refresh
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {message && (
        <div className="inline-message success">
          {message}
        </div>
      )}

      {loading ? (
        <div className="panel">
          <div className="empty-state">
            Loading profile...
          </div>
        </div>
      ) : (
        <>
          <div className="panel">
            <div className="panel-header">
              <div className="employee-cell">
                <div className="avatar-circle">
                  {fullName.charAt(0).toUpperCase()}
                </div>

                <div>
                  <h2>{fullName}</h2>
                  <p>
                    {designation ||
                      role ||
                      'Team member'}
                  </p>
                </div>
              </div>

              <span className="status-badge">
                {role || 'Employee'}
              </span>
            </div>

            <div className="form-grid">
              <label>
                First name
                <input
                  value={firstName}
                  onChange={(event) =>
                    setFirstName(event.target.value)
                  }
                  readOnly={!editing}
                />
              </label>

              <label>
                Last name
                <input
                  value={lastName}
                  onChange={(event) =>
                    setLastName(event.target.value)
                  }
                  readOnly={!editing}
                />
              </label>

              <label>
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(event) =>
                    setEmail(event.target.value)
                  }
                  readOnly={!editing}
                />
              </label>

              <label>
                Employee ID
                <input
                  value={employeeId}
                  onChange={(event) =>
                    setEmployeeId(event.target.value)
                  }
                  readOnly={!editing}
                />
              </label>

              <label>
                Department
                <input
                  value={department}
                  onChange={(event) =>
                    setDepartment(event.target.value)
                  }
                  readOnly={!editing}
                />
              </label>

              <label>
                Designation
                <input
                  value={designation}
                  onChange={(event) =>
                    setDesignation(event.target.value)
                  }
                  readOnly={!editing}
                />
              </label>

              <label>
                Joining date
                <input
                  type="date"
                  value={joiningDate}
                  onChange={(event) =>
                    setJoiningDate(event.target.value)
                  }
                  readOnly={!editing}
                />
              </label>

              <label>
                Role
                <input
                  value={role}
                  onChange={(event) =>
                    setRole(event.target.value)
                  }
                  readOnly={!editing}
                />
              </label>
            </div>
          </div>

          <div className="panel profile-contact-panel">
            <div className="panel-header">
              <div>
                <h2>Contact Information</h2>
                <p>
                  Manage the contact details associated
                  with your profile.
                </p>
              </div>
            </div>

            <form
              className="form-grid"
              onSubmit={saveProfile}
            >
              <label>
                Phone
                <input
                  type="tel"
                  value={phone}
                  onChange={(event) =>
                    setPhone(event.target.value)
                  }
                  placeholder="Phone number"
                  readOnly={!editing}
                />
              </label>

              <label className="full">
                Address
                <textarea
                  rows={4}
                  value={address}
                  onChange={(event) =>
                    setAddress(event.target.value)
                  }
                  placeholder="Address"
                  readOnly={!editing}
                />
              </label>

              <div className="full profile-form-actions">
                {!editing ? (
                  <button
                    className="secondary-btn"
                    type="button"
                    onClick={startEditing}
                  >
                    Edit Profile
                  </button>
                ) : (
                  <>
                    <button
                      className="secondary-btn"
                      type="button"
                      onClick={cancelEditing}
                      disabled={saving}
                    >
                      Cancel
                    </button>

                    <button
                      className="primary-btn"
                      type="submit"
                      disabled={saving}
                    >
                      {saving
                        ? 'Saving...'
                        : 'Save Changes'}
                    </button>
                  </>
                )}
              </div>
            </form>
          </div>
        </>
      )}
    </div>
  )
}