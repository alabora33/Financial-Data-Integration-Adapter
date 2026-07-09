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
      {loading && <div className="loading">Analiz ediliyor…</div>}

      {data && !loading && (
        <>
          {/* Stat cards */}
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
            {/* Faiz */}
            <div className="card">
              <div className="card-title">Faiz &amp; Tutar İstatistikleri</div>
              <table style={{ width: '100%' }}>
                <tbody>
                  {[
                    ['Faiz — Min',  `%${fmt(f?.min)}`],
                    ['Faiz — Max',  `%${fmt(f?.max)}`],
                    ['Faiz — Ort',  `%${fmt(f?.ortalama)}`],
                    ['Tutar — Min', `${fmt(t?.min)} ₺`],
                    ['Tutar — Max', `${fmt(t?.max)} ₺`],
                  ].map(([lbl, val]) => (
                    <tr key={lbl}>
                      <td style={{ padding: '7px 0', color: 'var(--muted)', fontSize: '13px' }}>{lbl}</td>
                      <td style={{ padding: '7px 0', textAlign: 'right', fontWeight: '600', fontVariantNumeric: 'tabular-nums' }}>{val}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Veri kalitesi */}
            <div className="card">
              <div className="card-title">Veri Kalitesi — Eksik Alanlar</div>
              <ProgRow label="Sigorta (boş)"   value={q?.bos_sigorta_alani} total={data.toplam_kayit} bad={q?.bos_sigorta_oran_pct > 5} />
              <ProgRow label="Dış Rating (boş)" value={q?.bos_dis_rating}    total={data.toplam_kayit} bad={q?.bos_dis_rating_pct > 5} />
              <ProgRow label="İç Rating (boş)"  value={q?.bos_ic_rating}     total={data.toplam_kayit} bad />
              <p style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '10px' }}>
                * Kırmızı: %5 üzeri eksiklik
              </p>
            </div>
          </div>

          <div className="two-col">
            {/* Durum dağılımı */}
            <div className="card">
              <div className="card-title">Kredi Durum Dağılımı</div>
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

            {/* Sigorta dağılımı — sadece RETAIL */}
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

          {/* Son sync */}
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
