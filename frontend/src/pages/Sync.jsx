import { useState } from 'react'
import { triggerSync } from '../api'

const BANKS = ['BANK001', 'BANK002', 'BANK003']
const TYPES = ['RETAIL', 'COMMERCIAL']

export default function Sync() {
  const [bank,    setBank]    = useState('BANK001')
  const [type,    setType]    = useState('RETAIL')
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)
  const [error,   setError]   = useState('')

  const run = async () => {
    setLoading(true)
    setResult(null)
    setError('')
    try {
      const data = await triggerSync(bank, type)
      setResult(data)
    } catch (err) {
      if (err.message !== 'UNAUTHORIZED') setError(err.message || 'Senkronizasyon başarısız.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="ph">
        <h2>Veri Senkronizasyonu</h2>
        <p>Seçilen bankadan kredi verilerini çekip veri ambarına aktarır.</p>
      </div>

      <div className="card">
        <div className="card-title">Senkronizasyon Parametreleri</div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Banka Kodu</label>
            <select className="form-select" value={bank} onChange={e => setBank(e.target.value)}>
              {BANKS.map(b => <option key={b}>{b}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Kredi Tipi</label>
            <select className="form-select" value={type} onChange={e => setType(e.target.value)}>
              {TYPES.map(t => <option key={t}>{t}</option>)}
            </select>
          </div>
          <button className="btn btn-primary" onClick={run} disabled={loading}>
            {loading ? 'Senkronize ediliyor…' : 'Senkronize Et'}
          </button>
        </div>
      </div>

      {error  && <div className="alert alert-error">{error}</div>}

      {result && (
        <>
          <div className="alert alert-success">
            Senkronizasyon tamamlandı —{' '}
            <strong>{result.kredi?.rows_fetched?.toLocaleString() ?? 0}</strong> kredi,{' '}
            <strong>{result.odeme_plani?.rows_fetched?.toLocaleString() ?? 0}</strong> ödeme planı satırı işlendi.
          </div>

          {/* Kredi istatistikleri */}
          <div className="card-title" style={{ marginBottom: 8, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.5px', color: 'var(--muted)' }}>Kredi Kayıtları</div>
          <div className="stat-grid" style={{ marginBottom: 16 }}>
            <div className="stat-card">
              <div className="stat-label">Toplam Çekilen</div>
              <div className="stat-value">{result.kredi?.rows_fetched?.toLocaleString() ?? 0}</div>
              <div className="stat-sub">{result.bank_code} · {result.loan_type}</div>
            </div>
            <div className="stat-card green">
              <div className="stat-label">Geçerli Kayıt</div>
              <div className="stat-value">{result.kredi?.rows_valid?.toLocaleString() ?? 0}</div>
            </div>
            <div className="stat-card red">
              <div className="stat-label">Hatalı Kayıt</div>
              <div className="stat-value">{result.kredi?.rows_invalid?.toLocaleString() ?? 0}</div>
            </div>
            <div className="stat-card blue">
              <div className="stat-label">Önceki Silinen</div>
              <div className="stat-value">{result.kredi?.rows_deleted_before_sync?.toLocaleString() ?? 0}</div>
            </div>
          </div>

          {/* Ödeme planı istatistikleri */}
          <div className="card-title" style={{ marginBottom: 8, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.5px', color: 'var(--muted)' }}>Ödeme Planları</div>
          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-label">Toplam Çekilen</div>
              <div className="stat-value">{result.odeme_plani?.rows_fetched?.toLocaleString() ?? 0}</div>
            </div>
            <div className="stat-card green">
              <div className="stat-label">Geçerli Plan</div>
              <div className="stat-value">{result.odeme_plani?.rows_valid?.toLocaleString() ?? 0}</div>
            </div>
            <div className="stat-card red">
              <div className="stat-label">Alan Hatası</div>
              <div className="stat-value">{result.odeme_plani?.rows_invalid_field?.toLocaleString() ?? 0}</div>
            </div>
            <div className="stat-card" style={{ borderLeftColor: '#f59e0b' }}>
              <div className="stat-label">Çapraz Hata</div>
              <div className="stat-value">{result.odeme_plani?.rows_invalid_cross?.toLocaleString() ?? 0}</div>
              <div className="stat-sub">Kredisi olmayan plan</div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
