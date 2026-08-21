// Shared "searches remaining" progress bar — used on HomePage and ProfilePage
// so the total/percentage/color logic stays in one place.
export default function QuotaProgressBar({ searchesLeft, searchesQuota }) {
  if (searchesLeft === -1 || searchesLeft < 0) return null
  const total = searchesQuota > 0 ? searchesQuota : Math.max(searchesLeft, 10)
  const pct   = Math.min(100, Math.round((searchesLeft / total) * 100))
  const color = pct > 50 ? '#38a169' : pct > 20 ? '#d69e2e' : '#e53e3e'
  return (
    <div style={{ height: 6, background: 'var(--bg)', borderRadius: 4, overflow: 'hidden' }}>
      <div style={{
        height: '100%', width: `${pct}%`, background: color,
        borderRadius: 4, transition: 'width 0.7s cubic-bezier(0.22,1,0.36,1)',
      }} />
    </div>
  )
}
