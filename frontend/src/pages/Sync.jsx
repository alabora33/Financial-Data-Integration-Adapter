import { useState, useRef } from 'react'
import { triggerSync, uploadCSV } from '../api'

const BANKS = ['BANK001', 'BANK002', 'BANK003']
const TYPES = ['RETAIL', 'COMMERCIAL']
const KINDS = ['credit', 'payment_plan']

export default function Sync() {
  const [bank,    setBank]    = useState('BANK001')
  const [type,    setType]    = useState('RETAIL')
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)
  const [error,   setError]   = useState('')

  // Upload state
  const [uBank,    setUBank]    = useState('BANK001')
  const [uType,    setUType]    = useState('RETAIL')
  const [uKind,    setUKind]    = useState('credit')
  const [uLoading, setULoading] = useState(false)
  const [uResult,  setUResult]  = useState(null)
  const [uError,   setUError]   = useState('')
  const fileRef = useRef(null)

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

  const upload = async () => {
    const file = fileRef.current?.files?.[0]
    if (!file) { setUError('Lütfen bir CSV dosyası seçin.'); return }
    setULoading(true)
    setUResult(null)
    setUError('')
    try {
      const data = await uploadCSV(uBank, uType, uKind, file)
      setUResult(data)
      fileRef.current.value = ''
    } catch (err) {
      if (err.message !== 'UNAUTHORIZED') setUError(err.message || 'Yükleme başarısız.')
    } finally {
      setULoading(false)
    }
  }

  return (
    <div>
      <div className="ph">
        <h2>Veri Senkronizasyonu</h2>
        <p>CSV yükleme ve senkronizasyon işlemleri.</p>
      </div>

      {/* ── CSV Upload ── */}
      <div className="card">
        <div className="card-title">CSV Yükleme (Banka Simülatörü)</div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Banka</label>
            <select className="form-select" value={uBank} onChange={e => setUBank(e.target.value)}>
              {BANKS.map(b => <option key={b}>{b}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Kredi Tipi</label>
            <select className="form-select" value={uType} onChange={e => setUType(e.target.value)}>
              {TYPES.map(t => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Veri Türü</label>
            <select className="form-select" value={uKind} onChange={e => setUKind(e.target.value)}>
              {KINDS.map(k => <option key={k}>{k}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">CSV Dosyası</label>
            <input ref={fileRef} type="file" accept=".csv" className="form-select" style={{ padding: '5px 8px' }} />
          </div>
          <button className="btn btn-primary" onClick={upload} disabled={uLoading}>
            {uLoading ? 'Yükleniyor…' : 'Yükle'}
          </button>
        </div>
        {uError  && <div className="alert alert-error" style={{ marginTop: 10 }}>{uError}</div>}
        {uResult && (
          <div className="alert alert-success" style={{ marginTop: 10 }}>
            Yükleme başarılı — <strong>{uResult.row_count?.toLocaleString()}</strong> satır ·{' '}
            {uResult.tenant_id} / {uResult.loan_type} / {uResult.data_kind}
          </div>
        )}
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
          {result.kredi?.warning ? (
            <div className="alert alert-error">
              ⚠️ <strong>Eski veri korundu:</strong> {result.kredi.warning}
            </div>
          ) : (
            <div className="alert alert-success">
              Senkronizasyon tamamlandı —{' '}
              <strong>{result.kredi?.rows_fetched?.toLocaleString() ?? 0}</strong> kredi,{' '}
              <strong>{result.odeme_plani?.rows_fetched?.toLocaleString() ?? 0}</strong> ödeme planı satırı işlendi.
            </div>
          )}

          {}
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

          {result.kredi?.ornek_hatalar?.length > 0 && (
            <div className="card" style={{ borderLeft: '3px solid #ef4444', marginBottom: 16 }}>
              <div className="card-title" style={{ color: '#ef4444' }}>Örnek Doğrulama Hataları (ilk {result.kredi.ornek_hatalar.length})</div>
              {result.kredi.ornek_hatalar.map((h, i) => (
                <div key={i} style={{ fontFamily: 'monospace', fontSize: 12, padding: '3px 0', color: 'var(--muted)', borderBottom: '1px solid var(--border)' }}>{h}</div>
              ))}
            </div>
          )}

          {}
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
