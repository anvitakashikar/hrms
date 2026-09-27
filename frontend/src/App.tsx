import { BrowserRouter, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { apiDownload, apiFetch } from './lib/api'
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
      { label: 'Attendance', to: '/attendance' },
      { label: 'Holidays', to: '/holidays' },
      { label: 'Policies', to: '/policies' },
      { label: 'Documents', to: '/documents' },
      { label: 'Onboarding', to: '/onboarding' },
      { label: 'Announcements', to: '/announcements' },
      { label: 'Recruitment', to: '/recruitment' },
      { label: 'Performance', to: '/performance' },
      { label: 'AI Assistant', to: '/ai' },
      { label: 'Notifications', to: '/notifications' },
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
          <Route path="/leave" element={<LeavePage user={user} />} />
          <Route path="/expenses" element={<ExpensesPage user={user} />} />
          <Route path="/payroll" element={<PayrollPage user={user} />} />
          <Route path="/documents" element={<DocumentsPage user={user} />} />
          <Route path="/onboarding" element={<OnboardingPage user={user} />} />
          <Route path="/announcements" element={<AnnouncementsPage user={user} />} />
          <Route path="/attendance" element={<AttendancePage user={user} />} />
          <Route path="/holidays" element={<HolidayPage user={user} />} />
          <Route path="/policies" element={<PolicyPage user={user} />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/recruitment" element={<RecruitmentPage user={user} />} />
          <Route path="/performance" element={<PerformancePage user={user} />} />
          <Route path="/ai" element={<AiAssistantPage />} />
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

function LeavePage({ user }: { user: UserSummary | null }) {
  const [items, setItems] = useState<LeaveApplication[]>([])
  const [leaveType, setLeaveType] = useState('Annual')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [reason, setReason] = useState('')
  const [message, setMessage] = useState('')
  const isReviewer = user?.role === 'admin' || user?.role === 'hr' || user?.role === 'manager'

  const load = async () => setItems(await apiFetch<LeaveApplication[]>('/leave/applications'))

  useEffect(() => {
    load().catch((error) => setMessage(error instanceof Error ? error.message : 'Unable to load leave requests'))
  }, [user?.role])

  const apply = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/leave/applications', {
      method: 'POST',
      body: JSON.stringify({ leave_type: leaveType, start_date: startDate, end_date: endDate, reason }),
    })
    setReason('')
    setMessage('Leave request submitted')
    await load()
  }

  const decide = async (id: string, status: 'approve' | 'reject') => {
    const comment = status === 'reject' ? window.prompt('Reason for rejection?')?.trim() : ''
    if (status === 'reject' && !comment) return
    await apiFetch(`/leave/applications/${id}/${status}`, { method: 'PATCH', body: JSON.stringify({ comment }) })
    await load()
  }

  return (
    <section className="panel">
      <div className="panel-header"><div><p className="eyebrow">Time away</p><h3>Leave Requests</h3></div></div>
      {message && <p className="inline-message" role="status">{message}</p>}
      {!isReviewer && <form className="workflow-form" onSubmit={apply}>
        <label>Leave type<input value={leaveType} onChange={(event) => setLeaveType(event.target.value)} required /></label>
        <label>From<input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} required /></label>
        <label>To<input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} required /></label>
        <label>Reason<input value={reason} onChange={(event) => setReason(event.target.value)} required /></label>
        <button className="primary-btn" type="submit">Apply for leave</button>
      </form>}
      <div className="table-scroll"><table className="table">
        <thead>
          <tr>
            <th>Type</th>
            <th>Dates</th>
            <th>Status</th>
            <th>Reason</th>
            {isReviewer && <th>Review</th>}
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
              {isReviewer && <td>{item.status === 'pending' && <div className="row-actions"><button className="text-btn" type="button" onClick={() => decide(item.id, 'approve').catch((error) => setMessage(error.message))}>Approve</button><button className="text-btn danger" type="button" onClick={() => decide(item.id, 'reject').catch((error) => setMessage(error.message))}>Reject</button></div>}</td>}
            </tr>
          ))}
        </tbody>
      </table></div>
      {!items.length && <p className="muted">No leave requests.</p>}
    </section>
  )
}

function ExpensesPage({ user }: { user: UserSummary | null }) {
  const [items, setItems] = useState<ExpenseClaim[]>([])
  const [category, setCategory] = useState('Travel')
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState('INR')
  const [description, setDescription] = useState('')
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().slice(0, 10))
  const [message, setMessage] = useState('')
  const isReviewer = user?.role === 'admin' || user?.role === 'hr' || user?.role === 'manager'

  const load = async () => setItems(await apiFetch<ExpenseClaim[]>('/expenses/claims'))

  useEffect(() => {
    load().catch((error) => setMessage(error instanceof Error ? error.message : 'Unable to load expense claims'))
  }, [user?.role])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/expenses/claims', {
      method: 'POST',
      body: JSON.stringify({ category, amount: Number(amount), currency, description, expense_date: expenseDate }),
    })
    setAmount('')
    setDescription('')
    setMessage('Expense claim submitted')
    await load()
  }

  const decide = async (id: string, status: 'approved' | 'rejected') => {
    const comment = status === 'rejected' ? window.prompt('Reason for rejection?')?.trim() : ''
    if (status === 'rejected' && !comment) return
    await apiFetch(`/expenses/claims/${id}/decision`, { method: 'PATCH', body: JSON.stringify({ status, comment }) })
    await load()
  }

  return (
    <section className="panel">
      <div className="panel-header"><div><p className="eyebrow">Reimbursements</p><h3>Expense Claims</h3></div></div>
      {message && <p className="inline-message" role="status">{message}</p>}
      {!isReviewer && <form className="workflow-form" onSubmit={submit}>
        <label>Category<input value={category} onChange={(event) => setCategory(event.target.value)} required /></label>
        <label>Amount<input type="number" min="0.01" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} required /></label>
        <label>Currency<input maxLength={3} value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} required /></label>
        <label>Date<input type="date" value={expenseDate} onChange={(event) => setExpenseDate(event.target.value)} required /></label>
        <label>Description<input value={description} onChange={(event) => setDescription(event.target.value)} required /></label>
        <button className="primary-btn" type="submit">Submit claim</button>
      </form>}
      <div className="table-scroll"><table className="table">
        <thead>
          <tr>
            <th>Category</th>
            <th>Amount</th>
            <th>Date</th>
            <th>Status</th>
            {isReviewer && <th>Review</th>}
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
              {isReviewer && <td>{item.status === 'submitted' && <div className="row-actions"><button className="text-btn" type="button" onClick={() => decide(item.id, 'approved').catch((error) => setMessage(error.message))}>Approve</button><button className="text-btn danger" type="button" onClick={() => decide(item.id, 'rejected').catch((error) => setMessage(error.message))}>Reject</button></div>}</td>}
            </tr>
          ))}
        </tbody>
      </table></div>
      {!items.length && <p className="muted">No expense claims.</p>}
    </section>
  )
}

interface NotificationItem {
  id: string
  title: string
  message: string
  event: string
  created_at: string
  read_at?: string | null
}

function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([])
  const [message, setMessage] = useState('')
  const load = async () => setItems(await apiFetch<NotificationItem[]>('/notifications'))
  useEffect(() => {
    load().catch((error) => setMessage(error instanceof Error ? error.message : 'Unable to load notifications'))
  }, [])
  const markRead = async (id: string) => {
    await apiFetch(`/notifications/${id}/read`, { method: 'PATCH' })
    await load()
  }
  return <section className="panel">
    <div className="panel-header"><div><p className="eyebrow">Updates</p><h3>Notifications</h3></div><span className="muted">{items.filter((item) => !item.read_at).length} unread</span></div>
    {message && <p className="inline-message" role="status">{message}</p>}
    <ul className="notification-list">{items.map((item) => <li key={item.id} className={item.read_at ? 'read' : ''}>
      <div><strong>{item.title}</strong><p>{item.message}</p><small>{new Date(item.created_at).toLocaleString()}</small></div>
      {!item.read_at && <button className="text-btn" type="button" onClick={() => markRead(item.id).catch((error) => setMessage(error.message))}>Mark read</button>}
    </li>)}</ul>
    {!items.length && <p className="muted">You’re all caught up.</p>}
  </section>
}

interface Payslip {
  id: string
  period_start: string
  gross_pay: number
  total_deductions: number
  net_pay: number
  status: string
}

interface PayrollRun {
  id: string
  period_start: string
  period_end: string
  employee_count: number
  total_gross: number
  total_deductions: number
  total_net: number
  status: string
  payslips?: Payslip[]
}

interface SalaryComponent {
  id: string
  name: string
  kind: string
}

function PayrollPage({ user }: { user: UserSummary | null }) {
  const [summary, setSummary] = useState<{ base_salary: number; deductions: number; net_salary: number; status: string; period?: string } | null>(null)
  const [payslips, setPayslips] = useState<Payslip[]>([])
  const [runs, setRuns] = useState<PayrollRun[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [components, setComponents] = useState<SalaryComponent[]>([])
  const [selectedComponents, setSelectedComponents] = useState<string[]>([])
  const [selectedRun, setSelectedRun] = useState<PayrollRun | null>(null)
  const [componentName, setComponentName] = useState('')
  const [componentKind, setComponentKind] = useState('earning')
  const [componentValue, setComponentValue] = useState('')
  const [employeeId, setEmployeeId] = useState('')
  const [baseSalary, setBaseSalary] = useState('')
  const [ruleKind, setRuleKind] = useState('pf')
  const [employeeRate, setEmployeeRate] = useState('')
  const [employerRate, setEmployerRate] = useState('')
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7))
  const [message, setMessage] = useState('')
  const canManage = user?.role === 'admin' || user?.role === 'hr'

  const load = async () => {
    const [payrollSummary, slipItems] = await Promise.all([
      apiFetch<typeof summary>('/payroll/summary'),
      apiFetch<Payslip[]>('/payroll/payslips'),
    ])
    setSummary(payrollSummary)
    setPayslips(slipItems)
    if (canManage) {
      const [runItems, employeePage, componentItems] = await Promise.all([
        apiFetch<PayrollRun[]>('/payroll/runs'),
        apiFetch<{ items: Employee[] }>('/employees/'),
        apiFetch<SalaryComponent[]>('/payroll/components'),
      ])
      setRuns(runItems)
      setEmployees(employeePage.items)
      setComponents(componentItems)
      if (!employeeId && employeePage.items.length) setEmployeeId(employeePage.items[0].id)
    }
  }
  useEffect(() => { load().catch((error) => setMessage(error.message)) }, [user?.role])

  const addComponent = async (event: FormEvent) => {
    event.preventDefault()
    const component = await apiFetch<SalaryComponent>('/payroll/components', {
      method: 'POST',
      body: JSON.stringify({ name: componentName, kind: componentKind, calculation: 'fixed', value: Number(componentValue) }),
    })
    setComponents((current) => [...current, component])
    setComponentName('')
    setComponentValue('')
  }

  const saveStructure = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/payroll/structures', {
      method: 'POST',
      body: JSON.stringify({ employee_id: employeeId, base_salary: Number(baseSalary), component_ids: selectedComponents }),
    })
    setMessage('Salary structure saved')
  }

  const addRule = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/payroll/deduction-rules', {
      method: 'POST',
      body: JSON.stringify({ name: ruleKind.toUpperCase(), kind: ruleKind, employee_rate: Number(employeeRate || 0), employer_rate: Number(employerRate || 0), rate_multiplier: 1.5 }),
    })
    setMessage(`${ruleKind.toUpperCase()} rule saved`)
    setEmployeeRate('')
    setEmployerRate('')
  }

  const createRun = async () => {
    const [year, month] = period.split('-').map(Number)
    const monthEnd = new Date(year, month, 0).getDate()
    const run = await apiFetch<PayrollRun>('/payroll/runs', {
      method: 'POST',
      body: JSON.stringify({ period_start: `${period}-01`, period_end: `${period}-${String(monthEnd).padStart(2, '0')}` }),
    })
    setSelectedRun(run)
    setMessage('Payroll preview generated. Review totals before approval.')
    await load()
  }

  const approveRun = async () => {
    if (!selectedRun) return
    await apiFetch(`/payroll/runs/${selectedRun.id}/approve`, { method: 'PATCH' })
    setMessage('Payroll approved. Finalize to publish payslips.')
    await load()
  }

  const finalizeRun = async () => {
    if (!selectedRun) return
    await apiFetch(`/payroll/runs/${selectedRun.id}/finalize`, { method: 'PATCH' })
    setMessage('Payslips published to employees')
    setSelectedRun(null)
    await load()
  }

  return <div className="module-stack">
    <div className="page-grid payroll-summary">
      <StatCard title="Base salary" value={summary ? `₹${summary.base_salary}` : '—'} tone="blue" />
      <StatCard title="Deductions" value={summary ? `₹${summary.deductions}` : '—'} tone="amber" />
      <StatCard title="Net pay" value={summary ? `₹${summary.net_salary}` : '—'} tone="green" />
      <StatCard title="Latest period" value={summary?.period || 'No payslip'} tone="violet" />
    </div>
    {message && <p className="inline-message" role="status">{message}</p>}
    {canManage && <>
      <section className="panel"><div className="panel-header"><div><p className="eyebrow">Compensation setup</p><h3>Salary components</h3></div></div>
        <form className="workflow-form" onSubmit={(event) => addComponent(event).catch((error) => setMessage(error.message))}>
          <label>Component<input value={componentName} onChange={(event) => setComponentName(event.target.value)} required /></label>
          <label>Type<select value={componentKind} onChange={(event) => setComponentKind(event.target.value)}><option value="earning">Earning</option><option value="deduction">Deduction</option></select></label>
          <label>Monthly value<input type="number" min="0" step="0.01" value={componentValue} onChange={(event) => setComponentValue(event.target.value)} required /></label>
          <button className="secondary-btn" type="submit">Add component</button>
        </form>
        <form className="workflow-form" onSubmit={(event) => saveStructure(event).catch((error) => setMessage(error.message))}>
          <label>Employee<select value={employeeId} onChange={(event) => setEmployeeId(event.target.value)} required>{employees.map((item) => <option key={item.id} value={item.id}>{item.first_name} {item.last_name}</option>)}</select></label>
          <label>Monthly base salary<input type="number" min="0" step="0.01" value={baseSalary} onChange={(event) => setBaseSalary(event.target.value)} required /></label>
          <label>Component<select multiple value={selectedComponents} onChange={(event) => setSelectedComponents(Array.from(event.target.selectedOptions, (option) => option.value))}>{components.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.kind}</option>)}</select></label>
          <button className="primary-btn" type="submit" disabled={!employeeId}>Save salary structure</button>
        </form>
      </section>
      <section className="panel"><div className="panel-header"><div><p className="eyebrow">Configurable calculations</p><h3>Deduction and contribution rules</h3></div></div>
        <form className="workflow-form" onSubmit={(event) => addRule(event).catch((error) => setMessage(error.message))}>
          <label>Rule<select value={ruleKind} onChange={(event) => setRuleKind(event.target.value)}><option value="pf">PF</option><option value="esi">ESI</option><option value="tax">Tax / TDS</option><option value="deduction">Other deduction</option><option value="overtime">Overtime rate</option></select></label>
          <label>Employee rate %<input type="number" min="0" max="100" step="0.01" value={employeeRate} onChange={(event) => setEmployeeRate(event.target.value)} /></label>
          <label>Employer rate %<input type="number" min="0" max="100" step="0.01" value={employerRate} onChange={(event) => setEmployerRate(event.target.value)} /></label>
          <button className="secondary-btn" type="submit">Save rule</button>
        </form>
      </section>
      <section className="panel"><div className="panel-header"><div><p className="eyebrow">Payroll cycle</p><h3>Preview and finalize</h3></div></div>
        <div className="workflow-form"><label>Period<input type="month" value={period} onChange={(event) => setPeriod(event.target.value)} /></label><button className="primary-btn" type="button" onClick={() => createRun().catch((error) => setMessage(error.message))}>Generate preview</button></div>
        {selectedRun && <div className="run-preview"><strong>{selectedRun.period_start.slice(0, 7)} · {selectedRun.employee_count} employees</strong><span>Gross ₹{selectedRun.total_gross}</span><span>Deductions ₹{selectedRun.total_deductions}</span><span>Net ₹{selectedRun.total_net}</span>
          {selectedRun.status === 'preview' && <button className="secondary-btn" type="button" onClick={() => approveRun().catch((error) => setMessage(error.message))}>Approve run</button>}
          {selectedRun.status === 'approved' && <button className="primary-btn" type="button" onClick={() => finalizeRun().catch((error) => setMessage(error.message))}>Finalize and publish</button>}
        </div>}
        <div className="table-scroll"><table className="table"><thead><tr><th>Period</th><th>Employees</th><th>Gross</th><th>Net</th><th>Status</th></tr></thead><tbody>{runs.map((run) => <tr key={run.id} onClick={() => setSelectedRun(run)}><td>{run.period_start.slice(0, 7)}</td><td>{run.employee_count}</td><td>₹{run.total_gross}</td><td>₹{run.total_net}</td><td>{run.status}</td></tr>)}</tbody></table></div>
      </section>
    </>}
    <section className="panel"><div className="panel-header"><div><p className="eyebrow">Employee self-service</p><h3>Payslip history</h3></div></div>
      <div className="table-scroll"><table className="table"><thead><tr><th>Period</th><th>Gross</th><th>Deductions</th><th>Net</th><th>Document</th></tr></thead><tbody>{payslips.map((item) => <tr key={item.id}><td>{item.period_start.slice(0, 7)}</td><td>₹{item.gross_pay}</td><td>₹{item.total_deductions}</td><td>₹{item.net_pay}</td><td><button className="text-btn" type="button" onClick={() => apiDownload(`/payroll/payslips/${item.id}/download`, `payslip-${item.period_start.slice(0, 7)}.csv`).catch((error) => setMessage(error.message))}>Download CSV</button></td></tr>)}</tbody></table></div>
      {!payslips.length && <p className="muted">{summary?.status === 'no_payslip' ? 'No finalized payslips are available yet.' : 'No payslips available.'}</p>}
    </section>
  </div>
}

interface EmployeeDocument {
  id: string
  name: string
  category: string
  status: string
  expiry_date?: string | null
  rejection_reason?: string | null
  file_name: string
}

interface DocumentCategory {
  id: string
  name: string
  required: boolean
  active: boolean
}

function DocumentsPage({ user }: { user: UserSummary | null }) {
  const [documents, setDocuments] = useState<EmployeeDocument[]>([])
  const [categories, setCategories] = useState<DocumentCategory[]>([])
  const [missing, setMissing] = useState<{ owner_user_id: string; category: string }[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [categoryId, setCategoryId] = useState('')
  const [categoryName, setCategoryName] = useState('')
  const [required, setRequired] = useState(false)
  const [message, setMessage] = useState('')
  const isHr = user?.role === 'admin' || user?.role === 'hr'

  const load = async () => {
    const [docs, categoryItems, missingItems] = await Promise.all([
      apiFetch<EmployeeDocument[]>('/documents'),
      apiFetch<DocumentCategory[]>('/documents/categories'),
      apiFetch<{ owner_user_id: string; category: string }[]>('/documents/missing'),
    ])
    setDocuments(docs)
    setCategories(categoryItems)
    setMissing(missingItems)
    if (!categoryId && categoryItems.length) setCategoryId(categoryItems[0].id)
  }

  useEffect(() => {
    load().catch((error) => setMessage(error instanceof Error ? error.message : 'Unable to load documents'))
  }, [user?.role])

  const upload = async (event: FormEvent) => {
    event.preventDefault()
    if (!file || !categoryId) return
    const form = new FormData()
    form.set('file', file)
    form.set('category_id', categoryId)
    const result = await apiFetch<EmployeeDocument>('/documents', { method: 'POST', body: form })
    setDocuments((current) => [result, ...current])
    setFile(null)
    setMessage('Document uploaded for verification')
  }

  const addCategory = async (event: FormEvent) => {
    event.preventDefault()
    const category = await apiFetch<DocumentCategory>('/documents/categories', {
      method: 'POST',
      body: JSON.stringify({ name: categoryName, required }),
    })
    setCategories((current) => [...current, category])
    setCategoryId(category.id)
    setCategoryName('')
  }

  const toggleRequired = async (category: DocumentCategory) => {
    const updated = await apiFetch<DocumentCategory>(`/documents/categories/${category.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ required: !category.required }),
    })
    setCategories((current) => current.map((item) => item.id === category.id ? updated : item))
  }

  const replaceDocument = async (documentId: string, replacement: File | undefined) => {
    if (!replacement) return
    const form = new FormData()
    form.set('file', replacement)
    const updated = await apiFetch<EmployeeDocument>(`/documents/${documentId}/replace`, { method: 'POST', body: form })
    setDocuments((current) => current.map((item) => item.id === documentId ? updated : item))
    setMessage('Replacement uploaded for verification')
  }

  const review = async (documentId: string, status: 'approved' | 'rejected') => {
    const rejection_reason = status === 'rejected' ? window.prompt('Reason for rejection?')?.trim() : ''
    if (status === 'rejected' && !rejection_reason) return
    await apiFetch(`/documents/${documentId}/verification`, {
      method: 'PATCH',
      body: JSON.stringify({ status, rejection_reason }),
    })
    await load()
  }

  return (
    <div className="module-stack">
      <section className="panel">
        <div className="panel-header"><div><p className="eyebrow">Employee records</p><h3>Documents</h3></div></div>
        {message && <p className="inline-message" role="status">{message}</p>}
        <form className="workflow-form" onSubmit={upload}>
          <label>Document category<select value={categoryId} onChange={(event) => setCategoryId(event.target.value)} required>
            <option value="">Select category</option>{categories.filter((item) => item).map((item) => <option key={item.id} value={item.id}>{item.name}{item.required ? ' · required' : ''}</option>)}
          </select></label>
          <label>Choose file<input type="file" accept=".pdf,.png,.jpg,.jpeg,.doc,.docx" onChange={(event) => setFile(event.target.files?.[0] || null)} required /></label>
          <button className="primary-btn" type="submit" disabled={!file || !categoryId}>Upload document</button>
        </form>
        {isHr && <form className="category-form" onSubmit={addCategory}>
          <input aria-label="New document category" value={categoryName} onChange={(event) => setCategoryName(event.target.value)} placeholder="New category" required />
          <label className="check-label"><input type="checkbox" checked={required} onChange={(event) => setRequired(event.target.checked)} /> Required</label>
          <button className="secondary-btn" type="submit">Add category</button>
        </form>}
        {isHr && <ul className="list-stack category-list">{categories.map((category) => <li key={category.id}><span>{category.name}</span><button className="text-btn" type="button" onClick={() => toggleRequired(category).catch((error) => setMessage(error.message))}>{category.required ? 'Required' : 'Optional'}</button></li>)}</ul>}
        {isHr && <p className="muted">Missing required items: {missing.length}</p>}
        <div className="table-scroll"><table className="table">
          <thead><tr><th>Document</th><th>Category</th><th>Status</th><th>Expiry</th><th>Actions</th></tr></thead>
          <tbody>{documents.map((item) => <tr key={item.id}>
            <td>{item.name}{item.rejection_reason && <small className="table-note">Reason: {item.rejection_reason}</small>}</td>
            <td>{item.category}</td><td><span className={`status-badge ${item.status}`}>{item.status.replaceAll('_', ' ')}</span></td><td>{item.expiry_date || 'Not set'}</td>
            <td className="row-actions"><button className="text-btn" type="button" onClick={() => apiDownload(`/documents/${item.id}/download`, item.file_name).catch((error) => setMessage(error.message))}>Download</button>
              {isHr && item.status === 'pending_verification' && <><button className="text-btn" type="button" onClick={() => review(item.id, 'approved')}>Approve</button><button className="text-btn danger" type="button" onClick={() => review(item.id, 'rejected')}>Reject</button></>}
              {item.status === 'rejected' && <label className="text-btn replace-upload">Replace<input type="file" accept=".pdf,.png,.jpg,.jpeg,.doc,.docx" onChange={(event) => replaceDocument(item.id, event.target.files?.[0]).catch((error) => setMessage(error.message))} /></label>}
            </td>
          </tr>)}</tbody>
        </table></div>
        {!documents.length && <p className="muted">No documents to show.</p>}
      </section>
    </div>
  )
}

interface AttendanceRecord {
  id: string
  work_date: string
  check_in_time: string
  check_out_time?: string | null
  working_minutes: number
  overtime_minutes: number
  late_minutes: number
  status: string
}

interface RegularizationRequest {
  id: string
  work_date: string
  reason: string
  status: string
}

interface ShiftItem {
  id: string
  name: string
  start_time: string
  end_time: string
  grace_minutes: number
}

function AttendancePage({ user }: { user: UserSummary | null }) {
  const [records, setRecords] = useState<AttendanceRecord[]>([])
  const [requests, setRequests] = useState<RegularizationRequest[]>([])
  const [shifts, setShifts] = useState<ShiftItem[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [shiftName, setShiftName] = useState('Standard')
  const [shiftStart, setShiftStart] = useState('09:00')
  const [shiftEnd, setShiftEnd] = useState('17:00')
  const [employeeId, setEmployeeId] = useState('')
  const [shiftId, setShiftId] = useState('')
  const [zoneName, setZoneName] = useState('Office')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [radius, setRadius] = useState('150')
  const [dateValue, setDateValue] = useState(new Date().toISOString().slice(0, 10))
  const [reason, setReason] = useState('')
  const [message, setMessage] = useState('')
  const isReviewer = user?.role === 'admin' || user?.role === 'hr' || user?.role === 'manager'
  const canConfigure = user?.role === 'admin' || user?.role === 'hr'

  const load = async () => {
    const [history, regularizations] = await Promise.all([
      apiFetch<AttendanceRecord[]>('/attendance/history'),
      apiFetch<RegularizationRequest[]>('/attendance/regularization-requests'),
    ])
    setRecords(history)
    setRequests(regularizations)
    setShifts(await apiFetch<ShiftItem[]>('/attendance/shifts'))
    if (canConfigure) {
      const employeePage = await apiFetch<{ items: Employee[] }>('/employees/')
      setEmployees(employeePage.items)
      if (!employeeId && employeePage.items.length) setEmployeeId(employeePage.items[0].id)
    }
  }

  useEffect(() => {
    load().catch((error) => setMessage(error instanceof Error ? error.message : 'Unable to load attendance'))
  }, [user?.role])

  const locationPayload = async () => {
    if (!navigator.geolocation) return {}
    return new Promise<Record<string, number>>((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (position) => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
        () => resolve({}),
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 },
      )
    })
  }

  const attendanceAction = async (action: 'check-in' | 'check-out') => {
    const location = await locationPayload()
    await apiFetch(`/attendance/${action}`, { method: 'POST', body: JSON.stringify(location) })
    setMessage(action === 'check-in' ? 'Checked in' : 'Checked out')
    await load()
  }

  const submitRegularization = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/attendance/regularization-requests', {
      method: 'POST',
      body: JSON.stringify({ work_date: dateValue, reason }),
    })
    setReason('')
    setMessage('Regularization request submitted')
    await load()
  }

  const decide = async (id: string, status: 'approved' | 'rejected') => {
    await apiFetch(`/attendance/regularization-requests/${id}/decision`, { method: 'PATCH', body: JSON.stringify({ status }) })
    await load()
  }

  const createShift = async (event: FormEvent) => {
    event.preventDefault()
    const shift = await apiFetch<ShiftItem>('/attendance/shifts', { method: 'POST', body: JSON.stringify({ name: shiftName, start_time: shiftStart, end_time: shiftEnd }) })
    setShifts((current) => [...current, shift])
    setShiftId(shift.id)
  }

  const assignShift = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch(`/attendance/shifts/${shiftId}/assignments`, { method: 'POST', body: JSON.stringify({ employee_id: employeeId }) })
    setMessage('Shift assigned')
  }

  const createZone = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/attendance/geo-fences', { method: 'POST', body: JSON.stringify({ name: zoneName, latitude: Number(latitude), longitude: Number(longitude), radius_meters: Number(radius) }) })
    setMessage('Attendance work zone saved')
  }

  return <div className="module-stack">
    <section className="panel">
      <div className="panel-header"><div><p className="eyebrow">Time and presence</p><h3>Attendance</h3></div><div className="row-actions"><button className="primary-btn" type="button" onClick={() => attendanceAction('check-in').catch((error) => setMessage(error.message))}>Check in</button><button className="secondary-btn" type="button" onClick={() => attendanceAction('check-out').catch((error) => setMessage(error.message))}>Check out</button></div></div>
      {message && <p className="inline-message" role="status">{message}</p>}
      {canConfigure && <div className="attendance-admin-tools">
        <form className="workflow-form" onSubmit={(event) => createShift(event).catch((error) => setMessage(error.message))}>
          <label>Shift name<input value={shiftName} onChange={(event) => setShiftName(event.target.value)} required /></label><label>Starts<input type="time" value={shiftStart} onChange={(event) => setShiftStart(event.target.value)} required /></label><label>Ends<input type="time" value={shiftEnd} onChange={(event) => setShiftEnd(event.target.value)} required /></label><button className="secondary-btn" type="submit">Create shift</button>
        </form>
        <form className="workflow-form" onSubmit={(event) => assignShift(event).catch((error) => setMessage(error.message))}>
          <label>Employee<select value={employeeId} onChange={(event) => setEmployeeId(event.target.value)} required>{employees.map((item) => <option key={item.id} value={item.id}>{item.first_name} {item.last_name}</option>)}</select></label><label>Shift<select value={shiftId} onChange={(event) => setShiftId(event.target.value)} required><option value="">Select shift</option>{shifts.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.start_time}-{item.end_time}</option>)}</select></label><button className="secondary-btn" type="submit" disabled={!shiftId || !employeeId}>Assign shift</button>
        </form>
        <form className="workflow-form" onSubmit={(event) => createZone(event).catch((error) => setMessage(error.message))}>
          <label>Work zone<input value={zoneName} onChange={(event) => setZoneName(event.target.value)} required /></label><label>Latitude<input type="number" min="-90" max="90" step="any" value={latitude} onChange={(event) => setLatitude(event.target.value)} required /></label><label>Longitude<input type="number" min="-180" max="180" step="any" value={longitude} onChange={(event) => setLongitude(event.target.value)} required /></label><label>Radius (m)<input type="number" min="10" max="5000" value={radius} onChange={(event) => setRadius(event.target.value)} required /></label><button className="secondary-btn" type="submit">Save geofence</button>
        </form>
      </div>}
      <div className="table-scroll"><table className="table"><thead><tr><th>Date</th><th>In</th><th>Out</th><th>Hours</th><th>Late</th><th>Overtime</th><th>Status</th></tr></thead>
        <tbody>{records.map((record) => <tr key={record.id}><td>{record.work_date}</td><td>{record.check_in_time || '—'}</td><td>{record.check_out_time || '—'}</td><td>{(record.working_minutes / 60).toFixed(1)}</td><td>{record.late_minutes} min</td><td>{record.overtime_minutes} min</td><td><span className={`status-badge ${record.status}`}>{record.status.replaceAll('_', ' ')}</span></td></tr>)}</tbody>
      </table></div>
      {!records.length && <p className="muted">No attendance records yet.</p>}
    </section>
    <section className="panel">
      <div className="panel-header"><h3>Regularization requests</h3></div>
      {!isReviewer && <form className="workflow-form" onSubmit={submitRegularization}><label>Attendance date<input type="date" value={dateValue} onChange={(event) => setDateValue(event.target.value)} required /></label><label>Reason<input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Explain the correction" required /></label><button className="secondary-btn" type="submit">Submit request</button></form>}
      <div className="table-scroll"><table className="table"><thead><tr><th>Date</th><th>Reason</th><th>Status</th>{isReviewer && <th>Review</th>}</tr></thead><tbody>
        {requests.map((item) => <tr key={item.id}><td>{item.work_date}</td><td>{item.reason}</td><td>{item.status}</td>{isReviewer && <td>{item.status === 'pending' && <div className="row-actions"><button className="text-btn" type="button" onClick={() => decide(item.id, 'approved')}>Approve</button><button className="text-btn danger" type="button" onClick={() => decide(item.id, 'rejected')}>Reject</button></div>}</td>}</tr>)}
      </tbody></table></div>
      {!requests.length && <p className="muted">No regularization requests.</p>}
    </section>
  </div>
}

interface HolidayCalendar {
  id: string
  name: string
  department?: string | null
  location?: string | null
}

interface HolidayEntry {
  id: string
  calendar_id: string
  name: string
  date: string
  category: string
  location?: string | null
  department?: string | null
}

function HolidayPage({ user }: { user: UserSummary | null }) {
  const [calendars, setCalendars] = useState<HolidayCalendar[]>([])
  const [holidays, setHolidays] = useState<HolidayEntry[]>([])
  const [calendarId, setCalendarId] = useState('')
  const [calendarName, setCalendarName] = useState('')
  const [holidayName, setHolidayName] = useState('')
  const [holidayDate, setHolidayDate] = useState('')
  const [category, setCategory] = useState('public')
  const [department, setDepartment] = useState('')
  const [location, setLocation] = useState('')
  const [message, setMessage] = useState('')
  const canManage = user?.role === 'admin' || user?.role === 'hr'

  const load = async () => {
    const [calendarItems, holidayItems] = await Promise.all([
      apiFetch<HolidayCalendar[]>('/holidays/calendars'),
      apiFetch<HolidayEntry[]>(canManage ? '/holidays' : '/holidays/mine'),
    ])
    setCalendars(calendarItems)
    setHolidays(holidayItems)
    if (!calendarId && calendarItems.length) setCalendarId(calendarItems[0].id)
  }
  useEffect(() => { load().catch((error) => setMessage(error.message)) }, [user?.role])

  const addCalendar = async (event: FormEvent) => {
    event.preventDefault()
    const calendar = await apiFetch<HolidayCalendar>('/holidays/calendars', {
      method: 'POST', body: JSON.stringify({ name: calendarName, department: department || null, location: location || null }),
    })
    setCalendarName('')
    await load()
    setCalendarId(calendar.id)
  }

  const addHoliday = async (event: FormEvent) => {
    event.preventDefault()
    const holiday = await apiFetch<HolidayEntry>('/holidays', {
      method: 'POST', body: JSON.stringify({ calendar_id: calendarId, name: holidayName, date: holidayDate, category, department: department || null, location: location || null }),
    })
    setHolidays((current) => [...current, holiday].sort((left, right) => left.date.localeCompare(right.date)))
    setHolidayName('')
  }

  const editHoliday = async (item: HolidayEntry) => {
    const name = window.prompt('Holiday name', item.name)?.trim()
    if (!name) return
    const updated = await apiFetch<HolidayEntry>(`/holidays/${item.id}`, { method: 'PATCH', body: JSON.stringify({ name }) })
    setHolidays((current) => current.map((holiday) => holiday.id === item.id ? updated : holiday))
  }

  const deleteHoliday = async (id: string) => {
    await apiFetch<void>(`/holidays/${id}`, { method: 'DELETE' })
    setHolidays((current) => current.filter((holiday) => holiday.id !== id))
  }

  return <div className="module-stack">
    <section className="panel">
      <div className="panel-header"><div><p className="eyebrow">Time away</p><h3>Holiday calendars</h3></div></div>
      {message && <p className="inline-message" role="status">{message}</p>}
      {canManage && <form className="workflow-form" onSubmit={(event) => addCalendar(event).catch((error) => setMessage(error.message))}>
        <label>Calendar name<input value={calendarName} onChange={(event) => setCalendarName(event.target.value)} required /></label>
        <label>Department<input value={department} onChange={(event) => setDepartment(event.target.value)} placeholder="All departments" /></label>
        <label>Location<input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="All locations" /></label>
        <button className="primary-btn" type="submit">Create calendar</button>
      </form>}
      {calendars.length > 0 && <ul className="list-stack">{calendars.map((item) => <li key={item.id}><button className="text-btn" type="button" onClick={() => setCalendarId(item.id)}>{item.name}</button><span>{[item.department, item.location].filter(Boolean).join(' · ') || 'Organization-wide'}</span></li>)}</ul>}
    </section>
    <section className="panel">
      <div className="panel-header"><div><p className="eyebrow">Organization schedule</p><h3>Holidays</h3></div></div>
      {canManage && <form className="workflow-form" onSubmit={(event) => addHoliday(event).catch((error) => setMessage(error.message))}>
        <label>Holiday<input value={holidayName} onChange={(event) => setHolidayName(event.target.value)} required /></label>
        <label>Date<input type="date" value={holidayDate} onChange={(event) => setHolidayDate(event.target.value)} required /></label>
        <label>Calendar<select value={calendarId} onChange={(event) => setCalendarId(event.target.value)} required><option value="">Select calendar</option>{calendars.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Category<select value={category} onChange={(event) => setCategory(event.target.value)}><option value="public">Public</option><option value="regional">Regional</option><option value="company">Company</option></select></label>
        <button className="primary-btn" type="submit" disabled={!calendarId}>Add holiday</button>
      </form>}
      <div className="table-scroll"><table className="table"><thead><tr><th>Date</th><th>Holiday</th><th>Category</th><th>Applicability</th>{canManage && <th>Actions</th>}</tr></thead><tbody>
        {holidays.map((item) => <tr key={item.id}><td>{item.date}</td><td>{item.name}</td><td>{item.category}</td><td>{[item.department, item.location].filter(Boolean).join(' · ') || 'Calendar scope'}</td>{canManage && <td className="row-actions"><button className="text-btn" type="button" onClick={() => editHoliday(item).catch((error) => setMessage(error.message))}>Edit</button><button className="text-btn danger" type="button" onClick={() => deleteHoliday(item.id).catch((error) => setMessage(error.message))}>Delete</button></td>}</tr>)}
      </tbody></table></div>
      {!holidays.length && <p className="muted">No holidays configured for this view.</p>}
    </section>
  </div>
}

interface PolicyEntry {
  id: string
  name: string
  process: string
  description: string
  active: boolean
  rules?: { id: string; key: string; value: unknown }[]
}

function PolicyPage({ user }: { user: UserSummary | null }) {
  const [policies, setPolicies] = useState<PolicyEntry[]>([])
  const [selectedPolicy, setSelectedPolicy] = useState('')
  const [name, setName] = useState('')
  const [process, setProcess] = useState('attendance')
  const [department, setDepartment] = useState('')
  const [location, setLocation] = useState('')
  const [ruleKey, setRuleKey] = useState('')
  const [ruleValue, setRuleValue] = useState('')
  const [message, setMessage] = useState('')
  const canManage = user?.role === 'admin' || user?.role === 'hr'
  const load = async () => setPolicies(await apiFetch<PolicyEntry[]>(canManage ? '/policies' : '/policies/applicable'))
  useEffect(() => { load().catch((error) => setMessage(error.message)) }, [user?.role])

  const createPolicy = async (event: FormEvent) => {
    event.preventDefault()
    const policy = await apiFetch<PolicyEntry>('/policies', { method: 'POST', body: JSON.stringify({ name, process, department: department || null, location: location || null }) })
    setName('')
    await load()
    setSelectedPolicy(policy.id)
  }

  const createRule = async (event: FormEvent) => {
    event.preventDefault()
    if (!selectedPolicy) return
    let value: unknown = ruleValue
    try { value = JSON.parse(ruleValue) as unknown } catch { value = ruleValue }
    await apiFetch(`/policies/${selectedPolicy}/rules`, { method: 'POST', body: JSON.stringify({ key: ruleKey, value }) })
    setRuleKey('')
    setRuleValue('')
    await load()
  }

  const togglePolicy = async (policy: PolicyEntry) => {
    await apiFetch(`/policies/${policy.id}`, { method: 'PATCH', body: JSON.stringify({ active: !policy.active }) })
    await load()
  }

  const assignPolicy = async (event: FormEvent) => {
    event.preventDefault()
    if (!selectedPolicy || (!department && !location)) return
    await apiFetch('/policies/assignments', { method: 'POST', body: JSON.stringify({ policy_id: selectedPolicy, department: department || null, location: location || null }) })
    setMessage('Policy assignment saved')
  }

  return <div className="module-stack">
    <section className="panel">
      <div className="panel-header"><div><p className="eyebrow">Configurable rules</p><h3>HR Policies</h3></div></div>
      {message && <p className="inline-message" role="status">{message}</p>}
      {canManage && <form className="workflow-form" onSubmit={(event) => createPolicy(event).catch((error) => setMessage(error.message))}>
        <label>Policy name<input value={name} onChange={(event) => setName(event.target.value)} required /></label>
        <label>Process<select value={process} onChange={(event) => setProcess(event.target.value)}><option value="attendance">Attendance</option><option value="leave">Leave</option><option value="expense">Expense</option><option value="overtime">Overtime</option><option value="payroll">Payroll</option></select></label>
        <label>Department<input value={department} onChange={(event) => setDepartment(event.target.value)} placeholder="All departments" /></label>
        <label>Location<input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="All locations" /></label>
        <button className="primary-btn" type="submit">Create policy</button>
      </form>}
      <div className="table-scroll"><table className="table"><thead><tr><th>Policy</th><th>Process</th><th>Rules</th><th>Status</th>{canManage && <th>Action</th>}</tr></thead><tbody>
        {policies.map((item) => <tr key={item.id} onClick={() => setSelectedPolicy(item.id)} className={selectedPolicy === item.id ? 'selected-row' : ''}><td>{item.name}</td><td>{item.process}</td><td>{item.rules?.map((rule) => `${rule.key}: ${String(rule.value)}`).join(', ') || 'No rules'}</td><td>{item.active ? 'Active' : 'Inactive'}</td>{canManage && <td><button className="text-btn" type="button" onClick={(event) => { event.stopPropagation(); togglePolicy(item).catch((error) => setMessage(error.message)) }}>{item.active ? 'Deactivate' : 'Activate'}</button></td>}</tr>)}
      </tbody></table></div>
      {!policies.length && <p className="muted">No applicable policies.</p>}
    </section>
    {canManage && selectedPolicy && <section className="panel">
      <div className="panel-header"><h3>Policy rules and assignment</h3></div>
      <form className="workflow-form" onSubmit={(event) => createRule(event).catch((error) => setMessage(error.message))}>
        <label>Rule key<input value={ruleKey} onChange={(event) => setRuleKey(event.target.value)} required /></label>
        <label>Rule value<input value={ruleValue} onChange={(event) => setRuleValue(event.target.value)} placeholder="Number, text, or JSON" required /></label>
        <button className="secondary-btn" type="submit">Add rule</button>
      </form>
      <form className="workflow-form" onSubmit={(event) => assignPolicy(event).catch((error) => setMessage(error.message))}>
        <label>Assign department<input value={department} onChange={(event) => setDepartment(event.target.value)} placeholder="Department" /></label>
        <label>Assign location<input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Location" /></label>
        <button className="secondary-btn" type="submit">Assign policy</button>
      </form>
    </section>}
  </div>
}

interface JobPosting {
  id: string
  title: string
  department: string
  open_positions: number
  status: string
}

interface CandidateApplication {
  id: string
  candidate_id: string
  job_id: string
  candidate_name: string
  email: string
  status: string
}

interface Requisition {
  id: string
  title: string
  department: string
  openings: number
  status: string
}

function RecruitmentPage({ user }: { user: UserSummary | null }) {
  const [jobs, setJobs] = useState<JobPosting[]>([])
  const [candidates, setCandidates] = useState<CandidateApplication[]>([])
  const [requisitions, setRequisitions] = useState<Requisition[]>([])
  const [jobTitle, setJobTitle] = useState('')
  const [department, setDepartment] = useState('')
  const [openings, setOpenings] = useState('1')
  const [candidateName, setCandidateName] = useState('')
  const [candidateEmail, setCandidateEmail] = useState('')
  const [jobId, setJobId] = useState('')
  const [selectedApplication, setSelectedApplication] = useState('')
  const [interviewTime, setInterviewTime] = useState('')
  const [offerSalary, setOfferSalary] = useState('')
  const [offerExpiry, setOfferExpiry] = useState('')
  const [message, setMessage] = useState('')
  const canRecruit = user?.role === 'admin' || user?.role === 'hr' || user?.role === 'manager'

  const load = async () => {
    const [jobItems, candidateItems, requisitionItems] = await Promise.all([
      apiFetch<JobPosting[]>('/recruitment/jobs'),
      apiFetch<CandidateApplication[]>('/recruitment/applicants'),
      apiFetch<Requisition[]>('/recruitment/requisitions'),
    ])
    setJobs(jobItems)
    setCandidates(candidateItems)
    setRequisitions(requisitionItems)
    if (!jobId && jobItems.length) setJobId(jobItems[0].id)
    if (!selectedApplication && candidateItems.length) setSelectedApplication(candidateItems[0].id)
  }
  useEffect(() => {
    if (canRecruit) load().catch((error) => setMessage(error.message))
  }, [user?.role])

  const createJob = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/recruitment/jobs', { method: 'POST', body: JSON.stringify({ title: jobTitle, department, open_positions: Number(openings) }) })
    setJobTitle('')
    setMessage('Job posting published')
    await load()
  }

  const createRequisition = async () => {
    await apiFetch('/recruitment/requisitions', { method: 'POST', body: JSON.stringify({ title: jobTitle, department, openings: Number(openings) }) })
    setMessage('Requisition sent for approval')
    await load()
  }

  const addCandidate = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/recruitment/applicants', { method: 'POST', body: JSON.stringify({ job_id: jobId, candidate_name: candidateName, email: candidateEmail }) })
    setCandidateName('')
    setCandidateEmail('')
    setMessage('Candidate added to pipeline')
    await load()
  }

  const updateCandidate = async (candidate: CandidateApplication, status: string) => {
    await apiFetch(`/recruitment/applicants/${candidate.id}`, { method: 'PATCH', body: JSON.stringify({ status }) })
    await load()
  }

  const scheduleInterview = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/recruitment/interviews', { method: 'POST', body: JSON.stringify({ application_id: selectedApplication, scheduled_at: new Date(interviewTime).toISOString(), panel_user_ids: user ? [user.id] : [] }) })
    setMessage('Interview scheduled')
  }

  const createOffer = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/recruitment/offers', { method: 'POST', body: JSON.stringify({ application_id: selectedApplication, salary: Number(offerSalary), expires_at: new Date(offerExpiry).toISOString() }) })
    setMessage('Offer created')
    await load()
  }

  if (!canRecruit) return <section className="panel"><h3>Recruitment</h3><p className="muted">Recruitment data is available to HR, managers, and administrators.</p></section>

  return <div className="module-stack">
    <section className="panel"><div className="panel-header"><div><p className="eyebrow">Hiring pipeline</p><h3>Recruitment</h3></div></div>
      {message && <p className="inline-message" role="status">{message}</p>}
      <form className="workflow-form" onSubmit={(event) => createJob(event).catch((error) => setMessage(error.message))}>
        <label>Job title<input value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} required /></label><label>Department<input value={department} onChange={(event) => setDepartment(event.target.value)} required /></label><label>Openings<input type="number" min="1" value={openings} onChange={(event) => setOpenings(event.target.value)} required /></label><button className="primary-btn" type="submit">Publish job</button><button className="secondary-btn" type="button" onClick={() => createRequisition().catch((error) => setMessage(error.message))}>Request approval</button>
      </form>
      <div className="table-scroll"><table className="table"><thead><tr><th>Role</th><th>Department</th><th>Openings</th><th>Status</th></tr></thead><tbody>{jobs.map((job) => <tr key={job.id}><td>{job.title}</td><td>{job.department}</td><td>{job.open_positions}</td><td>{job.status}</td></tr>)}</tbody></table></div>
    </section>
    <section className="panel"><div className="panel-header"><div><p className="eyebrow">Candidate records</p><h3>Candidate pipeline</h3></div></div>
      <form className="workflow-form" onSubmit={(event) => addCandidate(event).catch((error) => setMessage(error.message))}>
        <label>Candidate<input value={candidateName} onChange={(event) => setCandidateName(event.target.value)} required /></label><label>Email<input type="email" value={candidateEmail} onChange={(event) => setCandidateEmail(event.target.value)} required /></label><label>Job<select value={jobId} onChange={(event) => setJobId(event.target.value)} required><option value="">Select job</option>{jobs.filter((job) => job.status === 'open').map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}</select></label><button className="secondary-btn" type="submit" disabled={!jobId}>Add candidate</button>
      </form>
      <div className="table-scroll"><table className="table"><thead><tr><th>Candidate</th><th>Email</th><th>Job</th><th>Pipeline stage</th></tr></thead><tbody>{candidates.map((candidate) => <tr key={candidate.id}><td>{candidate.candidate_name}</td><td>{candidate.email}</td><td>{jobs.find((job) => job.id === candidate.job_id)?.title || '—'}</td><td><select value={candidate.status} onChange={(event) => updateCandidate(candidate, event.target.value).catch((error) => setMessage(error.message))}><option value="applied">Applied</option><option value="screening">Screening</option><option value="interview">Interview</option><option value="offer">Offer</option><option value="hired">Hired</option><option value="rejected">Rejected</option></select></td></tr>)}</tbody></table></div>
    </section>
    <section className="panel"><div className="panel-header"><div><p className="eyebrow">Selection workflow</p><h3>Interviews and offers</h3></div></div>
      <label className="inline-field">Candidate application<select value={selectedApplication} onChange={(event) => setSelectedApplication(event.target.value)}><option value="">Select candidate</option>{candidates.map((item) => <option key={item.id} value={item.id}>{item.candidate_name} · {item.status}</option>)}</select></label>
      <form className="workflow-form" onSubmit={(event) => scheduleInterview(event).catch((error) => setMessage(error.message))}><label>Interview date and time<input type="datetime-local" value={interviewTime} onChange={(event) => setInterviewTime(event.target.value)} required /></label><button className="secondary-btn" type="submit" disabled={!selectedApplication}>Schedule interview</button></form>
      {(user?.role === 'admin' || user?.role === 'hr') && <form className="workflow-form" onSubmit={(event) => createOffer(event).catch((error) => setMessage(error.message))}><label>Offer salary<input type="number" min="0" step="0.01" value={offerSalary} onChange={(event) => setOfferSalary(event.target.value)} required /></label><label>Offer expires<input type="datetime-local" value={offerExpiry} onChange={(event) => setOfferExpiry(event.target.value)} required /></label><button className="primary-btn" type="submit" disabled={!selectedApplication}>Create offer</button></form>}
      {requisitions.length > 0 && <div className="table-scroll"><table className="table"><thead><tr><th>Requisition</th><th>Department</th><th>Openings</th><th>Status</th><th>Decision</th></tr></thead><tbody>{requisitions.map((item) => <tr key={item.id}><td>{item.title}</td><td>{item.department}</td><td>{item.openings}</td><td>{item.status}</td><td>{item.status === 'pending_approval' && (user?.role === 'admin' || user?.role === 'hr') && <div className="row-actions"><button className="text-btn" type="button" onClick={() => apiFetch(`/recruitment/requisitions/${item.id}/decision`, { method: 'PATCH', body: JSON.stringify({ status: 'approved' }) }).then(load).catch((error) => setMessage(error.message))}>Approve</button><button className="text-btn danger" type="button" onClick={() => apiFetch(`/recruitment/requisitions/${item.id}/decision`, { method: 'PATCH', body: JSON.stringify({ status: 'rejected' }) }).then(load).catch((error) => setMessage(error.message))}>Reject</button></div>}</td></tr>)}</tbody></table></div>}
    </section>
  </div>
}

interface OnboardingTask {
  id: string
  title: string
  employee_email: string
  due_date: string
  status: string
}

interface AssetRecord {
  id: string
  name: string
  status: string
  assigned_user_id?: string | null
}

function OnboardingPage({ user }: { user: UserSummary | null }) {
  const [tasks, setTasks] = useState<OnboardingTask[]>([])
  const [assets, setAssets] = useState<AssetRecord[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [dashboard, setDashboard] = useState<Record<string, number> | null>(null)
  const [title, setTitle] = useState('')
  const [assignee, setAssignee] = useState('')
  const [dueDate, setDueDate] = useState(new Date().toISOString().slice(0, 10))
  const [checklistName, setChecklistName] = useState('')
  const [checklistTasks, setChecklistTasks] = useState('Identity verification\nEquipment setup\nPolicy acknowledgement')
  const [assetName, setAssetName] = useState('')
  const [assetId, setAssetId] = useState('')
  const [message, setMessage] = useState('')
  const isHr = user?.role === 'admin' || user?.role === 'hr'
  const canAssign = isHr || user?.role === 'manager'

  const load = async () => {
    const [taskItems, assetItems] = await Promise.all([
      apiFetch<OnboardingTask[]>('/onboarding/tasks'),
      apiFetch<AssetRecord[]>('/onboarding/assets'),
    ])
    setTasks(taskItems)
    setAssets(assetItems)
    if (isHr) {
      const [overview, employeePage] = await Promise.all([
        apiFetch<Record<string, number>>('/onboarding/dashboard'),
        apiFetch<{ items: Employee[] }>('/employees/'),
      ])
      setDashboard(overview)
      setEmployees(employeePage.items)
      if (!assignee && employeePage.items.length) setAssignee(employeePage.items[0].email)
    }
    if (!assetId && assetItems.length) setAssetId(assetItems[0].id)
  }
  useEffect(() => {
    if (user) load().catch((error) => setMessage(error.message))
  }, [user?.role])

  const createTask = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/onboarding/tasks', { method: 'POST', body: JSON.stringify({ title, assignee, due_date: dueDate }) })
    setTitle('')
    setMessage('Onboarding task assigned')
    await load()
  }

  const createChecklist = async (event: FormEvent) => {
    event.preventDefault()
    const checklist = await apiFetch<{ id: string }>('/onboarding/checklists', {
      method: 'POST',
      body: JSON.stringify({ title: checklistName, tasks: checklistTasks.split('\n').map((taskTitle) => ({ title: taskTitle.trim(), days_from_start: 3 })).filter((item) => item.title) }),
    })
    await apiFetch(`/onboarding/checklists/${checklist.id}/assign`, { method: 'POST', body: JSON.stringify({ assignee }) })
    setMessage('Checklist assigned to employee')
    await load()
  }

  const updateTask = async (task: OnboardingTask, status: string) => {
    await apiFetch(`/onboarding/tasks/${task.id}`, { method: 'PATCH', body: JSON.stringify({ status }) })
    await load()
  }

  const createAsset = async (event: FormEvent) => {
    event.preventDefault()
    const asset = await apiFetch<AssetRecord>('/onboarding/assets', { method: 'POST', body: JSON.stringify({ name: assetName }) })
    setAssets((current) => [...current, asset])
    setAssetName('')
    setAssetId(asset.id)
  }

  const assignAsset = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch(`/onboarding/assets/${assetId}/assign`, { method: 'POST', body: JSON.stringify({ employee_email: assignee }) })
    setMessage('Asset assigned')
    await load()
  }

  const acknowledgeAsset = async (id: string) => {
    await apiFetch(`/onboarding/assets/${id}/acknowledge`, { method: 'PATCH' })
    await load()
  }

  const returnAsset = async (id: string) => {
    await apiFetch(`/onboarding/assets/${id}/return`, { method: 'PATCH' })
    await load()
  }

  return <div className="module-stack">
    <section className="panel"><div className="panel-header"><div><p className="eyebrow">New starter operations</p><h3>Onboarding</h3></div></div>
      {message && <p className="inline-message" role="status">{message}</p>}
      {dashboard && <div className="page-grid onboarding-summary"><StatCard title="Employees onboarding" value={String(dashboard.employees_onboarding || 0)} tone="blue" /><StatCard title="Pending tasks" value={String(dashboard.pending_tasks || 0)} tone="amber" /><StatCard title="Overdue tasks" value={String(dashboard.overdue_tasks || 0)} tone="violet" /><StatCard title="Documents pending" value={String(dashboard.documents_pending_verification || 0)} tone="green" /></div>}
      {canAssign && <form className="workflow-form" onSubmit={(event) => createTask(event).catch((error) => setMessage(error.message))}>
        <label>Task<input value={title} onChange={(event) => setTitle(event.target.value)} required /></label><label>Employee email<input type="email" list="onboarding-employees" value={assignee} onChange={(event) => setAssignee(event.target.value)} required /><datalist id="onboarding-employees">{employees.map((item) => <option key={item.id} value={item.email} />)}</datalist></label><label>Due date<input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} required /></label><button className="primary-btn" type="submit">Assign task</button>
      </form>}
      {isHr && <form className="workflow-form" onSubmit={(event) => createChecklist(event).catch((error) => setMessage(error.message))}>
        <label>Checklist template<input value={checklistName} onChange={(event) => setChecklistName(event.target.value)} placeholder="New employee checklist" required /></label><label>Tasks, one per line<textarea value={checklistTasks} onChange={(event) => setChecklistTasks(event.target.value)} rows={3} required /></label><button className="secondary-btn" type="submit">Create and assign checklist</button>
      </form>}
      <div className="table-scroll"><table className="table"><thead><tr><th>Task</th><th>Employee</th><th>Due</th><th>Status</th><th>Action</th></tr></thead><tbody>{tasks.map((task) => <tr key={task.id}><td>{task.title}</td><td>{task.employee_email}</td><td>{task.due_date}</td><td>{task.status}</td><td>{task.status !== 'completed' && (canAssign || task.employee_email === user?.email) && <button className="text-btn" type="button" onClick={() => updateTask(task, task.status === 'pending' ? 'in_progress' : 'completed').catch((error) => setMessage(error.message))}>{task.status === 'pending' ? 'Start' : 'Complete'}</button>}</td></tr>)}</tbody></table></div>
    </section>
    <section className="panel"><div className="panel-header"><div><p className="eyebrow">Equipment custody</p><h3>Assets</h3></div></div>
      {isHr && <><form className="workflow-form" onSubmit={(event) => createAsset(event).catch((error) => setMessage(error.message))}><label>Asset name<input value={assetName} onChange={(event) => setAssetName(event.target.value)} required /></label><button className="secondary-btn" type="submit">Add asset</button></form><form className="workflow-form" onSubmit={(event) => assignAsset(event).catch((error) => setMessage(error.message))}><label>Available asset<select value={assetId} onChange={(event) => setAssetId(event.target.value)}><option value="">Select asset</option>{assets.filter((item) => item.status === 'available').map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Employee email<input type="email" list="onboarding-employees" value={assignee} onChange={(event) => setAssignee(event.target.value)} /></label><button className="primary-btn" type="submit" disabled={!assetId || !assignee}>Assign asset</button></form></>}
      <div className="table-scroll"><table className="table"><thead><tr><th>Asset</th><th>Status</th><th>Action</th></tr></thead><tbody>{assets.map((asset) => <tr key={asset.id}><td>{asset.name}</td><td>{asset.status}</td><td>{asset.status === 'assigned' && asset.assigned_user_id === user?.id && <button className="text-btn" type="button" onClick={() => acknowledgeAsset(asset.id).catch((error) => setMessage(error.message))}>Acknowledge</button>}{isHr && ['assigned', 'acknowledged'].includes(asset.status) && <button className="text-btn" type="button" onClick={() => returnAsset(asset.id).catch((error) => setMessage(error.message))}>Mark returned</button>}</td></tr>)}</tbody></table></div>
      {!assets.length && <p className="muted">No assets to show.</p>}
    </section>
  </div>
}

interface PerformanceGoal {
  id: string
  title: string
  employee_user_id: string
  due_date: string
  progress: number
  status: string
}

interface ReviewCycle {
  id: string
  name: string
  start_date: string
  end_date: string
}

interface PerformanceReview {
  id: string
  employee_user_id: string
  employee_email: string
  cycle_id: string
  review_type: string
  rating: number
  notes: string
}

function PerformancePage({ user }: { user: UserSummary | null }) {
  const [goals, setGoals] = useState<PerformanceGoal[]>([])
  const [cycles, setCycles] = useState<ReviewCycle[]>([])
  const [reviews, setReviews] = useState<PerformanceReview[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [goalTitle, setGoalTitle] = useState('')
  const [goalDue, setGoalDue] = useState(new Date().toISOString().slice(0, 10))
  const [goalEmployee, setGoalEmployee] = useState('')
  const [cycleName, setCycleName] = useState('')
  const [cycleStart, setCycleStart] = useState('')
  const [cycleEnd, setCycleEnd] = useState('')
  const [selectedCycle, setSelectedCycle] = useState('')
  const [reviewType, setReviewType] = useState('self')
  const [rating, setRating] = useState('3')
  const [reviewNotes, setReviewNotes] = useState('')
  const [reviewEmployee, setReviewEmployee] = useState('')
  const [message, setMessage] = useState('')
  const canReview = user?.role === 'admin' || user?.role === 'hr' || user?.role === 'manager'
  const isHr = user?.role === 'admin' || user?.role === 'hr'

  const load = async () => {
    const [goalItems, cycleItems, reviewItems] = await Promise.all([
      apiFetch<PerformanceGoal[]>('/performance/goals'),
      apiFetch<ReviewCycle[]>('/performance/cycles'),
      apiFetch<PerformanceReview[]>('/performance/reviews'),
    ])
    setGoals(goalItems)
    setCycles(cycleItems)
    setReviews(reviewItems)
    if (!selectedCycle && cycleItems.length) setSelectedCycle(cycleItems[0].id)
    if (canReview) {
      const employeePage = await apiFetch<{ items: Employee[] }>('/employees/')
      setEmployees(employeePage.items)
      if (!reviewEmployee && employeePage.items.length) setReviewEmployee(employeePage.items[0].email)
      if (!goalEmployee && employeePage.items.length) setGoalEmployee(employeePage.items[0].email)
    }
  }
  useEffect(() => { if (user) load().catch((error) => setMessage(error.message)) }, [user?.role])

  const createGoal = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/performance/goals', { method: 'POST', body: JSON.stringify({ title: goalTitle, due_date: goalDue, employee_email: canReview ? goalEmployee : undefined }) })
    setGoalTitle('')
    setMessage('Goal saved')
    await load()
  }

  const updateProgress = async (goal: PerformanceGoal, progress: number) => {
    await apiFetch(`/performance/goals/${goal.id}`, { method: 'PATCH', body: JSON.stringify({ progress }) })
    await load()
  }

  const createCycle = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/performance/cycles', { method: 'POST', body: JSON.stringify({ name: cycleName, start_date: cycleStart, end_date: cycleEnd }) })
    setCycleName('')
    await load()
  }

  const submitReview = async (event: FormEvent) => {
    event.preventDefault()
    await apiFetch('/performance/reviews', {
      method: 'POST',
      body: JSON.stringify({ cycle_id: selectedCycle, review_type: reviewType, rating: Number(rating), notes: reviewNotes, employee_email: reviewType === 'manager' ? reviewEmployee : undefined }),
    })
    setReviewNotes('')
    setMessage('Review submitted')
    await load()
  }

  return <div className="module-stack">
    <section className="panel"><div className="panel-header"><div><p className="eyebrow">Goals and reviews</p><h3>Performance</h3></div></div>
      {message && <p className="inline-message" role="status">{message}</p>}
      <form className="workflow-form" onSubmit={(event) => createGoal(event).catch((error) => setMessage(error.message))}>
        <label>Goal<input value={goalTitle} onChange={(event) => setGoalTitle(event.target.value)} required /></label><label>Due date<input type="date" value={goalDue} onChange={(event) => setGoalDue(event.target.value)} required /></label>{canReview && <label>Employee<select value={goalEmployee} onChange={(event) => setGoalEmployee(event.target.value)}>{employees.map((item) => <option key={item.id} value={item.email}>{item.first_name} {item.last_name}</option>)}</select></label>}<button className="primary-btn" type="submit">Create goal</button>
      </form>
      <div className="goal-list">{goals.map((goal) => <div className="goal-row" key={goal.id}><div><strong>{goal.title}</strong><small>Due {goal.due_date} · {goal.status.replaceAll('_', ' ')}</small></div><label>Progress {goal.progress}%<input type="range" min="0" max="100" step="5" value={goal.progress} onChange={(event) => updateProgress(goal, Number(event.target.value)).catch((error) => setMessage(error.message))} /></label></div>)}</div>
      {!goals.length && <p className="muted">No goals assigned.</p>}
    </section>
    <section className="panel"><div className="panel-header"><div><p className="eyebrow">Review cycles</p><h3>Review workflow</h3></div></div>
      {isHr && <form className="workflow-form" onSubmit={(event) => createCycle(event).catch((error) => setMessage(error.message))}><label>Cycle name<input value={cycleName} onChange={(event) => setCycleName(event.target.value)} required /></label><label>Starts<input type="date" value={cycleStart} onChange={(event) => setCycleStart(event.target.value)} required /></label><label>Ends<input type="date" value={cycleEnd} onChange={(event) => setCycleEnd(event.target.value)} required /></label><button className="secondary-btn" type="submit">Create cycle</button></form>}
      <form className="workflow-form" onSubmit={(event) => submitReview(event).catch((error) => setMessage(error.message))}>
        <label>Cycle<select value={selectedCycle} onChange={(event) => setSelectedCycle(event.target.value)} required><option value="">Select cycle</option>{cycles.map((cycle) => <option key={cycle.id} value={cycle.id}>{cycle.name}</option>)}</select></label>
        {canReview && <label>Review type<select value={reviewType} onChange={(event) => setReviewType(event.target.value)}><option value="self">Self review</option><option value="manager">Manager review</option></select></label>}
        {canReview && reviewType === 'manager' && <label>Employee<select value={reviewEmployee} onChange={(event) => setReviewEmployee(event.target.value)}>{employees.map((item) => <option key={item.id} value={item.email}>{item.first_name} {item.last_name}</option>)}</select></label>}
        <label>Rating<select value={rating} onChange={(event) => setRating(event.target.value)}>{[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value}</option>)}</select></label><label>Feedback<input value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} required /></label><button className="primary-btn" type="submit" disabled={!selectedCycle}>Submit review</button>
      </form>
      <div className="table-scroll"><table className="table"><thead><tr><th>Review</th><th>Employee</th><th>Rating</th><th>Feedback</th></tr></thead><tbody>{reviews.map((review) => <tr key={review.id}><td>{reviewTypeLabel(review.review_type)}</td><td>{review.employee_email}</td><td>{review.rating}/5</td><td>{review.notes}</td></tr>)}</tbody></table></div>
    </section>
  </div>
}

function reviewTypeLabel(reviewType: string) {
  return reviewType === 'manager' ? 'Manager review' : 'Self review'
}

interface AssistantMessage {
  prompt: string
  answer: string
  sources: { module: string; record_count?: number }[]
}

function AiAssistantPage() {
  const [mode, setMode] = useState<'hr' | 'policy'>('hr')
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState<AssistantMessage[]>([])
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const question = prompt.trim()
    if (!question) return
    setLoading(true)
    setMessage('')
    try {
      if (mode === 'policy') {
        const result = await apiFetch<{ answer: string; sources: { module?: string; policy: string }[] }>('/ai/policy-assistant', { method: 'POST', body: JSON.stringify({ question }) })
        setMessages((current) => [...current, { prompt: question, answer: result.answer, sources: result.sources.map((source) => ({ module: source.policy })) }])
      } else {
        const result = await apiFetch<{ summary: string; sources: { module: string; record_count?: number }[] }>('/ai/assistant', { method: 'POST', body: JSON.stringify({ prompt: question }) })
        setMessages((current) => [...current, { prompt: question, answer: result.summary, sources: result.sources }])
      }
      setPrompt('')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to answer this question')
    } finally {
      setLoading(false)
    }
  }

  return <section className="panel ai-assistant">
    <div className="panel-header"><div><p className="eyebrow">Permission-aware help</p><h3>HR Assistant</h3></div></div>
    <div className="segmented-control" role="tablist"><button type="button" className={mode === 'hr' ? 'active' : ''} onClick={() => setMode('hr')}>HR data</button><button type="button" className={mode === 'policy' ? 'active' : ''} onClick={() => setMode('policy')}>Policy answers</button></div>
    <div className="assistant-thread" aria-live="polite">{messages.map((item, index) => <article className="assistant-response" key={`${item.prompt}-${index}`}><p className="assistant-question">{item.prompt}</p><p>{item.answer}</p>{item.sources.length > 0 && <small>Sources: {item.sources.map((source) => source.module).join(', ')}</small>}</article>)}{!messages.length && <p className="muted">Ask about your HR records or configured organization policies.</p>}</div>
    {message && <p className="error-box" role="alert">{message}</p>}
    <form className="workflow-form" onSubmit={submit}><label>Question<input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder={mode === 'policy' ? 'What is the leave policy?' : 'Where is my latest payslip?'} required /></label><button className="primary-btn" type="submit" disabled={loading}>{loading ? 'Checking records…' : 'Ask'}</button></form>
  </section>
}

interface AnnouncementItem {
  id: string
  title: string
  body: string
  audience: string
  status: string
  scheduled_at?: string | null
  read: boolean
}

function AnnouncementsPage({ user }: { user: UserSummary | null }) {
  const [items, setItems] = useState<AnnouncementItem[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [audience, setAudience] = useState('organization')
  const [department, setDepartment] = useState('')
  const [location, setLocation] = useState('')
  const [targetEmails, setTargetEmails] = useState<string[]>([])
  const [scheduledAt, setScheduledAt] = useState('')
  const [publish, setPublish] = useState(true)
  const [message, setMessage] = useState('')
  const canManage = user?.role === 'admin' || user?.role === 'hr'

  const load = async () => {
    const announcements = await apiFetch<AnnouncementItem[]>('/announcements')
    setItems(announcements)
    if (canManage) {
      const employeePage = await apiFetch<{ items: Employee[] }>('/employees/')
      setEmployees(employeePage.items)
    }
  }
  useEffect(() => { if (user) load().catch((error) => setMessage(error.message)) }, [user?.role])

  const createAnnouncement = async (event: FormEvent) => {
    event.preventDefault()
    const result = await apiFetch<AnnouncementItem>('/announcements', {
      method: 'POST',
      body: JSON.stringify({
        title,
        body,
        audience,
        department: audience === 'department' ? department : undefined,
        location: audience === 'location' ? location : undefined,
        target_emails: audience === 'employees' ? targetEmails : undefined,
        scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : undefined,
        publish,
      }),
    })
    setItems((current) => [result, ...current])
    setTitle('')
    setBody('')
    setMessage(result.status === 'scheduled' ? 'Announcement scheduled' : publish ? 'Announcement published' : 'Draft saved')
  }

  const markRead = async (id: string) => {
    await apiFetch(`/announcements/${id}/read`, { method: 'PATCH' })
    await load()
  }

  const setPublished = async (item: AnnouncementItem, shouldPublish: boolean) => {
    await apiFetch(`/announcements/${item.id}/${shouldPublish ? 'publish' : 'unpublish'}`, { method: 'POST' })
    await load()
  }

  return <div className="module-stack">
    <section className="panel"><div className="panel-header"><div><p className="eyebrow">Internal communication</p><h3>Announcements</h3></div></div>
      {message && <p className="inline-message" role="status">{message}</p>}
      {canManage && <form className="workflow-form" onSubmit={(event) => createAnnouncement(event).catch((error) => setMessage(error.message))}>
        <label>Title<input value={title} onChange={(event) => setTitle(event.target.value)} required /></label>
        <label>Audience<select value={audience} onChange={(event) => setAudience(event.target.value)}><option value="organization">Organization</option><option value="department">Department</option><option value="location">Location</option><option value="employees">Selected employees</option></select></label>
        {audience === 'department' && <label>Department<input value={department} onChange={(event) => setDepartment(event.target.value)} required /></label>}
        {audience === 'location' && <label>Location<input value={location} onChange={(event) => setLocation(event.target.value)} required /></label>}
        {audience === 'employees' && <label>Employees<select multiple value={targetEmails} onChange={(event) => setTargetEmails(Array.from(event.target.selectedOptions, (option) => option.value))}>{employees.map((item) => <option key={item.id} value={item.email}>{item.first_name} {item.last_name}</option>)}</select></label>}
        <label>Message<textarea rows={3} value={body} onChange={(event) => setBody(event.target.value)} required /></label>
        <label>Schedule<input type="datetime-local" value={scheduledAt} onChange={(event) => setScheduledAt(event.target.value)} /></label>
        <label className="check-label"><input type="checkbox" checked={publish} onChange={(event) => setPublish(event.target.checked)} /> Publish</label>
        <button className="primary-btn" type="submit">Save announcement</button>
      </form>}
      <ul className="announcement-list">{items.map((item) => <li key={item.id} className={item.read ? 'read' : ''}><div><div className="announcement-title"><strong>{item.title}</strong><span className={`status-badge ${item.status}`}>{item.status}</span></div><p>{item.body}</p><small>{item.audience}{item.scheduled_at ? ` · ${new Date(item.scheduled_at).toLocaleString()}` : ''}</small></div><div className="row-actions">{canManage && item.status !== 'published' && <button className="text-btn" type="button" onClick={() => setPublished(item, true).catch((error) => setMessage(error.message))}>Publish</button>}{canManage && item.status === 'published' && <button className="text-btn" type="button" onClick={() => setPublished(item, false).catch((error) => setMessage(error.message))}>Unpublish</button>}{!canManage && !item.read && <button className="text-btn" type="button" onClick={() => markRead(item.id).catch((error) => setMessage(error.message))}>Mark read</button>}</div></li>)}</ul>
      {!items.length && <p className="muted">No announcements available.</p>}
    </section>
  </div>
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
