// One header for every premium card in the report: title + the "למנויים בלבד" badge (same look everywhere)
// + the optional admin text shown while the feature is open to everyone.
export default function PremiumHeader({ title, publicLabel }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ fontWeight: 700, fontSize: 15, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0 }}>{title}</div>
        <span style={{
          flexShrink: 0, fontSize: 11, fontWeight: 700, background: '#0066d6', color: '#fff',
          borderRadius: 20, padding: '4px 10px', whiteSpace: 'nowrap',
        }}>למנויים בלבד</span>
      </div>
      {publicLabel && (
        <div style={{ fontSize: 12, lineHeight: 1.5, color: 'var(--text-muted)', marginTop: 6 }}>{publicLabel}</div>
      )}
    </div>
  )
}
