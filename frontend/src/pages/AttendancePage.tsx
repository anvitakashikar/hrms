import {useEffect, useState } from 'react'
import type {FormEvent} from 'react'
import type { Employee, UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface AttendancePageProps {
  user: UserSummary | null
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

export default function AttendancePage({ user }: AttendancePageProps) {
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

  const [dateValue, setDateValue] = useState(
    new Date().toISOString().slice(0, 10),
  )
  const [reason, setReason] = useState('')
  const [message, setMessage] = useState('')

  const isReviewer =
    user?.role === 'admin' ||
    user?.role === 'hr' ||
    user?.role === 'manager'

  const canConfigure = user?.role === 'admin' || user?.role === 'hr'

  const load = async () => {
    const [history, regularizations, shiftList] = await Promise.all([
      apiFetch<AttendanceRecord[]>('/attendance/history'),
      apiFetch<RegularizationRequest[]>(
        '/attendance/regularization-requests',
      ),
      apiFetch<ShiftItem[]>('/attendance/shifts'),
    ])

    setRecords(history)
    setRequests(regularizations)
    setShifts(shiftList)

    if (canConfigure) {
      const employeePage = await apiFetch<{ items: Employee[] }>(
        '/employees/',
      )

      setEmployees(employeePage.items)

      if (!employeeId && employeePage.items.length) {
        setEmployeeId(employeePage.items[0].id)
      }
    }
  }

  useEffect(() => {
    load().catch((error) =>
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to load attendance',
      ),
    )
  }, [user?.role])

  const locationPayload = async () => {
    if (!navigator.geolocation) {
      return {}
    }

    return new Promise<Record<string, number>>((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (position) =>
          resolve({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          }),
        () => resolve({}),
        {
          enableHighAccuracy: true,
          timeout: 5000,
          maximumAge: 0,
        },
      )
    })
  }

  const attendanceAction = async (
    action: 'check-in' | 'check-out',
  ) => {
    const location = await locationPayload()

    await apiFetch(`/attendance/${action}`, {
      method: 'POST',
      body: JSON.stringify(location),
    })

    setMessage(action === 'check-in' ? 'Checked in' : 'Checked out')

    await load()
  }

  const submitRegularization = async (event: FormEvent) => {
    event.preventDefault()

    await apiFetch('/attendance/regularization-requests', {
      method: 'POST',
      body: JSON.stringify({
        work_date: dateValue,
        reason,
      }),
    })

    setReason('')
    setMessage('Regularization request submitted')

    await load()
  }

  const decide = async (
    id: string,
    status: 'approved' | 'rejected',
  ) => {
    await apiFetch(
      `/attendance/regularization-requests/${id}/decision`,
      {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      },
    )

    await load()
  }

  const createShift = async (event: FormEvent) => {
    event.preventDefault()

    const shift = await apiFetch<ShiftItem>(
      '/attendance/shifts',
      {
        method: 'POST',
        body: JSON.stringify({
          name: shiftName,
          start_time: shiftStart,
          end_time: shiftEnd,
        }),
      },
    )

    setShifts((current) => [...current, shift])
    setShiftId(shift.id)
    setMessage('Shift created')
  }

  const assignShift = async (event: FormEvent) => {
    event.preventDefault()

    await apiFetch(
      `/attendance/shifts/${shiftId}/assignments`,
      {
        method: 'POST',
        body: JSON.stringify({
          employee_id: employeeId,
        }),
      },
    )

    setMessage('Shift assigned')
  }

  const createZone = async (event: FormEvent) => {
    event.preventDefault()

    await apiFetch('/attendance/geo-fences', {
      method: 'POST',
      body: JSON.stringify({
        name: zoneName,
        latitude: Number(latitude),
        longitude: Number(longitude),
        radius_meters: Number(radius),
      }),
    })

    setMessage('Attendance work zone saved')
  }

  return (
    <div className="module-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Time and presence</p>
            <h3>Attendance</h3>
          </div>

          <div className="row-actions">
            <button
              className="primary-btn"
              type="button"
              onClick={() =>
                attendanceAction('check-in').catch((error) =>
                  setMessage(
                    error instanceof Error
                      ? error.message
                      : 'Unable to check in',
                  ),
                )
              }
            >
              Check in
            </button>

            <button
              className="secondary-btn"
              type="button"
              onClick={() =>
                attendanceAction('check-out').catch((error) =>
                  setMessage(
                    error instanceof Error
                      ? error.message
                      : 'Unable to check out',
                  ),
                )
              }
            >
              Check out
            </button>
          </div>
        </div>

        {message && (
          <p className="inline-message" role="status">
            {message}
          </p>
        )}

        {canConfigure && (
          <div className="attendance-admin-tools">
            <form
              className="workflow-form"
              onSubmit={(event) =>
                createShift(event).catch((error) =>
                  setMessage(
                    error instanceof Error
                      ? error.message
                      : 'Unable to create shift',
                  ),
                )
              }
            >
              <label>
                Shift name
                <input
                  value={shiftName}
                  onChange={(event) =>
                    setShiftName(event.target.value)
                  }
                  required
                />
              </label>

              <label>
                Starts
                <input
                  type="time"
                  value={shiftStart}
                  onChange={(event) =>
                    setShiftStart(event.target.value)
                  }
                  required
                />
              </label>

              <label>
                Ends
                <input
                  type="time"
                  value={shiftEnd}
                  onChange={(event) =>
                    setShiftEnd(event.target.value)
                  }
                  required
                />
              </label>

              <button className="secondary-btn" type="submit">
                Create shift
              </button>
            </form>

            <form
              className="workflow-form"
              onSubmit={(event) =>
                assignShift(event).catch((error) =>
                  setMessage(
                    error instanceof Error
                      ? error.message
                      : 'Unable to assign shift',
                  ),
                )
              }
            >
              <label>
                Employee
                <select
                  value={employeeId}
                  onChange={(event) =>
                    setEmployeeId(event.target.value)
                  }
                  required
                >
                  {employees.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.first_name} {item.last_name}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Shift
                <select
                  value={shiftId}
                  onChange={(event) =>
                    setShiftId(event.target.value)
                  }
                  required
                >
                  <option value="">Select shift</option>

                  {shifts.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} · {item.start_time}-
                      {item.end_time}
                    </option>
                  ))}
                </select>
              </label>

              <button
                className="secondary-btn"
                type="submit"
                disabled={!shiftId || !employeeId}
              >
                Assign shift
              </button>
            </form>

            <form
              className="workflow-form"
              onSubmit={(event) =>
                createZone(event).catch((error) =>
                  setMessage(
                    error instanceof Error
                      ? error.message
                      : 'Unable to save work zone',
                  ),
                )
              }
            >
              <label>
                Work zone
                <input
                  value={zoneName}
                  onChange={(event) =>
                    setZoneName(event.target.value)
                  }
                  required
                />
              </label>

              <label>
                Latitude
                <input
                  type="number"
                  min="-90"
                  max="90"
                  step="any"
                  value={latitude}
                  onChange={(event) =>
                    setLatitude(event.target.value)
                  }
                  required
                />
              </label>

              <label>
                Longitude
                <input
                  type="number"
                  min="-180"
                  max="180"
                  step="any"
                  value={longitude}
                  onChange={(event) =>
                    setLongitude(event.target.value)
                  }
                  required
                />
              </label>

              <label>
                Radius (m)
                <input
                  type="number"
                  min="10"
                  max="5000"
                  value={radius}
                  onChange={(event) =>
                    setRadius(event.target.value)
                  }
                  required
                />
              </label>

              <button className="secondary-btn" type="submit">
                Save geofence
              </button>
            </form>
          </div>
        )}

        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>In</th>
                <th>Out</th>
                <th>Hours</th>
                <th>Late</th>
                <th>Overtime</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              {records.map((record) => (
                <tr key={record.id}>
                  <td>{record.work_date}</td>
                  <td>{record.check_in_time || '—'}</td>
                  <td>{record.check_out_time || '—'}</td>
                  <td>
                    {(record.working_minutes / 60).toFixed(1)}
                  </td>
                  <td>{record.late_minutes} min</td>
                  <td>{record.overtime_minutes} min</td>
                  <td>
                    <span
                      className={`status-badge ${record.status}`}
                    >
                      {record.status.replaceAll('_', ' ')}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!records.length && (
          <p className="muted">No attendance records yet.</p>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h3>Regularization requests</h3>
        </div>

        {!isReviewer && (
          <form
            className="workflow-form"
            onSubmit={(event) =>
              submitRegularization(event).catch((error) =>
                setMessage(
                  error instanceof Error
                    ? error.message
                    : 'Unable to submit request',
                ),
              )
            }
          >
            <label>
              Attendance date
              <input
                type="date"
                value={dateValue}
                onChange={(event) =>
                  setDateValue(event.target.value)
                }
                required
              />
            </label>

            <label>
              Reason
              <input
                value={reason}
                onChange={(event) =>
                  setReason(event.target.value)
                }
                placeholder="Explain the correction"
                required
              />
            </label>

            <button className="secondary-btn" type="submit">
              Submit request
            </button>
          </form>
        )}

        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Reason</th>
                <th>Status</th>
                {isReviewer && <th>Review</th>}
              </tr>
            </thead>

            <tbody>
              {requests.map((item) => (
                <tr key={item.id}>
                  <td>{item.work_date}</td>
                  <td>{item.reason}</td>
                  <td>{item.status}</td>

                  {isReviewer && (
                    <td>
                      {item.status === 'pending' && (
                        <div className="row-actions">
                          <button
                            className="text-btn"
                            type="button"
                            onClick={() =>
                              decide(item.id, 'approved').catch(
                                (error) =>
                                  setMessage(
                                    error instanceof Error
                                      ? error.message
                                      : 'Unable to approve request',
                                  ),
                              )
                            }
                          >
                            Approve
                          </button>

                          <button
                            className="text-btn danger"
                            type="button"
                            onClick={() =>
                              decide(item.id, 'rejected').catch(
                                (error) =>
                                  setMessage(
                                    error instanceof Error
                                      ? error.message
                                      : 'Unable to reject request',
                                  ),
                              )
                            }
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!requests.length && (
          <p className="muted">
            No regularization requests.
          </p>
        )}
      </section>
    </div>
  )
}