import { useEffect, useState } from 'react'
import type { UserSummary } from '../types'
import { apiFetch } from '../lib/api'

interface NotificationsPageProps {
  user: UserSummary | null
}

interface NotificationItem {
  id: string
  title?: string | null
  message?: string | null
  type?: string | null
  is_read?: boolean
  created_at?: string | null
}

export default function NotificationsPage({
  user,
}: NotificationsPageProps) {
  const [notifications, setNotifications] = useState<
    NotificationItem[]
  >([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadNotifications = async () => {
    try {
      setLoading(true)
      setError('')

      const data = await apiFetch<NotificationItem[]>(
        '/notifications',
      )

      setNotifications(data)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load notifications.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadNotifications()
  }, [])

  const markAsRead = async (id: string) => {
    try {
      await apiFetch(`/notifications/${id}/read`, {
        method: 'PATCH',
      })

      setNotifications((current) =>
        current.map((notification) =>
          notification.id === id
            ? { ...notification, is_read: true }
            : notification,
        ),
      )
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to mark notification as read.',
      )
    }
  }

  const unreadCount = notifications.filter(
    (notification) => !notification.is_read,
  ).length

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="eyebrow">MY WORKSPACE</div>
          <h1>Notifications</h1>
          <p>
            Stay updated with important HRMS activities and
            announcements.
          </p>
        </div>

        <button
          className="secondary-btn"
          type="button"
          onClick={loadNotifications}
        >
          Refresh
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="stat-grid">
        <div className="stat-card">
          <span>Total Notifications</span>
          <strong>{notifications.length}</strong>
        </div>

        <div className="stat-card">
          <span>Unread</span>
          <strong>{unreadCount}</strong>
        </div>

        <div className="stat-card">
          <span>Read</span>
          <strong>
            {notifications.length - unreadCount}
          </strong>
        </div>

        <div className="stat-card">
          <span>Account</span>
          <strong>{user?.role || 'Employee'}</strong>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Your Notifications</h2>
            <p>
              Recent updates and actions related to your
              account.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">
            Loading notifications...
          </div>
        ) : notifications.length === 0 ? (
          <div className="empty-state">
            You don't have any notifications.
          </div>
        ) : (
          <div className="action-list">
            {notifications.map((notification) => (
              <div
                className="action-row"
                key={notification.id}
              >
                <div>
                  <div className="employee-cell">
                    <div className="avatar-circle">
                      {(
                        notification.title ||
                        notification.type ||
                        'N'
                      )
                        .charAt(0)
                        .toUpperCase()}
                    </div>

                    <div>
                      <strong>
                        {notification.title ||
                          notification.type ||
                          'Notification'}
                      </strong>

                      <div className="muted">
                        {notification.message ||
                          'No additional details.'}
                      </div>

                      {notification.created_at && (
                        <div className="muted">
                          {new Date(
                            notification.created_at,
                          ).toLocaleString()}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="row-actions">
                  {!notification.is_read && (
                    <>
                      <span className="status-badge warning">
                        Unread
                      </span>

                      <button
                        className="text-btn"
                        type="button"
                        onClick={() =>
                          markAsRead(notification.id)
                        }
                      >
                        Mark as read
                      </button>
                    </>
                  )}

                  {notification.is_read && (
                    <span className="status-badge success">
                      Read
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}