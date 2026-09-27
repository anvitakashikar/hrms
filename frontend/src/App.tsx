import { useEffect, useState } from 'react'
import { BrowserRouter } from 'react-router-dom'

import './App.css'

import { apiFetch } from './lib/api'
import AppShell from './components/AppShell'
import AuthPage from './pages/AuthPage'

import type { Role, UserSummary } from './types'

export default function App() {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('hrms_token'),
    
  )

  const [user, setUser] = useState<UserSummary | null>(null)
  const [loading, setLoading] = useState(false)

  /*
   * When an existing token is present, restore the logged-in user.
   */
  useEffect(() => {
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }

    setLoading(true)

    apiFetch<UserSummary>('/auth/me')
      .then((profile) => {
        setUser(profile)
      })
      .catch(() => {
        localStorage.removeItem('hrms_token')
        setToken(null)
        setUser(null)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [token])

  /*
   * Login
   */
  const handleLogin = async (
    email: string,
    password: string,
  ): Promise<void> => {
    setLoading(true)

    try {
      const result = await apiFetch<{
        access_token: string
        user: UserSummary
      }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          email,
          password,
        }),
      })

      localStorage.setItem('hrms_token', result.access_token)

      setToken(result.access_token)
      setUser(result.user)
    } finally {
      setLoading(false)
    }
  }

  /*
   * Signup
   */
  const handleSignup = async (payload: {
    email: string
    password: string
    first_name: string
    last_name: string
    role: Role
    org_name: string
  }): Promise<void> => {
    setLoading(true)

    try {
      await apiFetch<{ user: UserSummary }>('/auth/signup', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      /*
       * After successful signup, automatically log the
       * newly created user in.
       */
      await handleLogin(payload.email, payload.password)
    } finally {
      setLoading(false)
    }
  }

  /*
   * Logout
   */
  const handleLogout = () => {
    localStorage.removeItem('hrms_token')
    setToken(null)
    setUser(null)
  }

  /*
   * Not authenticated → show login/signup page.
   */
  if (!token) {
    return (
      <AuthPage
        onLogin={handleLogin}
        onSignup={handleSignup}
        loading={loading}
      />
    )
  }

  /*
   * Authenticated → show the complete HRMS application.
   *
   * AppShell contains all application routes.
   */
  return (
    <BrowserRouter>
      <AppShell
        user={user}
        onLogout={handleLogout}
      />
    </BrowserRouter>
  )
}