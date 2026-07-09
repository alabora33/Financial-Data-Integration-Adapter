import { useState } from 'react'
import { getData } from '../api'

const BANKS = ['BANK001', 'BANK002', 'BANK003']
const TYPES = ['RETAIL', 'COMMERCIAL']
const PAGE_SIZE = 50

function currency(n) {
  if (n == null) return '—'
  return Number(n).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function StatusBadge({ code }) {
  const cls = code === 'A' ? 'badge-green' : code === 'K' ? 'badge-gray' : 'badge-red'
  return <span className={`badge ${cls}`}>{code}</span>
}

function Pagination({ page, pages, onPage }) {
  const nums = []
  for (let p = Math.max(1, page - 2); p <= Math.min(pages, page + 2); p++) nums.push(p)

  return (
    <div className="pagination">
      <button className="pg-btn" onClick={() => onPage(page - 1)} disabled={page === 1}>‹</button>
      {nums[0] > 1 && <>
        <button className="pg-btn" onClick={() => onPage(1)}>1</button>
        {nums[0] > 2 && <span className="dotdot">…</span>}
      </>}
      {nums.map(p => (
        <button key={p} className={`pg-btn${p === page ? ' active' : ''}`} onClick={() => onPage(p)}>{p}</button>
      ))}
      {nums[nums.length - 1] < pages && <>
        {nums[nums.length - 1] < pages - 1 && <span className="dotdot">…</span>}
        <button className="pg-btn" onClick={() => onPage(pages)}>{pages}</button>
      </>}
      <button className="pg-btn" onClick={() => onPage(page + 1)} disabled={page === pages}>›</button>
    </div>
  )
}

export default function Data() {
  const [bank,    setBank]    = useState('BANK001')
  const [type,    setType]    = useState('RETAIL')
  const [page,    setPage]    = useState(1)
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)
  const [error,   setError]   = useState('')

  const load = async (p = 1) => {
    setLoading(true)
    setError('')
    try {
      const data = await getData(bank, type, p, PAGE_SIZE)
      setResult(data)
      setPage(p)
    } catch (err) {
      if (err.message !== 'UNAUTHORIZED') setError(err.message || 'Veri alınamadı.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="ph">
        <h2>Kredi Verileri</h2>
        <p>Veri ambarındaki normalize edilmiş kredi kayıtları.</p>
      </div>

      <div className="card">
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Banka</label>
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
          <button className="btn btn-primary" onClick={() => load(1)} disabled={loading}>
            {loading ? 'Yükleniyor…' : 'Getir'}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading && !result && (
        <div className="loading"><div className="spinner"/><span>Veriler yükleniyor…</span></div>
      )}

      {!loading && !result && !error && (
        <div className="loading" style={{color:'var(--muted-2)'}}>
          <svg width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" style={{opacity:.35}}>
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M3 9h18M3 15h18M9 3v18"/>
          </svg>
          <span>Banka ve kredi tipini seçip <strong>Getir</strong>'e basın.</span>
        </div>
      )}

      {result && (
        <div className="card" style={{ padding: 0, position:'relative' }}>
          {loading && (
            <div style={{position:'absolute',inset:0,background:'rgba(255,255,255,.7)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:2,borderRadius:'var(--r)'}}>
              <div className="spinner"/>
            </div>
          )}
          <div className="tbl-meta">
            <span>Toplam <strong>{result.total?.toLocaleString()}</strong> kayıt</span>
            <span>Sayfa {page} / {result.pages?.toLocaleString()}</span>
          </div>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Hesap No</th>
                  <th>Müşteri</th>
                  <th>Tip</th>
                  <th>Durum</th>
                  <th>Başlangıç</th>
                  <th>Vade</th>
                  <th style={{ textAlign: 'right' }}>Anapara (₺)</th>
                  <th style={{ textAlign: 'right' }}>Kalan (₺)</th>
                  <th style={{ textAlign: 'right' }}>Faiz %</th>
                  <th style={{ textAlign: 'center' }}>Taksit</th>
                </tr>
              </thead>
              <tbody>
                {result.data.map(r => (
                  <tr key={r.id}>
                    <td className="mono">{r.loan_account_number}</td>
                    <td className="mono">{r.customer_id}</td>
                    <td><StatusBadge code={r.customer_type} /></td>
                    <td><StatusBadge code={r.loan_status_code} /></td>
                    <td>{r.loan_start_date}</td>
                    <td>{r.final_maturity_date}</td>
                    <td style={{ textAlign: 'right' }}>{currency(r.original_loan_amount)}</td>
                    <td style={{ textAlign: 'right' }}>{currency(r.outstanding_principal_balance)}</td>
                    <td style={{ textAlign: 'right' }}>%{Number(r.nominal_interest_rate).toFixed(2)}</td>
                    <td style={{ textAlign: 'center' }}>{r.paid_installment_count}/{r.total_installment_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pages={result.pages} onPage={load} />
        </div>
      )}
    </div>
  )
}
