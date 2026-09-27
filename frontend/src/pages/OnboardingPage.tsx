import {useEffect, useState } from 'react'
import type {FormEvent} from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface OnboardingPageProps {
  user: UserSummary | null
}

interface OnboardingRecord {
  id: string
  employee_id?: string | null
  employee_name?: string | null
  status?: string | null
  joining_date?: string | null
  completion_percentage?: number | null
  completed_at?: string | null
}

interface OnboardingTask {
  id: string
  title: string
  description?: string | null
  completed: boolean
}

export default function OnboardingPage({
  user,
}: OnboardingPageProps) {
  const [records, setRecords] = useState<OnboardingRecord[]>([])
  const [tasks, setTasks] = useState<OnboardingTask[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')

  const [employeeId, setEmployeeId] = useState('')
  const [joiningDate, setJoiningDate] = useState('')
  const [taskTitle, setTaskTitle] = useState('')
  const [taskDescription, setTaskDescription] = useState('')

  const canManage =
    user?.role === 'admin' || user?.role === 'hr'

  const loadOnboarding = async () => {
    try {
      setLoading(true)
      setMessage('')

      const [onboardingData, taskData] = await Promise.all([
        apiFetch<OnboardingRecord[]>('/onboarding'),
        apiFetch<OnboardingTask[]>('/onboarding/tasks'),
      ])

      setRecords(onboardingData)
      setTasks(taskData)
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to load onboarding information.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadOnboarding()
  }, [])

  const createOnboarding = async (event: FormEvent) => {
    event.preventDefault()

    try {
      await apiFetch('/onboarding', {
        method: 'POST',
        body: JSON.stringify({
          employee_id: employeeId,
          joining_date: joiningDate || null,
        }),
      })

      setEmployeeId('')
      setJoiningDate('')
      setMessage('Onboarding process created successfully.')

      await loadOnboarding()
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to create onboarding process.',
      )
    }
  }

  const createTask = async (event: FormEvent) => {
    event.preventDefault()

    try {
      await apiFetch('/onboarding/tasks', {
        method: 'POST',
        body: JSON.stringify({
          title: taskTitle,
          description: taskDescription || null,
        }),
      })

      setTaskTitle('')
      setTaskDescription('')
      setMessage('Onboarding task created successfully.')

      await loadOnboarding()
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to create onboarding task.',
      )
    }
  }

  const toggleTask = async (task: OnboardingTask) => {
    try {
      await apiFetch(`/onboarding/tasks/${task.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          completed: !task.completed,
        }),
      })

      await loadOnboarding()
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to update onboarding task.',
      )
    }
  }

  return (
    <div className="page onboarding-page">
      <div className="page-header">
        <div>
          <div className="eyebrow">EMPLOYEE JOURNEY</div>
          <h1>Onboarding</h1>
          <p>
            Manage new-employee onboarding and onboarding tasks.
          </p>
        </div>

        <button
          className="secondary-btn"
          type="button"
          onClick={loadOnboarding}
        >
          Refresh
        </button>
      </div>

      {message && (
        <div className="error-box">
          {message}
        </div>
      )}

      {canManage && (
        <div className="dashboard-grid">
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Start Onboarding</h2>
                <p>
                  Create an onboarding process for an employee.
                </p>
              </div>
            </div>

            <form
              className="form-grid"
              onSubmit={createOnboarding}
            >
              <label>
                Employee ID
                <input
                  value={employeeId}
                  onChange={(event) =>
                    setEmployeeId(event.target.value)
                  }
                  placeholder="Employee ID"
                  required
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
                />
              </label>

              <div className="full">
                <button
                  className="primary-btn"
                  type="submit"
                >
                  Start Onboarding
                </button>
              </div>
            </form>
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Onboarding Task</h2>
                <p>
                  Add a reusable task to the onboarding process.
                </p>
              </div>
            </div>

            <form
              className="form-grid"
              onSubmit={createTask}
            >
              <label>
                Task title
                <input
                  value={taskTitle}
                  onChange={(event) =>
                    setTaskTitle(event.target.value)
                  }
                  placeholder="e.g. Submit identity documents"
                  required
                />
              </label>

              <label className="full">
                Description
                <textarea
                  value={taskDescription}
                  onChange={(event) =>
                    setTaskDescription(event.target.value)
                  }
                  rows={4}
                  placeholder="Describe what the employee needs to complete."
                />
              </label>

              <div className="full">
                <button
                  className="secondary-btn"
                  type="submit"
                >
                  Add Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div className="panel">
          <div className="empty-state">
            Loading onboarding information...
          </div>
        </div>
      ) : (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <span>Total Onboardings</span>
              <strong>{records.length}</strong>
            </div>

            <div className="stat-card">
              <span>In Progress</span>
              <strong>
                {
                  records.filter(
                    (item) =>
                      !item.status ||
                      item.status.toLowerCase() ===
                        'in_progress',
                  ).length
                }
              </strong>
            </div>

            <div className="stat-card">
              <span>Completed</span>
              <strong>
                {
                  records.filter(
                    (item) =>
                      item.status?.toLowerCase() ===
                      'completed',
                  ).length
                }
              </strong>
            </div>

            <div className="stat-card">
              <span>Tasks</span>
              <strong>{tasks.length}</strong>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Employee Onboarding</h2>
                <p>
                  Track the onboarding progress of employees.
                </p>
              </div>
            </div>

            {records.length === 0 ? (
              <div className="empty-state">
                No onboarding processes available.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Employee</th>
                      <th>Joining Date</th>
                      <th>Progress</th>
                      <th>Status</th>
                      <th>Completed</th>
                    </tr>
                  </thead>

                  <tbody>
                    {records.map((record) => (
                      <tr key={record.id}>
                        <td>
                          <strong>
                            {record.employee_name ||
                              record.employee_id ||
                              '—'}
                          </strong>
                        </td>

                        <td>
                          {record.joining_date || '—'}
                        </td>

                        <td>
                          {record.completion_percentage != null
                            ? `${record.completion_percentage}%`
                            : '—'}
                        </td>

                        <td>
                          <span className="status-badge">
                            {record.status || 'In progress'}
                          </span>
                        </td>

                        <td>
                          {record.completed_at || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Onboarding Tasks</h2>
                <p>
                  Tasks used during employee onboarding.
                </p>
              </div>
            </div>

            {tasks.length === 0 ? (
              <div className="empty-state">
                No onboarding tasks have been created.
              </div>
            ) : (
              <div className="action-list">
                {tasks.map((task) => (
                  <div
                    className="action-row"
                    key={task.id}
                  >
                    <div>
                      <strong>{task.title}</strong>

                      {task.description && (
                        <p>{task.description}</p>
                      )}
                    </div>

                    <label className="checkbox-field">
                      <input
                        type="checkbox"
                        checked={task.completed}
                        onChange={() =>
                          toggleTask(task)
                        }
                      />
                      Completed
                    </label>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}