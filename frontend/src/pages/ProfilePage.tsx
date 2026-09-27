import {useEffect, useState } from 'react'
import type {FormEvent} from 'react'
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
  const [profile, setProfile] = useState<ProfileData | null>(
    null,
  )
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')

  const loadProfile = async () => {
    try {
      setLoading(true)
      setError('')

      const data = await apiFetch<ProfileData>('/profile')

      setProfile(data)
      setPhone(data.phone || '')
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

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault()

    try {
      setSaving(true)
      setError('')
      setMessage('')

      const data = await apiFetch<ProfileData>('/profile', {
        method: 'PATCH',
        body: JSON.stringify({
          phone,
          address,
        }),
      })

      setProfile(data)
      setPhone(data.phone || phone)
      setAddress(data.address || address)
      setMessage('Profile updated successfully.')
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
    [profile?.first_name, profile?.last_name]
      .filter(Boolean)
      .join(' ') ||
    user?.email ||
    'User'

  return (
    <div className="page">
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
                    {profile?.designation ||
                      profile?.role ||
                      user?.role ||
                      'Team member'}
                  </p>
                </div>
              </div>

              <span className="status-badge">
                {profile?.role || user?.role || 'Employee'}
              </span>
            </div>

            <div className="form-grid">
              <label>
                First name
                <input
                  value={profile?.first_name || ''}
                  readOnly
                />
              </label>

              <label>
                Last name
                <input
                  value={profile?.last_name || ''}
                  readOnly
                />
              </label>

              <label>
                Email
                <input
                  value={
                    profile?.email ||
                    user?.email ||
                    ''
                  }
                  readOnly
                />
              </label>

              <label>
                Employee ID
                <input
                  value={profile?.employee_id || '—'}
                  readOnly
                />
              </label>

              <label>
                Department
                <input
                  value={profile?.department || '—'}
                  readOnly
                />
              </label>

              <label>
                Designation
                <input
                  value={profile?.designation || '—'}
                  readOnly
                />
              </label>

              <label>
                Joining date
                <input
                  value={profile?.joining_date || '—'}
                  readOnly
                />
              </label>

              <label>
                Role
                <input
                  value={
                    profile?.role ||
                    user?.role ||
                    '—'
                  }
                  readOnly
                />
              </label>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Contact Information</h2>
                <p>
                  Update the contact details associated with
                  your profile.
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
                />
              </label>

              <div className="full">
                <button
                  className="primary-btn"
                  type="submit"
                  disabled={saving}
                >
                  {saving
                    ? 'Saving...'
                    : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </>
      )}
    </div>
  )
}