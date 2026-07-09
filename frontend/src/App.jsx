import { useState, useEffect } from 'react'
import { logout, getUsernameFromToken } from './api'
import Login from './pages/Login'
import Sync from './pages/Sync'
import Data from './pages/Data'
import Profiling from './pages/Profiling'
import Navbar from './components/Navbar'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('teamsec_token'))
  const [tab, setTab]   = useState('sync')

  // Token süresi dolarsa veya 401 gelirse otomatik çıkış
  useEffect(() => {
    const handleUnauth = () => setToken(null)
    window.addEventListener('unauthorized', handleUnauth)
    return () => window.removeEventListener('unauthorized', handleUnauth)
  }, [])

  if (!token) {
    return <Login onLogin={() => setToken(localStorage.getItem('teamsec_token'))} />
  }

  const handleLogout = () => {
    logout()
    setToken(null)
  }

  return (
    <div className="app">
      <Navbar
        username={getUsernameFromToken()}
        activeTab={tab}
        setActiveTab={setTab}
        onLogout={handleLogout}
      />
      <main className="main">
        {tab === 'sync'      && <Sync />}
        {tab === 'data'      && <Data />}
        {tab === 'profiling' && <Profiling />}
      </main>
    </div>
  )
}
