import { useState } from 'react'
import { getProfiling } from '../api'

const BANKS = ['BANK001', 'BANK002', 'BANK003']
const TYPES = ['RETAIL', 'COMMERCIAL']

function fmt(n, d = 2) {
  if (n == null) return '—'
  return Number(n).toLocaleString('tr-TR', { minimumFractionDigits: d, maximumFractionDigits: d })
}
function fmtM(n) {
  if (n == null) return '—'
  return (Number(n) / 1_000_000).toFixed(2) + 'M ₺'
}

const PIE_COLORS = ['#3b82f6', '#22c55e', '#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4']

function PieChart({ items }) {
  if (!items || items.length === 0) return null
  const total = items.reduce((s, x) => s + (x.sayi || 0), 0)
  if (total === 0) return null
  const R = 70, hole = 42, cx = 90, cy = 90
  let angle = -Math.PI / 2
  const slices = items.map((item, i) => {
    const pct = item.sayi / total
    const start = angle
    angle += pct * 2 * Math.PI
    return { ...item, pct, start, end: angle, color: PIE_COLORS[i % PIE_COLORS.length] }
  })
  function arc(s) {
    const x1 = cx + R * Math.cos(s.start), y1 = cy + R * Math.sin(s.start)
    const x2 = cx + R * Math.cos(s.end),   y2 = cy + R * Math.sin(s.end)
    const x3 = cx + hole * Math.cos(s.end), y3 = cy + hole * Math.sin(s.end)
    const x4 = cx + hole * Math.cos(s.start), y4 = cy + hole * Math.sin(s.start)
    const lg = s.pct > 0.5 ? 1 : 0
    return `M${x1} ${y1} A${R} ${R} 0 ${lg} 1 ${x2} ${y2} L${x3} ${y3} A${hole} ${hole} 0 ${lg} 0 ${x4} ${y4}Z`
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      <svg width={180} height={180} viewBox="0 0 180 180">
        {slices.map((s, i) => <path key={i} d={arc(s)} fill={s.color} />)}
      </svg>
      <div>
        {slices.map((s, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6, fontSize: 13 }}>
            <div style={{ width: 11, height: 11, borderRadius: 2, background: s.color, flexShrink: 0 }} />
            <span>{s.loan_status_code === 'A' ? 'Aktif' : s.loan_status_code === 'K' ? 'Kapalı' : s.loan_status_code}</span>
            <span style={{ color: 'var(--muted)', marginLeft: 4 }}>{(s.pct * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ProgRow({ label, value, total, bad }) {
  const pct = total > 0 ? Math.min((value / total) * 100, 100) : 0
  return (
    <div className="prog-row">
      <div className="prog-lbl">{label}</div>
      <div className="prog-track">
        <div className={`prog-fill${bad ? ' bad' : ''}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="prog-val">{value?.toLocaleString()}</div>
    </div>
  )
}

export default function Profiling() {
  const [bank,    setBank]    = useState('BANK001')
  const [type,    setType]    = useState('RETAIL')
  const [loading, setLoading] = useState(false)
  const [data,    setData]    = useState(null)
  const [error,   setError]   = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      setData(await getProfiling(bank, type))
    } catch (err) {
      if (err.message !== 'UNAUTHORIZED') setError(err.message || 'Profiling alınamadı.')
    } finally {
      setLoading(false)
    }
  }

  const f = data?.faiz_istatistikleri
  const t = data?.tutar_istatistikleri
  const q = data?.veri_kalitesi

  return (
    <div>
      <div className="ph">
        <h2>Veri Kalitesi Profili</h2>
        <p>Portföy istatistikleri ve veri kalitesi raporu.</p>
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
          <button className="btn btn-primary" onClick={load} disabled={loading}>
            {loading ? 'Analiz ediliyor…' : 'Analiz Et'}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {loading && <div className="loading"><div className="spinner"/><span>Analiz ediliyor…</span></div>}

      {!loading && !data && !error && (
        <div className="loading" style={{color:'var(--muted-2)'}}>
          <svg width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" style={{opacity:.35}}>
            <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
          </svg>
          <span>Banka ve kredi tipini seçip <strong>Analiz Et</strong>'e basın.</span>
        </div>
      )}

      {data && !loading && (
        <>
          {}
          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-label">Toplam Kayıt</div>
              <div className="stat-value">{data.toplam_kayit?.toLocaleString()}</div>
              <div className="stat-sub">{type} · {bank}</div>
            </div>
            <div className="stat-card blue">
              <div className="stat-label">Kullandırılan</div>
              <div className="stat-value">{fmtM(t?.toplam_kullandirilan)}</div>
            </div>
            <div className="stat-card green">
              <div className="stat-label">Kalan Bakiye</div>
              <div className="stat-value">{fmtM(t?.toplam_kalan_bakiye)}</div>
            </div>
            <div className="stat-card amber">
              <div className="stat-label">Ort. Faiz</div>
              <div className="stat-value">%{fmt(f?.ortalama)}</div>
            </div>
          </div>

          <div className="two-col">
            {}
            <div className="card">
              <div className="card-title">Faiz &amp; Tutar İstatistikleri</div>
              <table style={{ width: '100%' }}>
                <tbody>
                  {[
                    ['Faiz — Min',    `%${fmt(f?.min)}`],
                    ['Faiz — Max',    `%${fmt(f?.max)}`],
                    ['Faiz — Ort',    `%${fmt(f?.ortalama)}`],
                    ['Faiz — Std.Sp', f?.stddev != null ? `%${fmt(f.stddev)}` : '—'],
                    ['Tutar — Min',  `${fmt(t?.min)} ₺`],
                    ['Tutar — Max',  `${fmt(t?.max)} ₺`],
                  ].map(([lbl, val]) => (
                    <tr key={lbl}>
                      <td style={{ padding: '7px 0', color: 'var(--muted)', fontSize: '13px' }}>{lbl}</td>
                      <td style={{ padding: '7px 0', textAlign: 'right', fontWeight: '600', fontVariantNumeric: 'tabular-nums' }}>{val}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {}
            <div className="card">
              <div className="card-title">Veri Kalitesi — Eksik Alanlar</div>
              <ProgRow label="Sigorta (boş)"          value={q?.bos_sigorta_alani}     total={data.toplam_kayit} bad={q?.bos_sigorta_oran_pct > 5} />
              <ProgRow label="Dış Rating (boş)"        value={q?.bos_dis_rating}         total={data.toplam_kayit} bad={q?.bos_dis_rating_pct > 5} />
              <ProgRow label="İç Rating (boş)"         value={q?.bos_ic_rating}          total={data.toplam_kayit} bad={q?.bos_ic_rating_pct > 5} />
              <ProgRow label="Müşteri ID (boş)"        value={q?.bos_customer_id}        total={data.toplam_kayit} bad={q?.bos_customer_id_pct > 1} />
              <ProgRow label="Kredi Başl. Tarihi (boş)" value={q?.bos_loan_start_date}   total={data.toplam_kayit} bad={q?.bos_loan_start_date_pct > 5} />
              <ProgRow label="Vade Tarihi (boş)"       value={q?.bos_final_maturity_date} total={data.toplam_kayit} bad={q?.bos_final_maturity_pct > 5} />
              <ProgRow label="Kapanış Tarihi (boş)"    value={q?.bos_loan_closing_date}  total={data.toplam_kayit} bad={false} />
              <ProgRow label="Sıfır Faiz Oranı"        value={q?.sifir_faiz_orani}       total={data.toplam_kayit} bad={q?.sifir_faiz_pct > 10} />
              <ProgRow label="Sıfır Kullandırılan"     value={q?.sifir_original_tutar}   total={data.toplam_kayit} bad={q?.sifir_tutar_pct > 5} />
              <p style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '10px' }}>
                * Kırmızı: eşik aşıldı
              </p>
            </div>
          </div>

          <div className="two-col">
            {}
            <div className="card">
              <div className="card-title">Kredi Durum Dağılımı</div>
              <PieChart items={data.durum_dagilimi} />
              <div style={{ marginTop: 12 }}>
                {data.durum_dagilimi?.map(item => (
                  <div className="dist-row" key={item.loan_status_code}>
                    <span>
                      {item.loan_status_code === 'A' ? 'A — Aktif'
                     : item.loan_status_code === 'K' ? 'K — Kapalı'
                     : item.loan_status_code}
                    </span>
                    <span className="dist-count">{item.sayi?.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>

            {}
            {data.sigorta_dagilimi?.length > 0 && (
              <div className="card">
                <div className="card-title">Sigorta Dağılımı</div>
                {data.sigorta_dagilimi?.map(item => (
                  <div className="dist-row" key={item.insurance_included}>
                    <span>{item.insurance_included === 'E' ? 'E — Sigortalı' : 'H — Sigortasız'}</span>
                    <span className="dist-count">{item.sayi?.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {}
          {data.kategorik_analiz && Object.keys(data.kategorik_analiz).length > 0 && (
            <div className="card">
              <div className="card-title">Kategorik Alan Analizi</div>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)', fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase' }}>
                    <th style={{ padding: '6px 0', textAlign: 'left' }}>Alan</th>
                    <th style={{ padding: '6px 0', textAlign: 'right' }}>Unique</th>
                    <th style={{ padding: '6px 0', textAlign: 'right' }}>En Sık Değer</th>
                    <th style={{ padding: '6px 0', textAlign: 'right' }}>Adet</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.kategorik_analiz).map(([alan, m]) => (
                    <tr key={alan} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '7px 0', fontSize: 12, fontFamily: 'monospace', color: 'var(--muted)' }}>{alan}</td>
                      <td style={{ padding: '7px 0', textAlign: 'right', fontWeight: 600 }}>{m.unique_count}</td>
                      <td style={{ padding: '7px 0', textAlign: 'right', fontFamily: 'monospace', fontSize: 12 }}>{m.most_frequent ?? '—'}</td>
                      <td style={{ padding: '7px 0', textAlign: 'right' }}>{m.most_frequent_count?.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {}
          {data.son_senkronizasyon && (
            <div className="card">
              <div className="card-title">Son Senkronizasyon</div>
              <div className="kv-row">
                {[
                  ['Tarih',     new Date(data.son_senkronizasyon.tarih).toLocaleString('tr-TR')],
                  ['Çekilen',   data.son_senkronizasyon.rows_fetched?.toLocaleString()],
                  ['Geçerli',   data.son_senkronizasyon.rows_valid?.toLocaleString()],
                  ['Hatalı',    data.son_senkronizasyon.rows_invalid?.toLocaleString()],
                ].map(([lbl, val]) => (
                  <div key={lbl}>
                    <div className="kv-item-lbl">{lbl}</div>
                    <div className="kv-item-val">{val}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
