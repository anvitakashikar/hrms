import { useState } from 'react'
import type { Role } from '../types'

interface AuthPageProps {
  onLogin: (email: string, password: string) => Promise<void>
  onSignup: (payload: {
    email: string
    password: string
    first_name: string
    last_name: string
    role: Role
    org_name: string
  }) => Promise<void>
  loading: boolean
}

export default function AuthPage({
  onLogin,
  onSignup,
  loading,
}: AuthPageProps) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')

  const [email, setEmail] = useState('admin@demo.com')
  const [password, setPassword] = useState('StrongPass123!')

  const [firstName, setFirstName] = useState('Demo')
  const [lastName, setLastName] = useState('User')
  const [orgName, setOrgName] = useState('Acme Corp')
  const [role, setRole] = useState<Role>('admin')

  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    try {
      setError(null)

      if (mode === 'login') {
        await onLogin(email, password)
      } else {
        const payload = {
          email,
          password,
          first_name: firstName,
          last_name: lastName,
          role,
          org_name: orgName,
        }

        await onSignup(payload)
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Authentication failed',
      )
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-header">
          <span className="pill">AI HRMS</span>

          <h1>
            {mode === 'login'
              ? 'Welcome back'
              : 'Create your HRMS workspace'}
          </h1>
        </div>

        <div className="segmented-control">
          <button
            type="button"
            className={mode === 'login' ? 'active' : ''}
            onClick={() => {
              setMode('login')
              setError(null)
            }}
          >
            Login
          </button>

          <button
            type="button"
            className={mode === 'signup' ? 'active' : ''}
            onClick={() => {
              setMode('signup')
              setError(null)
            }}
          >
            Sign up
          </button>
        </div>

        {mode === 'signup' && (
          <div className="form-grid">
            <input
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="First name"
            />

            <input
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="Last name"
            />
          </div>
        )}

        {mode === 'signup' && (
          <div className="form-grid single">
            <input
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              placeholder="Organization name"
            />

            <select
              value={role}
              onChange={(e) =>
                setRole(e.target.value as Role)
              }
            >
              <option value="admin">Admin</option>
              <option value="hr">HR</option>
              <option value="manager">Manager</option>
              <option value="employee">Employee</option>
            </select>
          </div>
        )}

        <div className="form-grid single">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email address"
          />

          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
          />
        </div>

        {error && (
          <div className="error-box">
            {error}
          </div>
        )}

        <button
          className="primary-btn full"
          onClick={submit}
          disabled={loading}
        >
          {loading
            ? 'Please wait...'
            : mode === 'login'
              ? 'Login'
              : 'Create account'}
        </button>
      </div>
    </div>
  )
}