'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams, useSearchParams } from 'next/navigation'
import {
  ArrowLeft, RefreshCw, Phone, ClipboardList,
  AlertTriangle, TrendingUp, Calendar, CheckCircle
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine
} from 'recharts'
import Sidebar from '@/components/Sidebar'
import { getPriorityScore, computeScore, assignInspection, initiateVideoCall } from '@/lib/api'

function getRiskColor(risk) {
  return { CRITICAL: 'var(--critical)', HIGH: 'var(--high)', MEDIUM: 'var(--medium)', LOW: 'var(--low)' }[risk] || 'var(--text-muted)'
}

function FactorBar({ factor }) {
  const color = factor.raw_score > 0.6 ? 'var(--critical)'
    : factor.raw_score > 0.3 ? 'var(--medium)' : 'var(--low)'
  const pct = Math.round(factor.raw_score * 100)

  return (
    <div className="factor-item">
      <div className="factor-header">
        <div className="factor-name">{factor.label}</div>
        <div className="factor-score" style={{ color }}>
          {pct}% <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>risk · ×{factor.weight}</span>
        </div>
      </div>
      <div className="factor-weight-bar">
        <div
          className="factor-weight-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <div className="factor-label">{factor.explanation}</div>
    </div>
  )
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const score = payload[0].value
  const risk = score >= 8 ? 'CRITICAL' : score >= 6 ? 'HIGH' : score >= 3 ? 'MEDIUM' : 'LOW'
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 10, padding: '10px 14px', fontSize: 12
    }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      <div style={{ color: getRiskColor(risk), fontWeight: 700, fontSize: 18, fontFamily: 'JetBrains Mono' }}>
        {score.toFixed(1)}
      </div>
      <div style={{ color: getRiskColor(risk), fontSize: 11 }}>{risk}</div>
    </div>
  )
}

export default function InstitutionDetailPage() {
  const router = useRouter()
  const params = useParams()
  const searchParams = useSearchParams()
  const { id } = params
  const action = searchParams.get('action')

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [computing, setComputing] = useState(false)
  const [assigning, setAssigning] = useState(false)
  const [calling, setCalling] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')

  useEffect(() => {
    fetchScore()
    if (action === 'call') setTimeout(() => handleVideoCall(), 800)
    if (action === 'inspect') setTimeout(() => handleAssign(), 800)
  }, [id])

  async function fetchScore() {
    setLoading(true)
    try {
      const res = await getPriorityScore(id)
      setData(res.data)
    } catch (err) {
      setError('Failed to load institution data.')
    } finally { setLoading(false) }
  }

  async function handleRecompute() {
    setComputing(true)
    try {
      await computeScore(id)
      await fetchScore()
      setSuccessMsg('Score recomputed successfully!')
      setTimeout(() => setSuccessMsg(''), 3000)
    } catch { setError('Failed to recompute score.') }
    finally { setComputing(false) }
  }

  async function handleAssign() {
    setAssigning(true)
    try {
      const res = await assignInspection({
        institution_id: id,
        inspection_type: 'physical',
        urgency: data?.priority_score >= 8 ? 'immediate' : 'within_48h',
        trigger_reason: `Score ${data?.priority_score}/10 triggered inspection.`
      })
      setSuccessMsg(`✅ Inspector auto-assigned: ${res.data.assigned_inspector?.name || 'assigned'}. Inspection ID: ${res.data.inspection_id.slice(0, 8)}...`)
      setTimeout(() => setSuccessMsg(''), 6000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to assign inspection.')
    } finally { setAssigning(false) }
  }

  async function handleVideoCall() {
    setCalling(true)
    try {
      const res = await initiateVideoCall({ institution_id: id, target_user_ids: [] })
      setSuccessMsg(`📹 Surprise video call initiated! Connecting to secure room...`)
      // Redirect the official straight to the video call page
      setTimeout(() => router.push(res.data.join_url), 1000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to initiate video call.')
    } finally { setCalling(false) }
  }

  if (loading) return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <div className="loading-container" style={{ minHeight: '100vh' }}>
          <div className="spinner" />
        </div>
      </main>
    </div>
  )

  if (!data) return null

  const riskColor = getRiskColor(data.risk_level)

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-container">

          {/* Breadcrumb */}
          <div className="breadcrumb">
            <button onClick={() => router.push('/dashboard')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <ArrowLeft size={14} /> Dashboard
            </button>
            <span className="breadcrumb-sep">›</span>
            <span className="breadcrumb-current">{data.institution_name}</span>
          </div>

          {/* Alerts */}
          {error && <div className="alert-banner critical"><AlertTriangle size={16}/> {error}</div>}
          {successMsg && <div className="alert-banner info"><CheckCircle size={16}/> {successMsg}</div>}

          {/* Header */}
          <div className="page-header">
            <div className="page-header-row">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                  <h1 style={{ margin: 0 }}>{data.institution_name}</h1>
                  <span className={`risk-badge ${data.risk_level}`}>
                    <span className="risk-dot" />
                    {data.risk_level} RISK
                  </span>
                </div>
                <p>📍 {data.district}, {data.state}</p>
              </div>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button id="recompute-btn" className="btn btn-ghost" onClick={handleRecompute} disabled={computing}>
                  <RefreshCw size={14} className={computing ? 'spin' : ''} />
                  {computing ? 'Computing...' : 'Recompute Score'}
                </button>
                <button id="video-call-btn" className="btn btn-warning" onClick={handleVideoCall} disabled={calling}>
                  <Phone size={14} />
                  {calling ? 'Initiating...' : '📹 Surprise Call'}
                </button>
                <button id="assign-inspection-btn" className="btn btn-danger" onClick={handleAssign} disabled={assigning}>
                  <ClipboardList size={14} />
                  {assigning ? 'Assigning...' : '🔍 Assign Inspection'}
                </button>
              </div>
            </div>
          </div>

          <div className="detail-grid">
            {/* Left Column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

              {/* Score Summary Card */}
              <div className="card">
                <div className="card-title-row">
                  <div className="section-title">Inspection Priority Score</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    v1 Rule-Based · Last updated {data.computed_at ? new Date(data.computed_at).toLocaleString('en-IN') : 'Never'}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 20 }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 56, fontWeight: 900, color: riskColor, fontFamily: 'JetBrains Mono', lineHeight: 1 }}>
                      {data.priority_score.toFixed(1)}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>out of 10.0</div>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: 8, padding: 14 }}>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6, fontWeight: 600 }}>
                        Recommended Action
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.5 }}>
                        {data.recommended_action}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="progress-bar" style={{ height: 8, borderRadius: 4 }}>
                  <div
                    className="progress-fill"
                    style={{ width: `${(data.priority_score / 10) * 100}%`, background: riskColor, height: '100%' }}
                  />
                </div>
              </div>

              {/* Explainable Factors */}
              <div className="card">
                <div className="card-title-row">
                  <div className="section-title">⚖️ Score Factor Breakdown</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>AI advisory — human review required</div>
                </div>
                <div className="factor-list">
                  {(data.factors || []).map((f, i) => (
                    <FactorBar key={i} factor={f} />
                  ))}
                </div>
              </div>

              {/* Score History Chart */}
              {data.history?.length > 1 && (
                <div className="card">
                  <div className="card-title-row">
                    <div className="section-title">📈 Score Trend (Last 14 days)</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Risk threshold lines shown</div>
                  </div>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={data.history} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                      <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickLine={false} />
                      <YAxis domain={[0, 10]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickLine={false} />
                      <Tooltip content={<CustomTooltip />} />
                      <ReferenceLine y={6} stroke="var(--high)" strokeDasharray="4 4" strokeOpacity={0.5} label={{ value: 'HIGH', position: 'right', fill: 'var(--high)', fontSize: 10 }} />
                      <ReferenceLine y={8} stroke="var(--critical)" strokeDasharray="4 4" strokeOpacity={0.5} label={{ value: 'CRIT', position: 'right', fill: 'var(--critical)', fontSize: 10 }} />
                      <Line
                        type="monotone" dataKey="score" stroke={riskColor}
                        strokeWidth={2.5} dot={{ fill: riskColor, r: 4, strokeWidth: 2, stroke: 'var(--bg-card)' }}
                        activeDot={{ r: 6 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Right Column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

              {/* Quick Actions */}
              <div className="card" style={{ borderColor: data.risk_level === 'CRITICAL' ? 'rgba(239,68,68,0.3)' : 'var(--border)' }}>
                <div className="section-title" style={{ marginBottom: 16 }}>⚡ Quick Actions</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <button id="qa-video-call" className="btn btn-warning w-full" onClick={handleVideoCall} disabled={calling}>
                    <Phone size={15} />
                    {calling ? 'Initiating call...' : 'Initiate Surprise Video Call'}
                  </button>
                  <button id="qa-physical-inspect" className="btn btn-danger w-full" onClick={handleAssign} disabled={assigning}>
                    <ClipboardList size={15} />
                    {assigning ? 'Assigning inspector...' : 'Assign Physical Inspection'}
                  </button>
                  <button id="qa-followup" className="btn btn-ghost w-full" onClick={() => {
                    assignInspection({ institution_id: id, inspection_type: 'follow_up', urgency: 'within_48h', trigger_reason: 'Manual follow-up inspection.' })
                      .then(() => setSuccessMsg('Follow-up inspection scheduled.'))
                  }}>
                    <Calendar size={15} />
                    Schedule Follow-up
                  </button>
                </div>
              </div>

              {/* Score Breakdown Legend */}
              <div className="card">
                <div className="section-title" style={{ marginBottom: 16 }}>📊 Scoring Weights</div>
                {[
                  { name: 'Attendance vs Reported', weight: '30%' },
                  { name: 'CCTV vs App Check-ins', weight: '30%' },
                  { name: 'Invoice Anomaly', weight: '20%' },
                  { name: 'Historical Pattern', weight: '10%' },
                  { name: 'Call Compliance', weight: '10%' },
                ].map((w, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: i < 4 ? '1px solid var(--border)' : 'none' }}>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{w.name}</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent-light)', fontFamily: 'JetBrains Mono' }}>{w.weight}</div>
                  </div>
                ))}
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 12, padding: '10px', background: 'rgba(255,255,255,0.03)', borderRadius: 8, lineHeight: 1.5 }}>
                  ⚠️ AI advisory only — all flags require human official review before any compliance action.
                </div>
              </div>

              {/* Compliance History Preview */}
              <div className="card">
                <div className="card-title-row" style={{ marginBottom: 16 }}>
                  <div className="section-title">📋 Recent Events</div>
                  <button className="btn btn-ghost btn-sm" onClick={() => router.push('/compliance')}>
                    View All
                  </button>
                </div>
                <div className="timeline">
                  {[
                    { title: 'Score Spike Detected', desc: 'Priority score reached 8.5 (CRITICAL)', date: 'Today · 09:15 AM', adverse: true },
                    { title: 'Invoice Flagged', desc: 'Duplicate document hash on INV-2026-0091', date: '2 days ago', adverse: true },
                    { title: 'Routine Check', desc: 'Monthly score computed: 6.8 (HIGH)', date: '7 days ago', adverse: false },
                  ].map((ev, i) => (
                    <div key={i} className="timeline-item">
                      <div className={`timeline-dot ${ev.adverse ? 'adverse' : 'normal'}`} />
                      <div className="timeline-content">
                        <div className="timeline-title">{ev.title}</div>
                        <div className="timeline-desc">{ev.desc}</div>
                        <div className="timeline-date">{ev.date}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
