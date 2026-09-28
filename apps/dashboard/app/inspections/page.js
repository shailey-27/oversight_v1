'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { RefreshCw, ClipboardList, MapPin, Calendar, User } from 'lucide-react'
import Sidebar from '@/components/Sidebar'
import { getMyInspections } from '@/lib/api'

function StatusPill({ status }) {
  return <span className={`status-pill ${status}`}>{status.replace('_', ' ')}</span>
}

function TypeBadge({ type }) {
  const colors = {
    physical: { bg: 'var(--accent-dim)', color: 'var(--accent-light)' },
    surprise_video: { bg: 'rgba(245,158,11,0.1)', color: 'var(--medium)' },
    routine: { bg: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)' },
    follow_up: { bg: 'rgba(16,185,129,0.1)', color: 'var(--low)' },
  }
  const style = colors[type] || colors.routine
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 4,
      fontSize: 11, fontWeight: 600, background: style.bg, color: style.color
    }}>
      {type.replace('_', ' ').toUpperCase()}
    </span>
  )
}

export default function InspectionsPage() {
  const router = useRouter()
  const [inspections, setInspections] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('ALL')

  useEffect(() => {
    fetchInspections()
  }, [])

  async function fetchInspections() {
    setLoading(true)
    try {
      const res = await getMyInspections()
      setInspections(res.data)
    } catch { } finally { setLoading(false) }
  }

  const filtered = inspections.filter(i =>
    filter === 'ALL' || i.status === filter
  )

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-container">

          <div className="page-header">
            <div className="page-header-row">
              <div>
                <h1>Inspections</h1>
                <p>All assigned and scheduled inspections across institutions</p>
              </div>
              <button id="refresh-inspections" className="btn btn-ghost" onClick={fetchInspections}>
                <RefreshCw size={15} /> Refresh
              </button>
            </div>
          </div>

          {/* Filter chips */}
          <div className="filter-bar" style={{ marginBottom: 20 }}>
            {['ALL', 'scheduled', 'in_progress', 'submitted', 'reviewed', 'closed'].map(s => (
              <button
                key={s}
                id={`filter-status-${s}`}
                className={`filter-chip ${filter === s ? 'active' : ''}`}
                onClick={() => setFilter(s)}
              >
                {s === 'ALL' ? 'All' : s.replace('_', ' ')}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="loading-container"><div className="spinner" /></div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon"><ClipboardList size={48} opacity={0.3} /></div>
              <div>No inspections found.</div>
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Institution</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Scheduled For</th>
                    <th>Trigger Reason</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(insp => (
                    <tr key={insp.id} id={`insp-row-${insp.id}`}>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 13 }}>
                          {insp.institution_id.slice(0, 8)}...
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          ID: {insp.id.slice(0, 12)}...
                        </div>
                      </td>
                      <td><TypeBadge type={insp.inspection_type} /></td>
                      <td><StatusPill status={insp.status} /></td>
                      <td>
                        <div style={{ fontSize: 12, fontFamily: 'JetBrains Mono', color: 'var(--text-secondary)' }}>
                          {insp.scheduled_for
                            ? new Date(insp.scheduled_for).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
                            : '—'}
                        </div>
                      </td>
                      <td style={{ maxWidth: 200 }}>
                        <div className="truncate text-sm text-secondary" title={insp.trigger_reason}>
                          {insp.trigger_reason || '—'}
                        </div>
                      </td>
                      <td>
                        <button
                          id={`view-insp-${insp.id}`}
                          className="btn btn-ghost btn-sm"
                          onClick={() => router.push(`/institution/${insp.institution_id}`)}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
