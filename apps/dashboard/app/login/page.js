'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { sendOTP, verifyOTP } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const [phase, setPhase] = useState('phone') // 'phone' | 'otp'
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [demoOtp, setDemoOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSendOTP(e) {
    e.preventDefault()
    if (phone.length !== 10) { setError('Enter a valid 10-digit phone number'); return }
    setLoading(true); setError('')
    try {
      const res = await sendOTP(phone)
      setDemoOtp(res.data.demo_otp || '')
      setPhase('otp')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send OTP. Is the backend running?')
    } finally { setLoading(false) }
  }

  async function handleVerifyOTP(e) {
    e.preventDefault()
    if (otp.length !== 6) { setError('Enter the 6-digit OTP'); return }
    setLoading(true); setError('')
    try {
      const res = await verifyOTP(phone, otp)
      const data = res.data
      if (data.needs_registration) {
        setError('This phone is not registered yet. Ask your admin to create your account.')
        setLoading(false); return
      }
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      router.push('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid OTP. Please try again.')
    } finally { setLoading(false) }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        {/* Logo */}
        <div className="login-logo">
          <div className="login-logo-icon">🛡️</div>
          <div className="login-title">OVERSIGHT</div>
          <div className="login-subtitle">Ministry of Social Justice & Empowerment</div>
        </div>

        {/* Phone Step */}
        {phase === 'phone' && (
          <form onSubmit={handleSendOTP}>
            <div className="form-group">
              <label className="form-label">PHONE NUMBER</label>
              <input
                id="phone-input"
                className="form-input"
                type="tel"
                maxLength={10}
                placeholder="Enter 10-digit phone number"
                value={phone}
                onChange={e => setPhone(e.target.value.replace(/\D/g, ''))}
                autoFocus
              />
            </div>
            {error && <div style={{ color: 'var(--critical)', fontSize: 12, marginBottom: 12 }}>{error}</div>}
            <button id="send-otp-btn" type="submit" className="login-btn-full" disabled={loading}>
              {loading ? '⏳ Sending OTP...' : 'Get OTP →'}
            </button>

            <div className="demo-note">
              <strong>🎯 Demo Accounts:</strong><br/>
              DoSJE Official: <strong>9000000001</strong><br/>
              PMU Inspector: <strong>9000000002</strong><br/>
              NGO Admin: <strong>9000000003</strong><br/>
              <em style={{ color: 'var(--text-muted)' }}>OTP shown in response (DEMO_MODE=True)</em>
            </div>
          </form>
        )}

        {/* OTP Step */}
        {phase === 'otp' && (
          <form onSubmit={handleVerifyOTP}>
            <div style={{ textAlign: 'center', marginBottom: 20 }}>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                OTP sent to <strong style={{ color: 'var(--text-primary)' }}>****{phone.slice(-4)}</strong>
              </div>
              <button
                type="button"
                onClick={() => { setPhase('phone'); setOtp(''); setError('') }}
                style={{ fontSize: 12, color: 'var(--accent-light)', background: 'none', border: 'none', cursor: 'pointer', marginTop: 4 }}
              >
                ← Change number
              </button>
            </div>

            {demoOtp && (
              <div className="demo-note" style={{ marginBottom: 16 }}>
                🔓 <strong>Demo OTP:</strong>{' '}
                <span
                  className="font-mono font-bold"
                  style={{ color: 'var(--accent-light)', fontSize: 20, cursor: 'pointer', letterSpacing: '0.15em' }}
                  onClick={() => setOtp(demoOtp)}
                  title="Click to auto-fill"
                >
                  {demoOtp}
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8 }}>(click to fill)</span>
              </div>
            )}

            <div className="form-group">
              <label className="form-label">ENTER OTP</label>
              <input
                id="otp-input"
                className="form-input otp-input"
                type="text"
                maxLength={6}
                placeholder="_ _ _ _ _ _"
                value={otp}
                onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
                autoFocus
              />
            </div>

            {error && <div style={{ color: 'var(--critical)', fontSize: 12, marginBottom: 12 }}>{error}</div>}

            <button id="verify-otp-btn" type="submit" className="login-btn-full" disabled={loading || otp.length !== 6}>
              {loading ? '⏳ Verifying...' : '✓ Login to OVERSIGHT'}
            </button>
          </form>
        )}

        <div style={{ textAlign: 'center', marginTop: 24, fontSize: 13, color: 'var(--text-secondary)' }}>
          <Link href="/" style={{ color: 'var(--accent-light)', textDecoration: 'underline' }}>
            ← Back to Home
          </Link>
        </div>

        <div style={{ textAlign: 'center', marginTop: 16, fontSize: 11, color: 'var(--text-muted)' }}>
          OVERSIGHT — Inspection & Governance Platform<br/>
          Developed for Portfolio Project
        </div>
      </div>
    </div>
  )
}
