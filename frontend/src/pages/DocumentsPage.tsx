import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { UserSummary } from '../types'
import { apiDownload, apiFetch } from '../lib/api'

interface DocumentsPageProps {
  user: UserSummary | null
}

interface EmployeeDocument {
  id: string
  name?: string | null
  category?: string | null
  status?: string | null
  expiry_date?: string | null
  rejection_reason?: string | null
  file_name?: string | null
}

interface DocumentCategory {
  id: string
  name: string
  required: boolean
  active: boolean
}

interface MissingDocument {
  id?: string
  name?: string
  category?: string
  employee_id?: string
  employee_name?: string
}

export default function DocumentsPage({
  user,
}: DocumentsPageProps) {
  const [documents, setDocuments] = useState<EmployeeDocument[]>([])
  const [categories, setCategories] = useState<DocumentCategory[]>([])
  const [missingDocuments, setMissingDocuments] = useState<MissingDocument[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const [showCategoryForm, setShowCategoryForm] = useState(false)
  const [categoryName, setCategoryName] = useState('')
  const [categoryRequired, setCategoryRequired] = useState(false)

  const [activeTab, setActiveTab] = useState<
    'documents' | 'missing' | 'categories'
  >('documents')

  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const canManage =
    user?.role === 'admin' || user?.role === 'hr'

  const loadDocuments = async () => {
    try {
      setLoading(true)
      setError('')

      const [
        documentsResult,
        categoriesResult,
        missingResult,
      ] = await Promise.all([
        apiFetch<EmployeeDocument[]>('/documents'),
        apiFetch<DocumentCategory[]>('/documents/categories'),
        apiFetch<MissingDocument[]>('/documents/missing'),
      ])

      setDocuments(documentsResult)
      setCategories(categoriesResult)
      setMissingDocuments(missingResult)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load documents.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDocuments()
  }, [])

  const uploadDocument = async (event: FormEvent) => {
    event.preventDefault()

    if (!selectedFile) {
      setError('Please select a file.')
      return
    }

    if (!selectedCategory) {
      setError('Please select a document category.')
      return
    }

    try {
      setError('')
      setMessage('')

      const formData = new FormData()

      formData.append('file', selectedFile)
      formData.append('category_id', selectedCategory)

      await apiFetch('/documents', {
        method: 'POST',
        body: formData,
      })

      setSelectedFile(null)
      setSelectedCategory('')

      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }

      setMessage('Document uploaded successfully.')

      await loadDocuments()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to upload document.',
      )
    }
  }

  const createCategory = async (event: FormEvent) => {
    event.preventDefault()

    if (!categoryName.trim()) {
      setError('Please enter a category name.')
      return
    }

    try {
      setError('')
      setMessage('')

      await apiFetch('/documents/categories', {
        method: 'POST',
        body: JSON.stringify({
          name: categoryName.trim(),
          required: categoryRequired,
        }),
      })

      setCategoryName('')
      setCategoryRequired(false)
      setShowCategoryForm(false)

      setMessage('Document category created successfully.')

      await loadDocuments()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to create document category.',
      )
    }
  }

  const toggleCategory = async (
    category: DocumentCategory,
  ) => {
    try {
      setError('')
      setMessage('')

      await apiFetch(
        `/documents/categories/${category.id}`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            active: !category.active,
            required: category.required,
          }),
        },
      )

      setMessage(
        category.active
          ? 'Category deactivated.'
          : 'Category activated.',
      )

      await loadDocuments()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to update category.',
      )
    }
  }

  const downloadDocument = async (
    document: EmployeeDocument,
  ) => {
    try {
      setError('')

      await apiDownload(
        `/documents/${document.id}/download`,
        document.file_name ||
          document.name ||
          'document',
      )
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to download document.',
      )
    }
  }

  const replaceDocument = async (
    document: EmployeeDocument,
    file: File,
  ) => {
    try {
      setError('')
      setMessage('')

      const formData = new FormData()
      formData.append('file', file)

      await apiFetch(
        `/documents/${document.id}/replace`,
        {
          method: 'POST',
          body: formData,
        },
      )

      setMessage('Document replaced successfully.')

      await loadDocuments()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to replace document.',
      )
    }
  }

  const verifyDocument = async (
    document: EmployeeDocument,
    status: 'verified' | 'rejected',
  ) => {
    try {
      setError('')
      setMessage('')

      let rejectionReason: string | undefined

      if (status === 'rejected') {
        rejectionReason =
          window.prompt(
            'Enter the reason for rejection:',
          ) || undefined

        if (!rejectionReason) {
          return
        }
      }

      await apiFetch(
        `/documents/${document.id}/verification`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            status,
            rejection_reason: rejectionReason,
          }),
        },
      )

      setMessage(
        status === 'verified'
          ? 'Document verified.'
          : 'Document rejected.',
      )

      await loadDocuments()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to update document status.',
      )
    }
  }

  const getStatusClass = (status?: string | null) => {
    const value = status?.toLowerCase()

    if (
      value === 'verified' ||
      value === 'approved'
    ) {
      return 'success'
    }

    if (
      value === 'pending' ||
      value === 'submitted'
    ) {
      return 'warning'
    }

    if (
      value === 'rejected' ||
      value === 'expired'
    ) {
      return 'danger'
    }

    return ''
  }

  const verifiedCount = documents.filter(
    (document) =>
      document.status?.toLowerCase() === 'verified' ||
      document.status?.toLowerCase() === 'approved',
  ).length

  const pendingCount = documents.filter(
    (document) =>
      !document.status ||
      document.status.toLowerCase() === 'pending' ||
      document.status.toLowerCase() === 'submitted',
  ).length

  const rejectedCount = documents.filter(
    (document) =>
      document.status?.toLowerCase() === 'rejected' ||
      document.status?.toLowerCase() === 'expired',
  ).length

  const requiredCategories = categories.filter(
    (category) =>
      category.required && category.active,
  ).length

  const activeCategories = categories.filter(
    (category) => category.active,
  ).length

  const verificationPercentage = useMemo(() => {
    if (documents.length === 0) {
      return 0
    }

    return Math.round(
      (verifiedCount / documents.length) * 100,
    )
  }, [documents.length, verifiedCount])

  const recentDocuments = useMemo(
    () => documents.slice(0, 5),
    [documents],
  )

  const cards = [
    {
      label: 'Total Documents',
      value: documents.length,
      icon: '▱',
      description: 'Documents submitted',
    },
    {
      label: 'Verified',
      value: verifiedCount,
      icon: '✓',
      description: `${verificationPercentage}% verified`,
    },
    {
      label: 'Pending',
      value: pendingCount,
      icon: '◷',
      description: 'Awaiting verification',
    },
    {
      label: 'Rejected',
      value: rejectedCount,
      icon: '!',
      description: 'Requires attention',
    },
  ]

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="eyebrow">
            DOCUMENT MANAGEMENT
          </div>

          <h1>Documents</h1>

          <p>
            Upload, review, verify, and manage employee
            documents.
          </p>
        </div>

        <button
          className="secondary-btn"
          type="button"
          onClick={loadDocuments}
          disabled={loading}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="error-box">
          {error}
        </div>
      )}

      {message && (
        <div className="inline-message success">
          {message}
        </div>
      )}

      {loading ? (
        <div className="panel">
          <div className="empty-state">
            Loading document information...
          </div>
        </div>
      ) : (
        <>
          <div className="documents-dashboard-container">
            <div className="documents-dashboard-heading">
              <div>
                <div className="dashboard-label">
                  DOCUMENT OVERVIEW
                </div>

                <h2>
                  Employee documents
                </h2>

                <p>
                  Welcome back, {user?.first_name || 'there'}. Here is
                  the current document management overview.
                </p>
              </div>
            </div>

            <div className="documents-kpi-grid">
              {cards.map((card) => (
                <div
                  className="documents-kpi-card"
                  key={card.label}
                >
                  <div className="documents-kpi-top">
                    <span className="documents-kpi-icon">
                      {card.icon}
                    </span>

                    <span>{card.label}</span>
                  </div>

                  <strong>{card.value}</strong>

                  <small>{card.description}</small>
                </div>
              ))}
            </div>

            <div className="documents-dashboard-grid">
              <section className="documents-dashboard-card">
                <div className="documents-card-header">
                  <div>
                    <h3>Verification Status</h3>
                    <p>
                      Current document verification progress.
                    </p>
                  </div>
                </div>

                <div className="documents-status-list">
                  <div className="documents-status-row">
                    <div className="documents-status-label">
                      <span className="documents-status-dot verified" />
                      <span>Verified</span>
                    </div>

                    <div className="documents-status-value">
                      <strong>{verifiedCount}</strong>
                      <small>
                        {verificationPercentage}%
                      </small>
                    </div>
                  </div>

                  <div className="documents-progress">
                    <div
                      className="documents-progress-bar verified"
                      style={{
                        width: `${verificationPercentage}%`,
                      }}
                    />
                  </div>

                  <div className="documents-status-row">
                    <div className="documents-status-label">
                      <span className="documents-status-dot pending" />
                      <span>Pending</span>
                    </div>

                    <div className="documents-status-value">
                      <strong>{pendingCount}</strong>
                    </div>
                  </div>

                  <div className="documents-status-row">
                    <div className="documents-status-label">
                      <span className="documents-status-dot rejected" />
                      <span>Rejected / Expired</span>
                    </div>

                    <div className="documents-status-value">
                      <strong>{rejectedCount}</strong>
                    </div>
                  </div>
                </div>
              </section>

              <section className="documents-dashboard-card">
                <div className="documents-card-header">
                  <div>
                    <h3>Document Snapshot</h3>
                    <p>
                      Key information about document configuration.
                    </p>
                  </div>
                </div>

                <div className="documents-snapshot-list">
                  <div className="documents-snapshot-row">
                    <span>Active categories</span>
                    <strong>{activeCategories}</strong>
                  </div>

                  <div className="documents-snapshot-row">
                    <span>Required categories</span>
                    <strong>{requiredCategories}</strong>
                  </div>

                  <div className="documents-snapshot-row">
                    <span>Missing documents</span>
                    <strong>{missingDocuments.length}</strong>
                  </div>

                  <div className="documents-snapshot-row">
                    <span>Verification rate</span>
                    <strong>
                      {verificationPercentage}%
                    </strong>
                  </div>
                </div>
              </section>
            </div>

            <section className="documents-dashboard-card">
              <div className="documents-card-header">
                <div>
                  <h3>Recent Documents</h3>
                  <p>
                    Latest documents associated with employee profiles.
                  </p>
                </div>
              </div>

              {recentDocuments.length === 0 ? (
                <div className="documents-dashboard-empty">
                  No documents have been uploaded yet.
                </div>
              ) : (
                <div className="documents-recent-list">
                  {recentDocuments.map((document) => (
                    <div
                      className="documents-recent-row"
                      key={document.id}
                    >
                      <div className="documents-recent-main">
                        <strong>
                          {document.name ||
                            document.file_name ||
                            'Document'}
                        </strong>

                        <span>
                          {document.category || 'Uncategorized'}
                        </span>
                      </div>

                      <div className="documents-recent-right">
                        <span
                          className={`status-badge ${getStatusClass(
                            document.status,
                          )}`}
                        >
                          {document.status || 'Pending'}
                        </span>

                        <span>
                          {document.expiry_date
                            ? `Expires ${document.expiry_date}`
                            : 'No expiry'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>

          <div className="panel">
            <div className="toolbar">
              <div className="segmented-control">
                <button
                  type="button"
                  className={
                    activeTab === 'documents'
                      ? 'active'
                      : ''
                  }
                  onClick={() =>
                    setActiveTab('documents')
                  }
                >
                  Documents
                </button>

                <button
                  type="button"
                  className={
                    activeTab === 'missing'
                      ? 'active'
                      : ''
                  }
                  onClick={() =>
                    setActiveTab('missing')
                  }
                >
                  Missing
                  {missingDocuments.length > 0 && (
                    <span className="tab-count">
                      {missingDocuments.length}
                    </span>
                  )}
                </button>

                {canManage && (
                  <button
                    type="button"
                    className={
                      activeTab === 'categories'
                        ? 'active'
                        : ''
                    }
                    onClick={() =>
                      setActiveTab('categories')
                    }
                  >
                    Categories
                  </button>
                )}
              </div>
            </div>
          </div>

          {activeTab === 'documents' && (
            <>
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <h2>Upload Document</h2>
                    <p>
                      Upload a document and assign it to a
                      category.
                    </p>
                  </div>
                </div>

                <form
                  className="workflow-form"
                  onSubmit={uploadDocument}
                >
                  <div className="form-section">
                    <div className="form-section-heading">
                      <h3>Document Information</h3>
                      <p>
                        Select the document category and choose
                        the file to upload.
                      </p>
                    </div>

                    <div className="form-grid">
                      <div className="form-field">
                        <label htmlFor="document-category">
                          Document category
                        </label>

                        <select
                          id="document-category"
                          value={selectedCategory}
                          onChange={(event) =>
                            setSelectedCategory(
                              event.target.value,
                            )
                          }
                          required
                        >
                          <option value="">
                            Select category
                          </option>

                          {categories
                            .filter(
                              (category) =>
                                category.active,
                            )
                            .map((category) => (
                              <option
                                key={category.id}
                                value={category.id}
                              >
                                {category.name}
                                {category.required
                                  ? ' • Required'
                                  : ''}
                              </option>
                            ))}
                        </select>
                      </div>

                      <div className="form-field">
                        <label htmlFor="document-file">
                          File
                        </label>

                        <input
                          ref={fileInputRef}
                          id="document-file"
                          type="file"
                          onChange={(event) =>
                            setSelectedFile(
                              event.target.files?.[0] ||
                                null,
                            )
                          }
                          required
                        />

                        <span className="form-hint">
                          {selectedFile
                            ? selectedFile.name
                            : 'Choose the document you want to upload.'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="form-actions">
                    <button
                      className="primary-btn"
                      type="submit"
                    >
                      Upload Document
                    </button>
                  </div>
                </form>
              </div>

              <div className="panel">
                <div className="panel-header">
                  <div>
                    <h2>Uploaded Documents</h2>
                    <p>
                      Documents associated with your employee
                      profile.
                    </p>
                  </div>
                </div>

                {documents.length === 0 ? (
                  <div className="empty-state">
                    No documents have been uploaded yet.
                  </div>
                ) : (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Document</th>
                          <th>Category</th>
                          <th>Status</th>
                          <th>Expiry</th>
                          <th>Actions</th>
                        </tr>
                      </thead>

                      <tbody>
                        {documents.map((document) => (
                          <tr key={document.id}>
                            <td>
                              <strong>
                                {document.name ||
                                  document.file_name ||
                                  'Document'}
                              </strong>

                              {document.file_name &&
                                document.name !==
                                  document.file_name && (
                                  <div className="muted">
                                    {document.file_name}
                                  </div>
                                )}
                            </td>

                            <td>
                              {document.category || '—'}
                            </td>

                            <td>
                              <span
                                className={`status-badge ${getStatusClass(
                                  document.status,
                                )}`}
                              >
                                {document.status ||
                                  'Pending'}
                              </span>

                              {document.rejection_reason && (
                                <div className="muted">
                                  {
                                    document.rejection_reason
                                  }
                                </div>
                              )}
                            </td>

                            <td>
                              {document.expiry_date || '—'}
                            </td>

                            <td>
                              <div className="row-actions">
                                <button
                                  className="text-btn"
                                  type="button"
                                  onClick={() =>
                                    downloadDocument(
                                      document,
                                    )
                                  }
                                >
                                  Download
                                </button>

                                <label className="text-btn">
                                  Replace

                                  <input
                                    type="file"
                                    hidden
                                    onChange={(event) => {
                                      const file =
                                        event.target.files?.[0]

                                      if (file) {
                                        void replaceDocument(
                                          document,
                                          file,
                                        )
                                      }

                                      event.target.value =
                                        ''
                                    }}
                                  />
                                </label>

                                {canManage &&
                                  document.status?.toLowerCase() !==
                                    'verified' && (
                                    <>
                                      <button
                                        className="text-btn"
                                        type="button"
                                        onClick={() =>
                                          verifyDocument(
                                            document,
                                            'verified',
                                          )
                                        }
                                      >
                                        Verify
                                      </button>

                                      <button
                                        className="text-btn danger"
                                        type="button"
                                        onClick={() =>
                                          verifyDocument(
                                            document,
                                            'rejected',
                                          )
                                        }
                                      >
                                        Reject
                                      </button>
                                    </>
                                  )}
                              </div>
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

          {activeTab === 'missing' && (
            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>Missing Documents</h2>
                  <p>
                    Documents that are required but have not
                    yet been submitted.
                  </p>
                </div>
              </div>

              {missingDocuments.length === 0 ? (
                <div className="empty-state">
                  No missing documents found.
                </div>
              ) : (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        {canManage && <th>Employee</th>}
                        <th>Document</th>
                        <th>Category</th>
                      </tr>
                    </thead>

                    <tbody>
                      {missingDocuments.map(
                        (document, index) => (
                          <tr
                            key={
                              document.id ||
                              `${document.employee_id}-${index}`
                            }
                          >
                            {canManage && (
                              <td>
                                {document.employee_name ||
                                  document.employee_id ||
                                  '—'}
                              </td>
                            )}

                            <td>
                              <strong>
                                {document.name ||
                                  'Required document'}
                              </strong>
                            </td>

                            <td>
                              {document.category || '—'}
                            </td>
                          </tr>
                        ),
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {activeTab === 'categories' && canManage && (
            <>
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <h2>Document Categories</h2>
                    <p>
                      Configure the types of documents employees
                      can submit.
                    </p>
                  </div>

                  <button
                    className="primary-btn"
                    type="button"
                    onClick={() =>
                      setShowCategoryForm(
                        (current) => !current,
                      )
                    }
                  >
                    {showCategoryForm
                      ? 'Cancel'
                      : 'Add Category'}
                  </button>
                </div>

                {showCategoryForm && (
                  <form
                    className="workflow-form"
                    onSubmit={createCategory}
                  >
                    <div className="form-section">
                      <div className="form-section-heading">
                        <h3>New Category</h3>
                        <p>
                          Create a document category and define
                          whether it is required.
                        </p>
                      </div>

                      <div className="form-grid">
                        <div className="form-field">
                          <label htmlFor="category-name">
                            Category name
                          </label>

                          <input
                            id="category-name"
                            value={categoryName}
                            onChange={(event) =>
                              setCategoryName(
                                event.target.value,
                              )
                            }
                            placeholder="e.g. Passport"
                            required
                          />
                        </div>

                        <div className="form-field">
                          <label htmlFor="category-required">
                            Requirement
                          </label>

                          <select
                            id="category-required"
                            value={
                              categoryRequired
                                ? 'yes'
                                : 'no'
                            }
                            onChange={(event) =>
                              setCategoryRequired(
                                event.target.value ===
                                  'yes',
                              )
                            }
                          >
                            <option value="no">
                              Optional
                            </option>

                            <option value="yes">
                              Required
                            </option>
                          </select>
                        </div>
                      </div>
                    </div>

                    <div className="form-actions">
                      <button
                        className="primary-btn"
                        type="submit"
                      >
                        Create Category
                      </button>
                    </div>
                  </form>
                )}
              </div>

              <div className="panel">
                <div className="panel-header">
                  <div>
                    <h2>Category Configuration</h2>
                    <p>
                      Manage active and inactive document
                      categories.
                    </p>
                  </div>
                </div>

                {categories.length === 0 ? (
                  <div className="empty-state">
                    No document categories found.
                  </div>
                ) : (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Category</th>
                          <th>Required</th>
                          <th>Status</th>
                          <th>Action</th>
                        </tr>
                      </thead>

                      <tbody>
                        {categories.map((category) => (
                          <tr key={category.id}>
                            <td>
                              <strong>
                                {category.name}
                              </strong>
                            </td>

                            <td>
                              {category.required
                                ? 'Yes'
                                : 'No'}
                            </td>

                            <td>
                              <span
                                className={`status-badge ${
                                  category.active
                                    ? 'success'
                                    : 'danger'
                                }`}
                              >
                                {category.active
                                  ? 'Active'
                                  : 'Inactive'}
                              </span>
                            </td>

                            <td>
                              <button
                                className="text-btn"
                                type="button"
                                onClick={() =>
                                  toggleCategory(
                                    category,
                                  )
                                }
                              >
                                {category.active
                                  ? 'Deactivate'
                                  : 'Activate'}
                              </button>
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
        </>
      )}
    </div>
  )
}