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
  const [newSignup, setNewSignup] = useState(false)

  /*
   * When an existing token is present, restore
   * the logged-in user.
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
        setNewSignup(false)
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
    setNewSignup(false)

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

      localStorage.setItem(
        'hrms_token',
        result.access_token,
      )

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
      await apiFetch<{ user: UserSummary }>(
        '/auth/signup',
        {
          method: 'POST',
          body: JSON.stringify(payload),
        },
      )

      /*
       * Mark this as a new signup before automatically
       * logging the user in.
       */
      setNewSignup(true)

      /*
       * Automatically log in the newly created user.
       */
      await handleLoginAfterSignup(
        payload.email,
        payload.password,
      )
    } finally {
      setLoading(false)
    }
  }

  /*
   * Login after signup.
   *
   * Unlike a normal login, this keeps the newSignup
   * state so the user can be sent to onboarding.
   */
  const handleLoginAfterSignup = async (
    email: string,
    password: string,
  ): Promise<void> => {
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

    localStorage.setItem(
      'hrms_token',
      result.access_token,
    )

    setToken(result.access_token)
    setUser(result.user)
  }

  /*
   * Logout
   */
  const handleLogout = () => {
    localStorage.removeItem('hrms_token')
    setToken(null)
    setUser(null)
    setNewSignup(false)
  }

  /*
   * Not authenticated → show landing/login/signup page.
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
   * AppShell receives whether the current session came
   * from a new signup so it can open onboarding first.
   */
  return (
    <BrowserRouter>
      <AppShell
        user={user}
        onLogout={handleLogout}
        initialRoute={
          newSignup
            ? '/onboarding'
            : '/'
        }
      />
    </BrowserRouter>
  )
}