'use client'
import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import {
  RefreshCw, TrendingUp, AlertTriangle,
  Building2, ClipboardList, Search
} from 'lucide-react'
import Sidebar from '@/components/Sidebar'
import { getDashboardOverview } from '@/lib/api'

// ── Risk helpers ──────────────────────────────────────────────
function getRiskColor(risk) {
  return { CRITICAL: 'var(--critical)', HIGH: 'var(--high)', MEDIUM: 'var(--medium)', LOW: 'var(--low)' }[risk] || 'var(--text-muted)'
}

function ScoreCircle({ score, risk }) {
  const color = getRiskColor(risk)
  const r = 26, cx = 32, cy = 32
  const circumference = 2 * Math.PI * r
  const filled = (score / 10) * circumference
  const dash = `${filled} ${circumference}`

  return (
    <div className="score-circle">
      <svg width="64" height="64">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="5"
          strokeDasharray={dash} strokeLinecap="round"
          style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%', transition: 'stroke-dasharray 0.8s ease' }}
        />
      </svg>
      <div className="score-circle-text">
        <div className="score-number" style={{ color }}>{score.toFixed(1)}</div>
        <div className="score-max">/10</div>
      </div>
    </div>
  )
}

function RiskBadge({ risk }) {
  const dots = { CRITICAL: '🔴', HIGH: '🟠', MEDIUM: '🟡', LOW: '🟢' }
  return (
    <span className={`risk-badge ${risk}`}>
      <span className="risk-dot" />
      {risk}
    </span>
  )
}

function InstitutionCard({ inst, onView, onTriggerCall, onAssign }) {
  const risk = inst.risk_level
  return (
    <div
      className={`institution-card risk-${risk.toLowerCase()}`}
      onClick={() => onView(inst.id)}
      id={`inst-card-${inst.id}`}
    >
      <div className="card-header">
        <div>
          <div className="card-title">{inst.name}</div>
          <div className="card-meta">📍 {inst.district}, {inst.state} · {inst.institution_type}</div>
        </div>
        <RiskBadge risk={risk} />
      </div>

      <div className="score-row">
        <ScoreCircle score={inst.priority_score} risk={risk} />
        <div className="score-info">
          <div className="score-label">Inspection Priority Score</div>
          <div className="progress-bar" style={{ marginBottom: 6 }}>
            <div
              className="progress-fill"
              style={{ width: `${(inst.priority_score / 10) * 100}%`, background: getRiskColor(risk) }}
            />
          </div>
          <div className="text-xs text-muted">
            Updated {inst.last_score_updated
              ? new Date(inst.last_score_updated).toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' })
              : 'Never'}
          </div>
        </div>
      </div>

      <div className="card-actions" onClick={e => e.stopPropagation()}>
        <button id={`view-${inst.id}`} className="btn btn-ghost btn-sm" onClick={() => onView(inst.id)}>
          View Details
        </button>
        {(risk === 'HIGH' || risk === 'CRITICAL') && (
          <>
            <button id={`call-${inst.id}`} className="btn btn-warning btn-sm" onClick={() => onTriggerCall(inst)}>
              📹 Video Call
            </button>
            <button id={`assign-${inst.id}`} className="btn btn-danger btn-sm" onClick={() => onAssign(inst)}>
              🔍 Inspect
            </button>
          </>
        )}
      </div>
    </div>
  )
}

// ── Main Dashboard Page ───────────────────────────────────────
export default function DashboardPage() {
  const router = useRouter()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('ALL')
  const [wsStatus, setWsStatus] = useState('connecting')
  const [liveAlerts, setLiveAlerts] = useState([])
  const [incomingCall, setIncomingCall] = useState(null)
  const [currentUser, setCurrentUser] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const res = await getDashboardOverview()
      setData(res.data)
      setError('')
    } catch (err) {
      if (err.response?.status === 401) { router.push('/login'); return }
      setError('Cannot reach the API. Make sure the backend is running at localhost:8000')
    } finally { setLoading(false) }
  }, [router])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    const userStr = localStorage.getItem('user')
    if (!token || !userStr) { router.push('/login'); return }
    const user = JSON.parse(userStr)
    setCurrentUser(user)
    
    // NGO Admins do not have access to the official dashboard overview
    if (user.role !== 'ngo_admin') {
      fetchData()
    } else {
      setLoading(false)
    }

    // WebSocket live updates
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/ws/dashboard?token=${token}`
    const ws = new WebSocket(wsUrl)
    ws.onopen = () => setWsStatus('live')
    ws.onclose = () => setWsStatus('offline')
    ws.onerror = () => setWsStatus('offline')
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'SCORE_UPDATE') {
        fetchData() // Refresh dashboard on score change
        setLiveAlerts(prev => [{
          id: Date.now(), institution_id: msg.institution_id,
          text: `Score updated to ${msg.new_score} (${msg.risk_level})`, risk: msg.risk_level
        }, ...prev].slice(0, 3))
      }
      if (msg.type === 'INCOMING_CALL') {
        // For the demo, show the popup to any logged-in NGO Admin, regardless of the specific institution ID
        if (user.role === 'ngo_admin' || user.institution_id === msg.institution_id) {
          setIncomingCall(msg)
        }
      }
      if (msg.type === 'CCTV_UPDATE') {
        setLiveAlerts(prev => [{
          id: Date.now(), institution_id: msg.institution_id,
          text: `CCTV Detected ${msg.estimated_count} people in frame`, risk: 'INFO'
        }, ...prev].slice(0, 3))
      }
    }

    // Auto-refresh every 60s as fallback
    const interval = setInterval(fetchData, 60000)
    return () => { ws.close(); clearInterval(interval) }
  }, [fetchData, router])

  const filtered = data?.institutions?.filter(i => {
    const matchSearch = i.name.toLowerCase().includes(search.toLowerCase()) ||
      (i.district || '').toLowerCase().includes(search.toLowerCase())
    const matchFilter = filter === 'ALL' || i.risk_level === filter
    return matchSearch && matchFilter
  }) || []

  function handleTriggerCall(inst) {
    router.push(`/institution/${inst.id}?action=call`)
  }
  function handleAssign(inst) {
    router.push(`/institution/${inst.id}?action=inspect`)
  }

  if (loading) return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <div className="loading-container" style={{ minHeight: '100vh' }}>
          <div className="spinner" />
          <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Loading dashboard...</div>
        </div>
      </main>
    </div>
  )

  return (
    <div className="app-layout">
      <Sidebar highRiskCount={(data?.high_risk_count || 0)} />
      <main className="main-content">
        <div className="page-container">

          {/* Live Alerts */}
          {liveAlerts.map(alert => (
            <div key={alert.id} className={`alert-banner ${alert.risk === 'CRITICAL' ? 'critical' : 'info'}`}>
              <AlertTriangle size={16} />
              <span><strong>Live Update:</strong> {alert.text}</span>
            </div>
          ))}

          {error && (
            <div className="alert-banner critical">
              <AlertTriangle size={16} />
              <span>{error}</span>
            </div>
          )}

          {/* Header */}
          <div className="page-header">
            <div className="page-header-row">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                  <h1 style={{ margin: 0 }}>Monitoring Dashboard</h1>
                  <span className={`live-indicator`}>
                    <span className={`live-dot`} style={{ background: wsStatus === 'live' ? 'var(--low)' : 'var(--text-muted)' }} />
                    {wsStatus === 'live' ? 'Live' : 'Offline'}
                  </span>
                </div>
                <p>Real-time inspection priority scores across all funded institutions</p>
              </div>
              <button id="refresh-btn" className="btn btn-ghost" onClick={fetchData}>
                <RefreshCw size={15} /> Refresh
              </button>
            </div>
          </div>

          {/* Stats */}
          {data && (
            <div className="stats-grid">
              <div className="stat-card blue">
                <div className="stat-icon" style={{ background: 'var(--accent-dim)', color: 'var(--accent-light)' }}>
                  <Building2 size={20} />
                </div>
                <div className="stat-value">{data.total_institutions}</div>
                <div className="stat-label">Total Institutions</div>
              </div>
              <div className="stat-card critical">
                <div className="stat-icon" style={{ background: 'var(--critical-dim)', color: 'var(--critical)' }}>
                  <AlertTriangle size={20} />
                </div>
                <div className="stat-value" style={{ color: 'var(--critical)' }}>{data.high_risk_count}</div>
                <div className="stat-label">High Risk Institutions</div>
                <div className="stat-trend">Require immediate attention</div>
              </div>
              <div className="stat-card medium">
                <div className="stat-icon" style={{ background: 'var(--medium-dim)', color: 'var(--medium)' }}>
                  <TrendingUp size={20} />
                </div>
                <div className="stat-value" style={{ color: 'var(--medium)' }}>{data.medium_risk_count}</div>
                <div className="stat-label">Medium Risk</div>
              </div>
              <div className="stat-card low">
                <div className="stat-icon" style={{ background: 'var(--low-dim)', color: 'var(--low)' }}>
                  <Building2 size={20} />
                </div>
                <div className="stat-value" style={{ color: 'var(--low)' }}>{data.low_risk_count}</div>
                <div className="stat-label">Low Risk</div>
              </div>
              <div className="stat-card blue">
                <div className="stat-icon" style={{ background: 'var(--accent-dim)', color: 'var(--accent-light)' }}>
                  <ClipboardList size={20} />
                </div>
                <div className="stat-value">{data.active_inspections}</div>
                <div className="stat-label">Active Inspections</div>
              </div>
            </div>
          )}

          {/* Filter Bar */}
          <div className="filter-bar">
            <div className="search-box">
              <Search size={15} className="search-icon" />
              <input
                id="search-institutions"
                type="text"
                placeholder="Search institutions or districts..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(f => (
              <button
                key={f}
                id={`filter-${f.toLowerCase()}`}
                className={`filter-chip ${filter === f ? 'active' : ''}`}
                onClick={() => setFilter(f)}
              >
                {f === 'ALL' ? 'All Institutions' : f}
              </button>
            ))}
          </div>

          {/* Institutions Grid */}
          <div style={{ marginBottom: 8, fontSize: 12, color: 'var(--text-muted)' }}>
            Showing {filtered.length} of {data?.total_institutions || 0} institutions
            {filter !== 'ALL' && ` · Filtered by ${filter}`}
          </div>

          <div className="institutions-grid">
            {filtered.map(inst => (
              <InstitutionCard
                key={inst.id}
                inst={inst}
                onView={id => router.push(`/institution/${id}`)}
                onTriggerCall={handleTriggerCall}
                onAssign={handleAssign}
              />
            ))}
          </div>

          {filtered.length === 0 && !loading && (
            <div className="empty-state">
              <div className="empty-state-icon">🏢</div>
              <div>No institutions found matching your filters.</div>
              <button className="btn btn-ghost btn-sm" style={{ marginTop: 12 }} onClick={() => { setSearch(''); setFilter('ALL') }}>
                Clear filters
              </button>
            </div>
          )}

          {/* Incoming Call Popup */}
          {incomingCall && (
            <div style={{
              position: 'fixed', bottom: 40, right: 40, width: 340, background: 'var(--critical)',
              borderRadius: 16, padding: 24, boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
              border: '2px solid rgba(255,255,255,0.2)', zIndex: 9999,
              animation: 'pulse 1.5s infinite'
            }}>
              <style>{`@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); } 70% { box-shadow: 0 0 0 20px rgba(239, 68, 68, 0); } 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); } }`}</style>
              <h3 style={{ margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: 8, color: '#fff' }}>
                <AlertTriangle size={24} /> INCOMING SURPRISE CALL
              </h3>
              <p style={{ margin: '0 0 20px 0', fontSize: 14, color: 'rgba(255,255,255,0.9)', lineHeight: 1.5 }}>
                <strong>{incomingCall.caller_name}</strong> from DoSJE has initiated a surprise video verification.
              </p>
              <div style={{ display: 'flex', gap: 10 }}>
                <button 
                  onClick={() => router.push(`/dashboard/calls/${incomingCall.room_name}`)}
                  style={{ flex: 1, padding: '10px', background: '#fff', color: 'var(--critical)', border: 'none', borderRadius: 8, fontWeight: 'bold', cursor: 'pointer' }}
                >
                  Accept Call
                </button>
                <button 
                  onClick={() => setIncomingCall(null)}
                  style={{ flex: 1, padding: '10px', background: 'rgba(0,0,0,0.2)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 8, cursor: 'pointer' }}
                >
                  Decline
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
