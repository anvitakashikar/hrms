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

type AuthMode = 'landing' | 'login' | 'signup'

export default function AuthPage({
  onLogin,
  onSignup,
  loading,
}: AuthPageProps) {
  const [mode, setMode] = useState<AuthMode>('landing')

  const [email, setEmail] = useState('admin@demo.com')
  const [password, setPassword] = useState('StrongPass123!')

  const [firstName, setFirstName] = useState('Demo')
  const [lastName, setLastName] = useState('User')
  const [orgName, setOrgName] = useState('Acme Corp')
  const [role, setRole] = useState<Role>('admin')

  const [error, setError] = useState<string | null>(null)

  const openMode = (nextMode: 'login' | 'signup') => {
    setMode(nextMode)
    setError(null)
  }

  const goBack = () => {
    setMode('landing')
    setError(null)
  }

  const submit = async () => {
    try {
      setError(null)

      if (mode === 'login') {
        await onLogin(email, password)
      } else if (mode === 'signup') {
        await onSignup({
          email,
          password,
          first_name: firstName,
          last_name: lastName,
          role,
          org_name: orgName,
        })
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Authentication failed',
      )
    }
  }

  /* ---------------- LANDING PAGE ---------------- */

  if (mode === 'landing') {
    return (
      <div className="landing-page">
        <header className="landing-navbar">
          <div className="landing-logo">
            <div className="landing-logo-mark">
              H
            </div>

            <div>
              <strong>HRMS</strong>
              <span>Human Resource Management</span>
            </div>
          </div>

          <nav className="landing-nav">
            <button
              type="button"
              onClick={() =>
                document
                  .getElementById('features')
                  ?.scrollIntoView({
                    behavior: 'smooth',
                  })
              }
            >
              Features
            </button>

            <button
              type="button"
              onClick={() =>
                document
                  .getElementById('about')
                  ?.scrollIntoView({
                    behavior: 'smooth',
                  })
              }
            >
              About
            </button>

            <button
              type="button"
              className="landing-login-btn"
              onClick={() => openMode('login')}
            >
              Login
            </button>

            <button
              type="button"
              className="landing-signup-btn"
              onClick={() => openMode('signup')}
            >
              Get Started
            </button>
          </nav>
        </header>

        <main>
          {/* HERO */}

          <section className="landing-hero">
            <div className="landing-hero-content">
              <div className="landing-eyebrow">
                <span>✦</span>
                Smarter HR. Better workplaces.
              </div>

              <h1>
                Everything your
                <br />
                <span>people need.</span>
              </h1>

              <p>
                A unified HR management platform designed
                to simplify employee management, attendance,
                leave, payroll, documents, performance and
                everyday HR operations.
              </p>

              <div className="landing-hero-actions">
                <button
                  type="button"
                  className="landing-primary-btn"
                  onClick={() => openMode('signup')}
                >
                  Get Started
                  <span>→</span>
                </button>

                <button
                  type="button"
                  className="landing-outline-btn"
                  onClick={() => openMode('login')}
                >
                  Login
                </button>
              </div>

              <div className="landing-trust">
                <span>✓</span>
                One platform for your entire workforce
              </div>
            </div>

            <div className="landing-hero-visual">
              <div className="dashboard-window">
                <div className="dashboard-window-top">
                  <div className="window-dots">
                    <span />
                    <span />
                    <span />
                  </div>

                  <span className="window-title">
                    HRMS Dashboard
                  </span>
                </div>

                <div className="dashboard-preview">
                  <div className="preview-sidebar">
                    <div className="preview-brand">
                      HRMS
                    </div>

                    <div className="preview-nav active">
                      <span>⌂</span>
                      Dashboard
                    </div>

                    <div className="preview-nav">
                      <span>♙</span>
                      Employees
                    </div>

                    <div className="preview-nav">
                      <span>◷</span>
                      Attendance
                    </div>

                    <div className="preview-nav">
                      <span>◫</span>
                      Leave
                    </div>

                    <div className="preview-nav">
                      <span>▤</span>
                      Payroll
                    </div>
                  </div>

                  <div className="preview-main">
                    <div className="preview-heading">
                      <div>
                        <small>Overview</small>
                        <h3>Good morning, Team</h3>
                      </div>

                      <div className="preview-avatar">
                        A
                      </div>
                    </div>

                    <div className="preview-stats">
                      <div>
                        <span>Employees</span>
                        <strong>248</strong>
                        <small>+12 this month</small>
                      </div>

                      <div>
                        <span>Present today</span>
                        <strong>221</strong>
                        <small>89.1% attendance</small>
                      </div>

                      <div>
                        <span>Leave requests</span>
                        <strong>08</strong>
                        <small>Needs attention</small>
                      </div>
                    </div>

                    <div className="preview-chart">
                      <div className="preview-chart-header">
                        <span>Attendance overview</span>
                        <small>This week</small>
                      </div>

                      <div className="chart-bars">
                        <span style={{ height: '48%' }} />
                        <span style={{ height: '67%' }} />
                        <span style={{ height: '58%' }} />
                        <span style={{ height: '82%' }} />
                        <span style={{ height: '74%' }} />
                        <span style={{ height: '91%' }} />
                        <span style={{ height: '78%' }} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="floating-card floating-card-one">
                <span className="floating-icon">✓</span>
                <div>
                  <strong>Attendance</strong>
                  <small>89.1% today</small>
                </div>
              </div>

              <div className="floating-card floating-card-two">
                <span className="floating-icon">₹</span>
                <div>
                  <strong>Payroll</strong>
                  <small>Processed</small>
                </div>
              </div>
            </div>
          </section>

          {/* FEATURES */}

          <section
            className="landing-section"
            id="features"
          >
            <div className="landing-section-heading">
              <span className="section-eyebrow">
                CORE FEATURES
              </span>

              <h2>
                Everything you need to manage HR
              </h2>

              <p>
                From hiring to payroll and everything in
                between, HRMS brings your essential HR
                workflows together in one place.
              </p>
            </div>

            <div className="feature-grid">
              <div className="feature-card">
                <div className="feature-icon">♙</div>
                <h3>Employee Management</h3>
                <p>
                  Maintain employee profiles, organizational
                  information, roles, departments and
                  employment details.
                </p>
              </div>

              <div className="feature-card">
                <div className="feature-icon">◷</div>
                <h3>Attendance & Leave</h3>
                <p>
                  Track attendance, manage leave requests,
                  holidays and keep workforce schedules
                  organized.
                </p>
              </div>

              <div className="feature-card">
                <div className="feature-icon">₹</div>
                <h3>Payroll & Benefits</h3>
                <p>
                  Manage payroll, salary structures,
                  deductions, overtime and employee benefits.
                </p>
              </div>

              <div className="feature-card">
                <div className="feature-icon">▱</div>
                <h3>Documents</h3>
                <p>
                  Securely manage employee documents,
                  verification, expiry tracking and
                  compliance requirements.
                </p>
              </div>

              <div className="feature-card">
                <div className="feature-icon">◎</div>
                <h3>Performance</h3>
                <p>
                  Set goals, track progress and support
                  structured performance and appraisal
                  workflows.
                </p>
              </div>

              <div className="feature-card">
                <div className="feature-icon">✦</div>
                <h3>AI-Powered Insights</h3>
                <p>
                  Use intelligent assistance to understand
                  HR information and make everyday workflows
                  more efficient.
                </p>
              </div>
            </div>
          </section>

          {/* ABOUT */}

          <section
            className="landing-about"
            id="about"
          >
            <div className="about-card">
              <div className="about-content">
                <span className="section-eyebrow">
                  ONE UNIFIED PLATFORM
                </span>

                <h2>
                  Built for employees,
                  <br />
                  managers and HR teams.
                </h2>

                <p>
                  HRMS connects the people and processes
                  behind your organization. Employees can
                  manage everyday requests while HR teams
                  get the tools they need to manage the
                  workforce effectively.
                </p>

                <div className="about-points">
                  <div>
                    <span>✓</span>
                    Employee self-service
                  </div>

                  <div>
                    <span>✓</span>
                    Role-based access
                  </div>

                  <div>
                    <span>✓</span>
                    Centralized HR operations
                  </div>

                  <div>
                    <span>✓</span>
                    Data-driven insights
                  </div>
                </div>
              </div>

              <div className="about-visual">
                <div className="about-orbit orbit-one">
                  <span>HR</span>
                </div>

                <div className="about-orbit orbit-two">
                  <span>AI</span>
                </div>

                <div className="about-center">
                  <strong>HRMS</strong>
                  <small>One platform</small>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}

          <section className="landing-cta">
            <span className="section-eyebrow">
              GET STARTED
            </span>

            <h2>
              Ready to simplify your HR operations?
            </h2>

            <p>
              Bring your people, processes and HR
              operations together in one platform.
            </p>

            <button
              type="button"
              className="landing-primary-btn"
              onClick={() => openMode('signup')}
            >
              Create your account
              <span>→</span>
            </button>
          </section>
        </main>

        <footer className="landing-footer">
          <div>
            <strong>HRMS</strong>
            <span>
              Human Resource Management System
            </span>
          </div>

          <p>
            © 2026 HRMS. All rights reserved.
          </p>
        </footer>
      </div>
    )
  }

    /* ---------------- LOGIN / SIGNUP ---------------- */

  return (
    <div className="auth-page">
      <div className="auth-page-brand">
        <button
          type="button"
          onClick={goBack}
          className="auth-brand-button"
        >
          <span className="auth-brand-mark">H</span>

          <span>
            <strong>HRMS</strong>
            <small>Human Resource Management</small>
          </span>
        </button>
      </div>

      <div className="auth-content">
        <div className="auth-card-modern">
          <button
            type="button"
            className="auth-back-button"
            onClick={goBack}
          >
            ← Back to home
          </button>

          <div className="auth-card-header">
            <span className="auth-card-pill">
              {mode === 'login'
                ? 'WELCOME BACK'
                : 'GET STARTED'}
            </span>

            <h1>
              {mode === 'login'
                ? 'Welcome back'
                : 'Create your account'}
            </h1>

            <p>
              {mode === 'login'
                ? 'Sign in to access your HRMS workspace.'
                : 'Set up your account and start managing your HR workspace.'}
            </p>
          </div>

          <div className="auth-mode-switch">
            <button
              type="button"
              className={
                mode === 'login' ? 'active' : ''
              }
              onClick={() => openMode('login')}
            >
              Login
            </button>

            <button
              type="button"
              className={
                mode === 'signup' ? 'active' : ''
              }
              onClick={() => openMode('signup')}
            >
              Sign up
            </button>
          </div>

          <div className="auth-form">
            {mode === 'signup' && (
              <div className="auth-two-column">
                <label>
                  <span>First name</span>

                  <input
                    value={firstName}
                    onChange={(e) =>
                      setFirstName(e.target.value)
                    }
                    placeholder="Enter first name"
                  />
                </label>

                <label>
                  <span>Last name</span>

                  <input
                    value={lastName}
                    onChange={(e) =>
                      setLastName(e.target.value)
                    }
                    placeholder="Enter last name"
                  />
                </label>
              </div>
            )}

            {mode === 'signup' && (
              <>
                <label>
                  <span>Organization name</span>

                  <input
                    value={orgName}
                    onChange={(e) =>
                      setOrgName(e.target.value)
                    }
                    placeholder="Enter organization name"
                  />
                </label>

                <label>
                  <span>Role</span>

                  <select
                    value={role}
                    onChange={(e) =>
                      setRole(e.target.value as Role)
                    }
                  >
                    <option value="admin">Admin</option>
                    <option value="hr">HR</option>
                    <option value="manager">
                      Manager
                    </option>
                    <option value="employee">
                      Employee
                    </option>
                  </select>
                </label>
              </>
            )}

            <label>
              <span>Email address</span>

              <input
                type="email"
                value={email}
                onChange={(e) =>
                  setEmail(e.target.value)
                }
                placeholder="you@company.com"
              />
            </label>

            <label>
              <span>Password</span>

              <input
                type="password"
                value={password}
                onChange={(e) =>
                  setPassword(e.target.value)
                }
                placeholder="Enter your password"
              />
            </label>

            {error && (
              <div className="auth-error">
                <span>!</span>
                {error}
              </div>
            )}

            <button
              type="button"
              className="auth-submit-button"
              onClick={submit}
              disabled={loading}
            >
              {loading
                ? 'Please wait...'
                : mode === 'login'
                  ? 'Login to HRMS'
                  : 'Create account'}

              {!loading && <span>→</span>}
            </button>
          </div>

          <div className="auth-card-footer">
            {mode === 'login'
              ? "Don't have an account?"
              : 'Already have an account?'}

            <button
              type="button"
              onClick={() =>
                openMode(
                  mode === 'login'
                    ? 'signup'
                    : 'login',
                )
              }
            >
              {mode === 'login'
                ? 'Create one'
                : 'Login'}
            </button>
          </div>
        </div>
      </div>

      <div className="auth-page-footer">
        <span>AI-powered HR management</span>
        <span>•</span>
        <span>Secure & centralized</span>
        <span>•</span>
        <span>Built for modern teams</span>
      </div>
    </div>
  )
}