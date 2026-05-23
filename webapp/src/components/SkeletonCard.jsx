function Sk({ w = '100%', h = 16, r = 8, mb = 0 }) {
  return (
    <div className="skeleton" style={{ width: w, height: h, borderRadius: r, marginBottom: mb, flexShrink: 0 }} />
  )
}

export function SkeletonHistoryCard() {
  return (
    <div style={{ background: 'var(--bg2)', borderRadius: 16, padding: 16, marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
        <Sk w={140} h={38} r={6} />
        <div style={{ flex: 1 }}>
          <Sk h={14} mb={6} />
          <Sk w="55%" h={12} />
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <Sk h={40} r={10} />
        <Sk h={40} r={10} />
      </div>
    </div>
  )
}
