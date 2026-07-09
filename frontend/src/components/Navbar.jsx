const TABS = [
  { id: 'sync',      label: 'Senkronizasyon' },
  { id: 'data',      label: 'Kredi Verileri' },
  { id: 'profiling', label: 'Veri Kalitesi'  },
]

export default function Navbar({ username, activeTab, setActiveTab, onLogout }) {
  return (
    <nav className="navbar">
      <div className="navbar-brand">TeamSec <span>Adapter</span></div>
      <div className="navbar-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`nav-tab${activeTab === t.id ? ' active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="navbar-right">
        <span>{username}</span>
        <button className="btn-logout" onClick={onLogout}>Çıkış</button>
      </div>
    </nav>
  )
}
