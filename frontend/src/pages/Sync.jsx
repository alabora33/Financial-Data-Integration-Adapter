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
            {loading && <span className="spinner" style={{width:14,height:14,borderWidth:2}} />}
            {loading ? 'Senkronize ediliyor…' : 'Senkronize Et'}
          </button>
        </div>
        {loading && (
          <div style={{marginTop:12,fontSize:12,color:'var(--muted)',display:'flex',alignItems:'center',gap:6}}>
            <span style={{color:'var(--accent)'}}>&#9432;</span>
            Senkronizasyon birkaç dakika sürebilir — lütfen sayfayı kapatmayın.
          </div>
        )}
      </div>

      {error  && <div className="alert alert-error">{error}</div>}

      {result && (() => {
        const k = result.kredi ?? {}
        const p = result.odeme_plani ?? {}
        const hasWarning = k.warning || p.warning
        return (
          <div className="sync-result">
            <div className="sync-result-hd">
              {hasWarning
                ? <span style={{color:'var(--amber)'}}>⚠ Senkronizasyon tamamlandı — uyarı var</span>
                : <><span style={{fontSize:18}}>✓</span> Senkronizasyon başarılı</>}
              <span style={{marginLeft:'auto',fontSize:12,fontWeight:400,color:'var(--muted)'}}>
                {result.bank_code} · {result.loan_type}
              </span>
            </div>

            <div className="sync-section">
              <div className="sync-section-title">Kredi Kayıtları</div>
              <div className="sync-metrics">
                <div className="sync-metric">
                  <span className="sync-metric-val neutral">{k.rows_fetched?.toLocaleString() ?? 0}</span>
                  <span className="sync-metric-lbl">Çekilen</span>
                </div>
                <div className="sync-metric">
                  <span className="sync-metric-val good">{k.rows_valid?.toLocaleString() ?? 0}</span>
                  <span className="sync-metric-lbl">Geçerli</span>
                </div>
                <div className="sync-metric">
                  <span className="sync-metric-val bad">{k.rows_invalid?.toLocaleString() ?? 0}</span>
                  <span className="sync-metric-lbl">Hatalı</span>
                </div>
                <div className="sync-metric">
                  <span className="sync-metric-val neutral">{k.rows_deleted_before_sync?.toLocaleString() ?? 0}</span>
                  <span className="sync-metric-lbl">Silinen (önceki)</span>
                </div>
              </div>
              {k.warning && <div className="sync-warning">⚠ {k.warning}</div>}
              {k.ornek_hatalar?.length > 0 && (
                <div style={{marginTop:10}}>
                  <div style={{fontSize:11,fontWeight:700,textTransform:'uppercase',letterSpacing:'.4px',color:'var(--red)',marginBottom:6}}>Örnek Hatalar</div>
                  {k.ornek_hatalar.map((h,i)=>(
                    <div key={i} style={{fontFamily:'monospace',fontSize:12,color:'var(--muted)',padding:'2px 0',borderBottom:'1px solid #f1f5f9'}}>{h}</div>
                  ))}
                </div>
              )}
            </div>

            <div className="sync-section">
              <div className="sync-section-title">Ödeme Planları</div>
              <div className="sync-metrics">
                <div className="sync-metric">
                  <span className="sync-metric-val neutral">{p.rows_fetched?.toLocaleString() ?? 0}</span>
                  <span className="sync-metric-lbl">Çekilen</span>
                </div>
                <div className="sync-metric">
                  <span className="sync-metric-val good">{p.rows_valid?.toLocaleString() ?? 0}</span>
                  <span className="sync-metric-lbl">Geçerli</span>
                </div>
                <div className="sync-metric">
                  <span className="sync-metric-val bad">{p.rows_invalid_field?.toLocaleString() ?? 0}</span>
                  <span className="sync-metric-lbl">Alan Hatası</span>
                </div>
                <div className="sync-metric">
                  <span className="sync-metric-val bad">{p.rows_invalid_cross?.toLocaleString() ?? 0}</span>
                  <span className="sync-metric-lbl">Çapraz Hata</span>
                </div>
              </div>
              {p.warning && <div className="sync-warning">⚠ {p.warning}</div>}
            </div>
          </div>
        )
      })()}
    </div>
  )
}
