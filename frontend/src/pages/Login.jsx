import { useState } from 'react'
import { login as apiLogin, register as apiRegister } from '../api'

export default function Login({ onLogin }) {
  const [mode, setMode]         = useState('login') // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm,  setConfirm]  = useState('')
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const [success,  setSuccess]  = useState('')

  const reset = (m) => { setMode(m); setError(''); setSuccess(''); setPassword(''); setConfirm('') }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (mode === 'register') {
      if (password !== confirm) { setError('Şifreler eşleşmiyor.'); return }
      if (password.length < 6)  { setError('Şifre en az 6 karakter olmalı.'); return }
      setLoading(true)
      try {
        await apiRegister(username, password)
        setSuccess('Kayıt başarılı! Giriş yapabilirsiniz.')
        setMode('login')
        setPassword('')
        setConfirm('')
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
      return
    }

    setLoading(true)
    try {
      await apiLogin(username, password)
      onLogin()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-box">
        <div className="login-logo">
          <div className="login-logo-icon">T</div>
          <h1>TeamSec <span>Adapter</span></h1>
          <p>Finansal Veri Entegrasyon Portalı</p>
        </div>

        <div className="login-tabs">
          <button className={`login-tab${mode === 'login' ? ' active' : ''}`} onClick={() => reset('login')} type="button">
            Giriş Yap
          </button>
          <button className={`login-tab${mode === 'register' ? ' active' : ''}`} onClick={() => reset('register')} type="button">
            Kayıt Ol
          </button>
        </div>

        <form onSubmit={submit}>
          <div className="login-field">
            <label>Kullanıcı Adı</label>
            <input
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder={mode === 'login' ? 'admin' : 'kullanici_adi'}
              autoComplete="username"
              required
            />
          </div>
          <div className="login-field">
            <label>Şifre</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={mode === 'register' ? 'En az 6 karakter' : ''}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              required
            />
          </div>
          {mode === 'register' && (
            <div className="login-field">
              <label>Şifre Tekrar</label>
              <input
                type="password"
                value={confirm}
                onChange={e => setConfirm(e.target.value)}
                placeholder="Şifreyi tekrar girin"
                autoComplete="new-password"
                required
              />
            </div>
          )}

          {error   && <div className="login-msg err">{error}</div>}
          {success && <div className="login-msg ok">{success}</div>}

          <button className="login-btn" disabled={loading}>
            {loading ? (mode === 'login' ? 'Giriş yapılıyor…' : 'Kaydediliyor…') : (mode === 'login' ? 'Giriş Yap' : 'Hesap Oluştur')}
          </button>
        </form>

        {mode === 'login' && (
          <p className="login-hint">
            Demo: <strong>admin / admin</strong> &nbsp;·&nbsp; <strong>readonly / readonly</strong>
          </p>
        )}
        {mode === 'register' && (
          <p className="login-hint">
            Kayıtlı hesaplar <strong>reader</strong> rolüyle tüm verileri görüntüleyebilir.
          </p>
        )}
      </div>
    </div>
  )
}
