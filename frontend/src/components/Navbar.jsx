const TABS = [
  {
    id: 'sync',
    label: 'Senkronizasyon',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
      </svg>
    ),
  },
  {
    id: 'data',
    label: 'Kredi Verileri',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <path d="M3 9h18M3 15h18M9 3v18"/>
      </svg>
    ),
  },
  {
    id: 'profiling',
    label: 'Veri Kalitesi',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="18" y1="20" x2="18" y2="10"/>
        <line x1="12" y1="20" x2="12" y2="4"/>
        <line x1="6"  y1="20" x2="6"  y2="14"/>
      </svg>
    ),
  },
]

export default function Navbar({ username, activeTab, setActiveTab, onLogout }) {
  const initials = username ? username.slice(0, 2).toUpperCase() : '?'
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <div className="brand-icon">T</div>
        <span className="brand-text">TeamSec <span>Adapter</span></span>
      </div>
      <div className="navbar-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`nav-tab${activeTab === t.id ? ' active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>
      <div className="navbar-right">
        <div className="user-pill">
          <div className="user-avatar">{initials}</div>
          {username}
        </div>
        <button className="btn-logout" onClick={onLogout}>Çıkış</button>
      </div>
    </nav>
  )
}
