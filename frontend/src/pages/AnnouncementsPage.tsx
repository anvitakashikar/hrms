import {useEffect, useState } from 'react'
import type {FormEvent} from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface AnnouncementsPageProps {
  user: UserSummary | null
}

interface Announcement {
  id: string
  title: string
  content?: string | null
  created_at?: string | null
  published_at?: string | null
  status?: string | null
  author_name?: string | null
}

export default function AnnouncementsPage({
  user,
}: AnnouncementsPageProps) {
  const [announcements, setAnnouncements] = useState<
    Announcement[]
  >([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')

  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')

  const canManage =
    user?.role === 'admin' || user?.role === 'hr'

  const loadAnnouncements = async () => {
    try {
      setLoading(true)
      setMessage('')

      const data = await apiFetch<Announcement[]>(
        '/announcements',
      )

      setAnnouncements(data)
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to load announcements.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAnnouncements()
  }, [])

  const createAnnouncement = async (
    event: FormEvent,
  ) => {
    event.preventDefault()

    try {
      await apiFetch('/announcements', {
        method: 'POST',
        body: JSON.stringify({
          title,
          content,
        }),
      })

      setTitle('')
      setContent('')
      setMessage(
        'Announcement published successfully.',
      )

      await loadAnnouncements()
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to publish announcement.',
      )
    }
  }

  return (
<div className="page announcements-page">
      <div className="page-header">
        <div>
          <div className="eyebrow">COMMUNICATION</div>
          <h1>Announcements</h1>
          <p>
            Share important updates and announcements with
            employees.
          </p>
        </div>

        <button
          className="secondary-btn"
          type="button"
          onClick={loadAnnouncements}
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
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>New Announcement</h2>
              <p>
                Publish an update for the organization.
              </p>
            </div>
          </div>

          <form
            className="form-grid"
            onSubmit={createAnnouncement}
          >
            <label className="full">
              Title
              <input
                value={title}
                onChange={(event) =>
                  setTitle(event.target.value)
                }
                placeholder="Announcement title"
                required
              />
            </label>

            <label className="full">
              Message
              <textarea
                value={content}
                onChange={(event) =>
                  setContent(event.target.value)
                }
                rows={6}
                placeholder="Write your announcement..."
                required
              />
            </label>

            <div className="full">
              <button
                className="primary-btn"
                type="submit"
              >
                Publish Announcement
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Latest Announcements</h2>
            <p>
              Organization-wide updates and notices.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">
            Loading announcements...
          </div>
        ) : announcements.length === 0 ? (
          <div className="empty-state">
            No announcements available.
          </div>
        ) : (
          <div className="action-list">
            {announcements.map((announcement) => (
              <article
                className="action-row"
                key={announcement.id}
              >
                <div>
                  <div className="announcement-heading">
                    <strong>
                      {announcement.title}
                    </strong>

                    {announcement.status && (
                      <span className="status-badge">
                        {announcement.status}
                      </span>
                    )}
                  </div>

                  <p className="announcement-content">
                    {announcement.content || '—'}
                  </p>

                  <div className="muted">
                    {announcement.author_name
                      ? `Posted by ${announcement.author_name}`
                      : 'Organization announcement'}
                    {announcement.published_at ||
                    announcement.created_at
                      ? ` · ${
                          announcement.published_at ||
                          announcement.created_at
                        }`
                      : ''}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}