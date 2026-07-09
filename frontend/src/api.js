const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getToken() {
  return localStorage.getItem('teamsec_token')
}

function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function handle401() {
  localStorage.removeItem('teamsec_token')
  window.dispatchEvent(new Event('unauthorized'))
}

export async function login(username, password) {
  const body = new URLSearchParams({ username, password })
  const resp = await fetch(`${API_URL}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!resp.ok) throw new Error('Kullanıcı adı veya şifre hatalı.')
  const data = await resp.json()
  localStorage.setItem('teamsec_token', data.access_token)
  return data
}

export function logout() {
  localStorage.removeItem('teamsec_token')
}

export async function triggerSync(tenantId, loanType) {
  const resp = await fetch(
    `${API_URL}/api/sync`,
    {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ tenant_id: tenantId, loan_type: loanType }),
    }
  )
  if (resp.status === 401) { handle401(); throw new Error('UNAUTHORIZED') }
  if (!resp.ok) throw new Error(await resp.text())
  return resp.json()
}

export async function getData(tenantId, loanType, page = 1, pageSize = 50) {
  const p = new URLSearchParams({ tenant_id: tenantId, loan_type: loanType, page, page_size: pageSize })
  const resp = await fetch(`${API_URL}/api/data?${p}`, { headers: authHeaders() })
  if (resp.status === 401) { handle401(); throw new Error('UNAUTHORIZED') }
  if (!resp.ok) throw new Error(await resp.text())
  return resp.json()
}

export async function getProfiling(tenantId, loanType) {
  const p = new URLSearchParams({ tenant_id: tenantId, loan_type: loanType })
  const resp = await fetch(`${API_URL}/api/profiling?${p}`, { headers: authHeaders() })
  if (resp.status === 401) { handle401(); throw new Error('UNAUTHORIZED') }
  if (!resp.ok) throw new Error(await resp.text())
  return resp.json()
}

export function getUsernameFromToken() {
  const token = getToken()
  if (!token) return ''
  try {
    return JSON.parse(atob(token.split('.')[1])).sub || ''
  } catch {
    return ''
  }
}
