import { useMemo } from 'react'
import { NavLink, Route, Routes, useNavigate } from 'react-router-dom'

import Dashboard from '../pages/Dashboard'
import EmployeesPage from '../pages/EmployeesPage'
import LeavePage from '../pages/LeavePage'
import ExpensesPage from '../pages/ExpensesPage'
import PayrollPage from '../pages/PayrollPage'
import DocumentsPage from '../pages/DocumentsPage'
import OnboardingPage from '../pages/OnboardingPage'
import AnnouncementsPage from '../pages/AnnouncementsPage'
import CompliancePage from '../pages/CompliancePage'
import LifecyclePage from '../pages/LifecyclePage'
import AnalyticsPage from '../pages/AnalyticsPage'
import ProfilePage from '../pages/ProfilePage'
import AttendancePage from '../pages/AttendancePage'
import OvertimePage from '../pages/OvertimePage'
import BenefitsPage from '../pages/BenefitsPage'
import HolidayPage from '../pages/HolidayPage'
import PolicyPage from '../pages/PolicyPage'
import NotificationsPage from '../pages/NotificationsPage'
import RecruitmentPage from '../pages/RecruitmentPage'
import PerformancePage from '../pages/PerformancePage'
import AiAssistantPage from '../pages/AiAssistantPage'

import type { UserSummary } from '../types'

interface AppShellProps {
  user: UserSummary | null
  onLogout: () => void
}

export default function AppShell({
  user,
  onLogout,
}: AppShellProps) {
  const navigate = useNavigate()

  const navGroups = useMemo(
    () => [
      {
        title: 'My Workspace',
        items: [
          { label: 'Dashboard', to: '/', icon: '⌂' },
          { label: 'Attendance', to: '/attendance', icon: '◷' },
          { label: 'Leave', to: '/leave', icon: '◫' },
          { label: 'Expenses', to: '/expenses', icon: '₹' },
          { label: 'Salary slips', to: '/payroll', icon: '▤' },
          { label: 'Goals & appraisal', to: '/performance', icon: '◎' },
          { label: 'Documents', to: '/documents', icon: '▱' },
          { label: 'AI assistant', to: '/ai', icon: '✦' },
        ],
      },
      {
        title: 'HR Management',
        items: [
          { label: 'Employees', to: '/employees', icon: '♙' },
          { label: 'Overtime', to: '/overtime', icon: '◴' },
          { label: 'Benefits & Tax', to: '/benefits', icon: '◇' },
          { label: 'Holidays', to: '/holidays', icon: '□' },
          { label: 'Policies', to: '/policies', icon: '▣' },
          { label: 'Onboarding', to: '/onboarding', icon: '→' },
          { label: 'Recruitment', to: '/recruitment', icon: '⌕' },
        ],
      },
      {
        title: 'Administration',
        items: [
          {
            label: 'Announcements',
            to: '/announcements',
            icon: '◉',
          },
          {
            label: 'Compliance & Privacy',
            to: '/compliance',
            icon: '✓',
          },
          {
            label: 'Duty, Letters & Reports',
            to: '/lifecycle',
            icon: '▤',
          },
          {
            label: 'Analytics',
            to: '/analytics',
            icon: '▥',
          },
          {
            label: 'Notifications',
            to: '/notifications',
            icon: '●',
          },
          {
            
          },
        ],
      },
    ],
    [],
  )

  const initials =
    `${user?.first_name?.[0] || ''}${user?.last_name?.[0] || ''}`
      .toUpperCase() || 'U'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">HRMS</div>

        <nav className="sidebar-nav">
          {navGroups.map((group) => (
            <div className="nav-group" key={group.title}>
              <div className="nav-group-label">
                {group.title}
              </div>

              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    isActive
                      ? 'nav-item active'
                      : 'nav-item'
                  }
                >
                  <span
                    className="nav-icon"
                    aria-hidden="true"
                  >
                    {item.icon}
                  </span>

                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="avatar-circle">
            {initials}
          </div>

          <div className="profile-mini-text">
            <strong>
              {user?.first_name} {user?.last_name}
            </strong>

            <small>{user?.role}</small>
          </div>

          <button
            className="logout-icon-btn"
            type="button"
            title="Logout"
            aria-label="Logout"
            onClick={onLogout}
          >
            ↪
          </button>
        </div>
      </aside>

      <main className="content-pane">
        <header className="topbar">
          <div className="topbar-context">
            HRMS· Team member
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <button
              className="notification-button"
              type="button"
              title="Notifications"
              aria-label="Notifications"
              onClick={() => navigate('/notifications')}
            >
              ♢
            </button>

            <button
              className="user-box"
              type="button"
              onClick={() => navigate('/profile')}
              title="Open profile"
            >
              {user?.email}
            </button>
          </div>
        </header>

        <Routes>
          <Route
            path="/"
            element={<Dashboard user={user} />}
          />

          <Route
            path="/employees"
            element={<EmployeesPage user={user} />}
          />

          <Route
  path="/leave"
  element={<LeavePage user={user} />}
/>
<Route
  path="/expenses"
  element={<ExpensesPage user={user} />}
/>

<Route
  path="/holidays"
  element={<HolidayPage user={user} />}
/>

          <Route
            path="/payroll"
            element={<PayrollPage user={user} />}
          />

          <Route
            path="/documents"
            element={<DocumentsPage user={user} />}
          />

          <Route
            path="/onboarding"
            element={<OnboardingPage user={user} />}
          />

          <Route
            path="/announcements"
            element={<AnnouncementsPage user={user} />}
          />

          <Route
            path="/compliance"
            element={<CompliancePage user={user} />}
          />

          <Route
            path="/lifecycle"
            element={<LifecyclePage user={user} />}
          />

          <Route
            path="/analytics"
            element={<AnalyticsPage user={user} />}
          />

          <Route
            path="/profile"
            element={<ProfilePage user={user} />}
          />

          <Route
            path="/attendance"
            element={<AttendancePage user={user} />}
          />

          <Route
            path="/overtime"
            element={<OvertimePage user={user} />}
          />

          <Route
            path="/benefits"
            element={<BenefitsPage user={user} />}
          />

          <Route
            path="/holidays"
            element={<HolidayPage user={user} />}
          />

          <Route
            path="/policies"
            element={<PolicyPage user={user} />}
          />

          <Route
            path="/notifications"
            element={<NotificationsPage user={user} />}
          />

          <Route
            path="/recruitment"
            element={<RecruitmentPage user={user} />}
          />

          <Route
            path="/performance"
            element={<PerformancePage user={user} />}
          />

          <Route
            path="/ai"
            element={<AiAssistantPage user={user} />}
          />
        </Routes>
      </main>
    </div>
  )
}