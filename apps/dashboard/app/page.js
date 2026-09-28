'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Moon, Sun, Shield, Activity, Users, Lock, ChevronRight } from 'lucide-react'

export default function Home() {
  const router = useRouter()
  const [theme, setTheme] = useState('dark')

  useEffect(() => {
    // Check saved theme
    const saved = localStorage.getItem('theme') || 'dark'
    setTheme(saved)
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light')
    else document.documentElement.removeAttribute('data-theme')
  }, [])

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    localStorage.setItem('theme', newTheme)
    if (newTheme === 'light') {
      document.documentElement.setAttribute('data-theme', 'light')
    } else {
      document.documentElement.removeAttribute('data-theme')
    }
  }

  return (
    <div className="landing-container">
      {/* Header */}
      <header className="landing-header">
        <div className="logo-section">
          <div className="logo-icon-large"><Shield size={24} /></div>
          <div>
            <h1 className="logo-text">OVERSIGHT</h1>
            <div className="logo-sub">Inspection & Governance</div>
          </div>
        </div>
        
        <div className="header-actions">
          <button onClick={toggleTheme} className="theme-toggle" aria-label="Toggle Theme">
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <Link href="/login" className="btn btn-ghost">Login</Link>
          <Link href="/register" className="btn btn-primary">Sign Up / Register</Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="landing-main">
        <div className="hero-content">
          <h2 className="hero-title">
            The Next Generation of <span className="text-highlight">Monitoring</span>
          </h2>
          <p className="hero-description">
            Oversight provides enterprise-grade, real-time surveillance and compliance tracking. 
            Empowering institutions to detect anomalies, track activities, and secure operations 
            with precision data analytics.
          </p>
          <div className="hero-buttons">
            <Link href="/register" className="btn btn-primary btn-lg">
              Get Started <ChevronRight size={18} />
            </Link>
            <Link href="/dashboard" className="btn btn-ghost btn-lg">
              View Dashboard
            </Link>
          </div>
        </div>

        {/* Features Row */}
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon"><Activity size={24} /></div>
            <h3>Real-Time Analytics</h3>
            <p>Monitor millions of data points instantly with low-latency updates and critical alerts.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon"><Users size={24} /></div>
            <h3>Multi-User Access</h3>
            <p>Role-based access control ensuring the right data reaches the right personnel securely.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon"><Lock size={24} /></div>
            <h3>Bank-Grade Security</h3>
            <p>End-to-end encryption with advanced Aadhaar-verified identity management.</p>
          </div>
        </div>
      </main>

      {/* Animated Sine Waves Bottom */}
      <div className="wave-container">
        <svg className="waves" xmlns="http://www.w3.org/2000/svg" xmlnsXlink="http://www.w3.org/1999/xlink" viewBox="0 24 150 28" preserveAspectRatio="none" shapeRendering="auto">
          <defs>
            <path id="gentle-wave" d="M-160 44c30 0 58-18 88-18s 58 18 88 18 58-18 88-18 58 18 88 18 v44h-352z" />
          </defs>
          <g className="parallax">
            <use xlinkHref="#gentle-wave" x="48" y="0" fill="rgba(234, 179, 8, 0.2)" />
            <use xlinkHref="#gentle-wave" x="48" y="3" fill="rgba(234, 179, 8, 0.4)" />
            <use xlinkHref="#gentle-wave" x="48" y="5" fill="rgba(234, 179, 8, 0.1)" />
            <use xlinkHref="#gentle-wave" x="48" y="7" fill="rgba(234, 179, 8, 0.6)" />
          </g>
        </svg>
      </div>

      <style jsx>{`
        .landing-container {
          min-height: 100vh;
          background-color: var(--bg-base);
          background-image: radial-gradient(rgba(234, 179, 8, 0.2) 1px, transparent 1px);
          background-size: 24px 24px;
          background-position: 0 0, 12px 12px;
          display: flex;
          flex-direction: column;
          position: relative;
          overflow: hidden;
        }

        .landing-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 24px 48px;
          position: relative;
          z-index: 10;
          animation: fadeDown 0.8s ease-out;
        }

        .logo-section {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .logo-icon-large {
          width: 48px; height: 48px;
          background: var(--accent);
          border-radius: 12px;
          display: flex; align-items: center; justify-content: center;
          box-shadow: var(--accent-glow);
          color: var(--bg-base);
        }

        .header-actions {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .theme-toggle {
          background: var(--bg-card);
          border: 1px solid var(--border);
          color: var(--text-primary);
          width: 40px; height: 40px;
          border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          cursor: pointer;
          transition: all var(--t-fast);
        }

        .theme-toggle:hover {
          background: var(--accent-dim);
          border-color: var(--border-accent);
          color: var(--accent-light);
          transform: rotate(15deg) scale(1.1);
        }

        .landing-main {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 60px 24px;
          position: relative;
          z-index: 10;
        }

        .hero-content {
          text-align: center;
          max-width: 800px;
          margin-bottom: 80px;
          animation: fadeUp 1s ease-out 0.2s both;
        }

        .hero-title {
          font-size: 56px;
          font-weight: 800;
          color: var(--text-primary);
          line-height: 1.1;
          margin-bottom: 24px;
          letter-spacing: -0.02em;
        }

        .text-highlight {
          background: linear-gradient(135deg, #facc15 0%, #f97316 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          position: relative;
        }

        .hero-description {
          font-size: 18px;
          color: var(--text-secondary);
          line-height: 1.6;
          margin-bottom: 40px;
          max-width: 600px;
          margin-left: auto;
          margin-right: auto;
        }

        .hero-buttons {
          display: flex;
          gap: 16px;
          justify-content: center;
        }

        .btn-primary:hover, .btn-ghost:hover {
          transform: translateY(-2px) scale(1.02);
        }

        .features-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 24px;
          width: 100%;
          max-width: 1100px;
          animation: fadeUp 1s ease-out 0.4s both;
        }

        .feature-card {
          background: rgba(234, 179, 8, 0.05);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid var(--accent);
          box-shadow: 0 0 15px rgba(234, 179, 8, 0.15), inset 0 0 10px rgba(234, 179, 8, 0.05);
          border-radius: 16px;
          padding: 32px;
          transition: transform var(--t-base), box-shadow var(--t-base);
        }
        
        [data-theme='light'] .feature-card {
          background: rgba(234, 179, 8, 0.08);
          border: 1px solid var(--accent);
          box-shadow: 0 0 15px rgba(234, 179, 8, 0.3), inset 0 0 10px rgba(234, 179, 8, 0.1);
        }

        .feature-card:hover {
          transform: translateY(-8px) scale(1.02);
          box-shadow: 0 10px 30px rgba(234, 179, 8, 0.4), inset 0 0 15px rgba(234, 179, 8, 0.15);
        }

        .feature-icon {
          width: 48px; height: 48px;
          background: var(--accent-dim);
          color: var(--accent-light);
          border-radius: 12px;
          display: flex; align-items: center; justify-content: center;
          margin-bottom: 20px;
          border: 1px solid var(--border-accent);
          transition: transform var(--t-base);
        }

        .feature-card:hover .feature-icon {
          transform: scale(1.1) rotate(5deg);
        }

        .feature-card h3 {
          font-size: 20px;
          color: var(--text-primary);
          margin-bottom: 12px;
        }

        .feature-card p {
          color: var(--text-secondary);
          font-size: 14px;
          line-height: 1.6;
        }

        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(30px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes fadeDown {
          from { opacity: 0; transform: translateY(-30px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .wave-container {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 100%;
          height: 15vh;
          min-height: 100px;
          max-height: 150px;
          z-index: 1;
          pointer-events: none;
        }

        .waves {
          position: relative;
          width: 100%;
          height: 100%;
          margin-bottom: -7px;
        }

        .parallax > use {
          animation: move-forever 25s cubic-bezier(.55,.5,.45,.5) infinite;
        }
        .parallax > use:nth-child(1) {
          animation-delay: -2s;
          animation-duration: 7s;
        }
        .parallax > use:nth-child(2) {
          animation-delay: -3s;
          animation-duration: 10s;
        }
        .parallax > use:nth-child(3) {
          animation-delay: -4s;
          animation-duration: 13s;
        }
        .parallax > use:nth-child(4) {
          animation-delay: -5s;
          animation-duration: 20s;
        }

        @keyframes move-forever {
          0% { transform: translate3d(-90px,0,0); }
          100% { transform: translate3d(85px,0,0); }
        }
      `}</style>
    </div>
  )
}
