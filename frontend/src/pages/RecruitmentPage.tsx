import {useEffect, useState } from 'react'
import type {FormEvent} from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface RecruitmentPageProps {
  user: UserSummary | null
}

interface JobOpening {
  id: string
  title: string
  department?: string | null
  location?: string | null
  employment_type?: string | null
  status?: string | null
  description?: string | null
  created_at?: string | null
}

interface Candidate {
  id: string
  name: string
  email: string
  job_title?: string | null
  status?: string | null
  applied_at?: string | null
}

export default function RecruitmentPage({
  user,
}: RecruitmentPageProps) {
  const [jobs, setJobs] = useState<JobOpening[]>([])
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')

  const [title, setTitle] = useState('')
  const [department, setDepartment] = useState('')
  const [location, setLocation] = useState('')
  const [employmentType, setEmploymentType] =
    useState('Full-time')
  const [description, setDescription] = useState('')

  const canManage =
    user?.role === 'admin' || user?.role === 'hr'

  const loadRecruitment = async () => {
    try {
      setLoading(true)
      setMessage('')

      const [jobData, candidateData] = await Promise.all([
        apiFetch<JobOpening[]>('/recruitment/jobs'),
        apiFetch<Candidate[]>('/recruitment/candidates'),
      ])

      setJobs(jobData)
      setCandidates(candidateData)
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to load recruitment data.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRecruitment()
  }, [])

  const createJob = async (event: FormEvent) => {
    event.preventDefault()

    try {
      await apiFetch('/recruitment/jobs', {
        method: 'POST',
        body: JSON.stringify({
          title,
          department: department || null,
          location: location || null,
          employment_type: employmentType,
          description: description || null,
        }),
      })

      setTitle('')
      setDepartment('')
      setLocation('')
      setEmploymentType('Full-time')
      setDescription('')
      setMessage('Job opening created successfully.')

      await loadRecruitment()
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to create job opening.',
      )
    }
  }

  return (
    <div className="page recruitment-page">
      <div className="page-header">
        <div>
          <div className="eyebrow">TALENT</div>
          <h1>Recruitment</h1>
          <p>
            Manage job openings and track candidates.
          </p>
        </div>

        <button
          className="secondary-btn"
          type="button"
          onClick={loadRecruitment}
        >
          Refresh
        </button>
      </div>

      {message && <div className="error-box">{message}</div>}

      {canManage && (
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Create Job Opening</h2>
              <p>
                Add a new position to the recruitment pipeline.
              </p>
            </div>
          </div>

          <form className="form-grid" onSubmit={createJob}>
            <label>
              Job title
              <input
                value={title}
                onChange={(event) =>
                  setTitle(event.target.value)
                }
                placeholder="e.g. Software Engineer"
                required
              />
            </label>

            <label>
              Department
              <input
                value={department}
                onChange={(event) =>
                  setDepartment(event.target.value)
                }
                placeholder="e.g. Engineering"
              />
            </label>

            <label>
              Location
              <input
                value={location}
                onChange={(event) =>
                  setLocation(event.target.value)
                }
                placeholder="e.g. Pune / Remote"
              />
            </label>

            <label>
              Employment type
              <select
                value={employmentType}
                onChange={(event) =>
                  setEmploymentType(event.target.value)
                }
              >
                <option value="Full-time">Full-time</option>
                <option value="Part-time">Part-time</option>
                <option value="Contract">Contract</option>
                <option value="Internship">Internship</option>
              </select>
            </label>

            <label className="full">
              Description
              <textarea
                value={description}
                onChange={(event) =>
                  setDescription(event.target.value)
                }
                rows={6}
                placeholder="Describe the role, responsibilities and requirements..."
              />
            </label>

            <div className="full">
              <button
                className="primary-btn"
                type="submit"
              >
                Create Opening
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="panel">
          <div className="empty-state">
            Loading recruitment data...
          </div>
        </div>
      ) : (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <span>Open Positions</span>
              <strong>
                {
                  jobs.filter(
                    (job) =>
                      !job.status ||
                      job.status.toLowerCase() === 'open',
                  ).length
                }
              </strong>
            </div>

            <div className="stat-card">
              <span>Total Openings</span>
              <strong>{jobs.length}</strong>
            </div>

            <div className="stat-card">
              <span>Candidates</span>
              <strong>{candidates.length}</strong>
            </div>

            <div className="stat-card">
              <span>Active Candidates</span>
              <strong>
                {
                  candidates.filter(
                    (candidate) =>
                      !candidate.status ||
                      !['rejected', 'withdrawn', 'hired'].includes(
                        candidate.status.toLowerCase(),
                      ),
                  ).length
                }
              </strong>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Job Openings</h2>
                <p>Current recruitment positions.</p>
              </div>
            </div>

            {jobs.length === 0 ? (
              <div className="empty-state">
                No job openings available.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Position</th>
                      <th>Department</th>
                      <th>Location</th>
                      <th>Type</th>
                      <th>Status</th>
                    </tr>
                  </thead>

                  <tbody>
                    {jobs.map((job) => (
                      <tr key={job.id}>
                        <td>
                          <strong>{job.title}</strong>

                          {job.description && (
                            <div className="muted">
                              {job.description}
                            </div>
                          )}
                        </td>

                        <td>{job.department || '—'}</td>
                        <td>{job.location || '—'}</td>
                        <td>
                          {job.employment_type || '—'}
                        </td>

                        <td>
                          <span className="status-badge">
                            {job.status || 'Open'}
                          </span>
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
                <h2>Candidates</h2>
                <p>Applicants currently in the pipeline.</p>
              </div>
            </div>

            {candidates.length === 0 ? (
              <div className="empty-state">
                No candidates available.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Candidate</th>
                      <th>Email</th>
                      <th>Position</th>
                      <th>Applied</th>
                      <th>Status</th>
                    </tr>
                  </thead>

                  <tbody>
                    {candidates.map((candidate) => (
                      <tr key={candidate.id}>
                        <td>
                          <strong>{candidate.name}</strong>
                        </td>
                        <td>{candidate.email}</td>
                        <td>{candidate.job_title || '—'}</td>
                        <td>{candidate.applied_at || '—'}</td>
                        <td>
                          <span className="status-badge">
                            {candidate.status || 'Applied'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}