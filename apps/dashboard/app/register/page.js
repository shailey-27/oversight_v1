'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Shield } from 'lucide-react'

export default function RegisterPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    aadhaar: '',
    role: 'official' // official, inspector, admin
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const validateAadhaar = (aadhaar) => {
    return /^[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}$/.test(aadhaar.replace(/\s/g, ''))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (!formData.name) {
      setError('Name is required.')
      return
    }
    if (formData.phone.length !== 10) {
      setError('Enter a valid 10-digit phone number.')
      return
    }
    if (!validateAadhaar(formData.aadhaar)) {
      setError('Enter a valid 12-digit Aadhaar Card number.')
      return
    }

    setLoading(true)

    // Simulate API registration
    setTimeout(() => {
      setLoading(false)
      setSuccess('Registration successful! Admin approval pending.')
      setTimeout(() => {
        router.push('/login')
      }, 2000)
    }, 1500)
  }

  return (
    <div className="login-page">
      <div className="login-card" style={{ maxWidth: 480 }}>
        {/* Logo */}
        <div className="login-logo">
          <div className="login-logo-icon"><Shield size={28} /></div>
          <div className="login-title">OVERSIGHT</div>
          <div className="login-subtitle">Register a new account</div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">FULL NAME</label>
            <input
              name="name"
              className="form-input"
              type="text"
              placeholder="e.g. Ramesh Kumar"
              value={formData.name}
              onChange={handleInputChange}
            />
          </div>

          <div className="form-group">
            <label className="form-label">PHONE NUMBER</label>
            <input
              name="phone"
              className="form-input"
              type="tel"
              maxLength={10}
              placeholder="10-digit phone number"
              value={formData.phone}
              onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value.replace(/\D/g, '') }))}
            />
          </div>

          <div className="form-group">
            <label className="form-label">AADHAAR CARD NUMBER</label>
            <input
              name="aadhaar"
              className="form-input"
              type="text"
              maxLength={14}
              placeholder="0000 0000 0000"
              value={formData.aadhaar}
              onChange={(e) => {
                let val = e.target.value.replace(/\D/g, '')
                val = val.replace(/(.{4})/g, '$1 ').trim()
                setFormData(prev => ({ ...prev, aadhaar: val }))
              }}
            />
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              * 12-digit valid Aadhaar required for identity verification
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">REQUESTED ROLE</label>
            <select
              name="role"
              className="form-input"
              value={formData.role}
              onChange={handleInputChange}
            >
              <option value="official">DoSJE Official (View Only)</option>
              <option value="inspector">PMU Inspector (Field Staff)</option>
              <option value="ngo_admin">NGO Administrator</option>
            </select>
          </div>

          {error && <div style={{ color: 'var(--critical)', fontSize: 13, marginBottom: 16 }}>{error}</div>}
          {success && <div style={{ color: 'var(--low)', fontSize: 13, marginBottom: 16 }}>{success}</div>}

          <button type="submit" className="login-btn-full" disabled={loading}>
            {loading ? '⏳ Registering...' : 'Register Account'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: 24, fontSize: 13, color: 'var(--text-secondary)' }}>
          Already have an account? <Link href="/login" style={{ color: 'var(--accent-light)', textDecoration: 'underline' }}>Login here</Link>
        </div>

        <div style={{ textAlign: 'center', marginTop: 16, fontSize: 13, color: 'var(--text-secondary)' }}>
          <Link href="/" style={{ color: 'var(--accent-light)', textDecoration: 'underline' }}>
            ← Back to Home
          </Link>
        </div>
      </div>
    </div>
  )
}
