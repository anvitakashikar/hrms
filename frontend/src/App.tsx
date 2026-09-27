import { BrowserRouter, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { apiFetch } from './lib/api'
import './App.css'
import type { Employee, ExpenseClaim, LeaveApplication, Role, UserSummary } from './types'

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('hrms_token'))
  const [user, setUser] = useState<UserSummary | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!token) {
      setUser(null)
      return
    }

    apiFetch<UserSummary>('/auth/me')
      .then((profile) => setUser(profile))
      .catch(() => {
        localStorage.removeItem('hrms_token')
        setToken(null)
      })
      .finally(() => setLoading(false))
  }, [token])

  const handleLogin = async (email: string, password: string) => {
    setLoading(true)
    try {
      const result = await apiFetch<{ access_token: string; user: UserSummary }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      localStorage.setItem('hrms_token', result.access_token)
      setToken(result.access_token)
      setUser(result.user)
    } finally {
      setLoading(false)
    }
  }

  const handleSignup = async (payload: { email: string; password: string; first_name: string; last_name: string; role: Role; org_name: string }) => {
    setLoading(true)
    try {
      await apiFetch<{ user: UserSummary }>('/auth/signup', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      await handleLogin(payload.email, payload.password)
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return <AuthPage onLogin={handleLogin} onSignup={handleSignup} loading={loading} />
  }

  return (
    <BrowserRouter>
      <AppShell
        user={user}
        onLogout={() => {
          localStorage.removeItem('hrms_token')
          setToken(null)
          setUser(null)
        }}
      />
    </BrowserRouter>
  )
}

function AuthPage({
  onLogin,
  onSignup,
  loading,
}: {
  onLogin: (email: string, password: string) => Promise<void>
  onSignup: (payload: { email: string; password: string; first_name: string; last_name: string; role: Role; org_name: string }) => Promise<void>
  loading: boolean
}) {
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
      setError(err instanceof Error ? err.message : 'Authentication failed')
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-header">
          <span className="pill">AI HRMS</span>
          <h1>{mode === 'login' ? 'Welcome back' : 'Create your HRMS workspace'}</h1>
        </div>
        <div className="segmented-control">
          <button type="button" className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>Login</button>
          <button type="button" className={mode === 'signup' ? 'active' : ''} onClick={() => setMode('signup')}>Sign up</button>
        </div>

        {mode === 'signup' && (
          <div className="form-grid">
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="First name" />
            <input value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="Last name" />
          </div>
        )}

        {mode === 'signup' && (
          <div className="form-grid single">
            <input value={orgName} onChange={(e) => setOrgName(e.target.value)} placeholder="Organization name" />
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              <option value="admin">Admin</option>
              <option value="hr">HR</option>
              <option value="manager">Manager</option>
              <option value="employee">Employee</option>
            </select>
          </div>
        )}

        <div className="form-grid single">
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email address" />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
        </div>

        {error && <div className="error-box">{error}</div>}
        <button className="primary-btn full" onClick={submit} disabled={loading}>
          {loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create account'}
        </button>
      </div>
    </div>
  )
}

function AppShell({ user, onLogout }: { user: UserSummary | null; onLogout: () => void }) {
  const navItems = useMemo(
    () => [
      { label: 'Dashboard', to: '/' },
      { label: 'Employees', to: '/employees' },
      { label: 'Leave', to: '/leave' },
      { label: 'Expenses', to: '/expenses' },
      { label: 'Payroll', to: '/payroll' },
      { label: 'Documents', to: '/documents' },
      { label: 'Recruitment', to: '/recruitment' },
      { label: 'Performance', to: '/performance' },
      { label: 'AI Assistant', to: '/ai' },
    ],
    [],
  )

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">HRMS</div>
        <nav>
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div>
            <strong>
              {user?.first_name} {user?.last_name}
            </strong>
            <small>{user?.role}</small>
          </div>
          <button className="secondary-btn" onClick={onLogout}>Logout</button>
        </div>
      </aside>
      <main className="content-pane">
        <header className="topbar">
          <div>
            <p className="eyebrow">Employee lifecycle</p>
            <h2>HR Operations Center</h2>
          </div>
          <div className="user-box">{user?.email}</div>
        </header>

        <Routes>
          <Route path="/" element={<Dashboard user={user} />} />
          <Route path="/employees" element={<EmployeesPage />} />
          <Route path="/leave" element={<LeavePage />} />
          <Route path="/expenses" element={<ExpensesPage />} />
          <Route path="/payroll" element={<PayrollPage />} />
          <Route path="/documents" element={<PlaceholderPage title="Documents" />} />
          <Route path="/recruitment" element={<PlaceholderPage title="Recruitment" />} />
          <Route path="/performance" element={<PlaceholderPage title="Performance" />} />
          <Route path="/ai" element={<PlaceholderPage title="AI Assistant" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

function Dashboard({ user }: { user: UserSummary | null }) {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch<{ items: Employee[] }>('/employees/')
      .then((data) => setEmployees(data.items))
      .catch(() => setEmployees([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page-grid">
      <StatCard title="Employees" value={String(employees.length)} tone="blue" />
      <StatCard title="Attendance" value="96.4%" tone="green" />
      <StatCard title="Leave Requests" value="12" tone="amber" />
      <StatCard title="Payroll" value="₹8.4L" tone="violet" />

      <section className="panel span-2">
        <div className="panel-header">
          <h3>Welcome</h3>
        </div>
        <p className="lead">
          Hello {user?.first_name || 'HR team'} — your HRMS workspace is active and uses real backend APIs for employee,
          leave, expense, and payroll operations.
        </p>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h3>People overview</h3>
        </div>
        {loading ? (
          <div className="muted">Loading team data...</div>
        ) : (
          <ul className="list-stack">
            {employees.slice(0, 5).map((employee) => (
              <li key={employee.id}>
                <span>
                  {employee.first_name} {employee.last_name}
                </span>
                <strong>{employee.department}</strong>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

function EmployeesPage() {
  const [employees, setEmployees] = useState<Employee[]>([])
  useEffect(() => {
    apiFetch<{ items: Employee[] }>('/employees/')
      .then((data) => setEmployees(data.items))
      .catch(() => setEmployees([]))
  }, [])

  return (
    <section className="panel">
      <div className="panel-header">
        <h3>Employees</h3>
        <button className="primary-btn">Add employee</button>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Employee</th>
            <th>Department</th>
            <th>Designation</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {employees.map((employee) => (
            <tr key={employee.id}>
              <td>
                {employee.first_name} {employee.last_name}
              </td>
              <td>{employee.department}</td>
              <td>{employee.designation}</td>
              <td>
                <span className="status-badge active">{employee.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function LeavePage() {
  const [items, setItems] = useState<LeaveApplication[]>([])
  useEffect(() => {
    apiFetch<LeaveApplication[]>('/leave/applications')
      .then((data) => setItems(data))
      .catch(() => setItems([]))
  }, [])

  return (
    <section className="panel">
      <div className="panel-header">
        <h3>Leave Requests</h3>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Type</th>
            <th>Dates</th>
            <th>Status</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.leave_type}</td>
              <td>
                {item.start_date} → {item.end_date}
              </td>
              <td>
                <span className="status-badge pending">{item.status}</span>
              </td>
              <td>{item.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function ExpensesPage() {
  const [items, setItems] = useState<ExpenseClaim[]>([])
  useEffect(() => {
    apiFetch<ExpenseClaim[]>('/expenses/claims')
      .then((data) => setItems(data))
      .catch(() => setItems([]))
  }, [])

  return (
    <section className="panel">
      <div className="panel-header">
        <h3>Expense Claims</h3>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Category</th>
            <th>Amount</th>
            <th>Date</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.category}</td>
              <td>
                {item.currency} {item.amount}
              </td>
              <td>{item.expense_date}</td>
              <td>
                <span className="status-badge pending">{item.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function PayrollPage() {
  const [summary, setSummary] = useState<{ base_salary: number; deductions: number; net_salary: number } | null>(null)
  useEffect(() => {
    apiFetch<{ base_salary: number; deductions: number; net_salary: number }>('/payroll/summary')
      .then((data) => setSummary(data))
      .catch(() => setSummary(null))
  }, [])

  return (
    <div className="page-grid">
      <StatCard title="Base salary" value={summary ? `₹${summary.base_salary}` : '—'} tone="blue" />
      <StatCard title="Deductions" value={summary ? `₹${summary.deductions}` : '—'} tone="amber" />
      <StatCard title="Net salary" value={summary ? `₹${summary.net_salary}` : '—'} tone="green" />
    </div>
  )
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h3>{title}</h3>
      </div>
      <p className="lead">
        This HRMS module is connected to the core platform architecture and ready for the next business workflow implementation.
      </p>
    </section>
  )
}

function StatCard({ title, value, tone }: { title: string; value: string; tone: 'blue' | 'green' | 'amber' | 'violet' }) {
  return (
    <div className={`stat-card ${tone}`}>
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  )
}

export default App
