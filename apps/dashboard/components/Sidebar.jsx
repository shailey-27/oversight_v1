'use client'
import { useRouter, usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import {
  LayoutDashboard, Building2, ClipboardList,
  History, Video, LogOut, Bell, Shield, Sun, Moon
} from 'lucide-react'

export default function Sidebar({ highRiskCount = 0 }) {
  const router = useRouter()
  const pathname = usePathname()
  const [user, setUser] = useState(null)
  const [theme, setTheme] = useState('dark')

  useEffect(() => {
    const stored = localStorage.getItem('user')
    if (stored) setUser(JSON.parse(stored))

    const storedTheme = localStorage.getItem('theme') || 'dark'
    setTheme(storedTheme)
    document.documentElement.setAttribute('data-theme', storedTheme)
  }, [])

  function toggleTheme() {
    const newTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    localStorage.setItem('theme', newTheme)
    document.documentElement.setAttribute('data-theme', newTheme)
  }

  function logout() {
    localStorage.clear()
    router.push('/')
  }

  const navItems = [
    { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard', badge: highRiskCount > 0 ? highRiskCount : null },
    { icon: Building2,       label: 'Institutions', href: '/institutions' },
    { icon: ClipboardList,   label: 'Inspections', href: '/inspections' },
    { icon: Video,           label: 'Video Calls', href: '/video-calls' },
    { icon: History,         label: 'Compliance History', href: '/compliance' },
  ]

  const roleLabels = {
    dosje_official: 'DoSJE Official',
    pmu_inspector:  'PMU Inspector',
    ngo_admin:      'NGO Admin',
    beneficiary:    'Beneficiary',
  }

  const initials = user?.full_name?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() || 'U'

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-mark">
          <div className="logo-icon">🛡️</div>
          <div className="logo-text">OVERSIGHT</div>
        </div>
        <div className="logo-sub">Smart Inspection & Governance</div>
      </div>

      {/* User */}
      {user && (
        <div className="sidebar-user">
          <div className="user-avatar">{initials}</div>
          <div className="user-info">
            <div className="user-name">{user.full_name}</div>
            <div className="user-role">{roleLabels[user.role] || user.role}</div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">Navigation</div>
        {navItems.map(item => {
          const Icon = item.icon
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          return (
            <button
              key={item.href}
              id={`nav-${item.label.toLowerCase().replace(/\s/g,'-')}`}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => router.push(item.href)}
            >
              <Icon className="nav-icon" size={18} />
              {item.label}
              {item.badge && <span className="nav-badge">{item.badge}</span>}
            </button>
          )
        })}

        <div className="nav-section-label" style={{ marginTop: 16 }}>System</div>
        <button className="nav-item" onClick={() => {}}>
          <Bell className="nav-icon" size={18} />
          Alerts
        </button>
        <button className="nav-item" onClick={() => {}}>
          <Shield className="nav-icon" size={18} />
          Audit Log
        </button>
        <button className="nav-item" onClick={toggleTheme}>
          {theme === 'dark' ? <Sun className="nav-icon" size={18} /> : <Moon className="nav-icon" size={18} />}
          {theme === 'dark' ? 'Day Mode' : 'Night Mode'}
        </button>
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 8, paddingLeft: 12 }}>
          OVERSIGHT v1.0
        </div>
        <button className="logout-btn" id="logout-btn" onClick={logout}>
          <LogOut size={16} />
          Sign Out
        </button>
      </div>
    </aside>
  )
}
