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

export function SkeletonWatchCard() {
  return (
    <div style={{
      background: 'var(--bg2)', borderRadius: 14, padding: '14px 16px', marginBottom: 10,
      borderRight: '3px solid #55555566',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <Sk w="60%" h={15} mb={8} />
          <Sk w="40%" h={11} />
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <Sk w={30} h={28} r={8} />
          <Sk w={30} h={28} r={8} />
        </div>
      </div>
    </div>
  )
}

export function SkeletonGarageCard() {
  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <Sk w={100} h={30} r={6} />
        <Sk w={90} h={20} r={20} />
      </div>
      <Sk w="65%" h={16} mb={8} />
      <Sk w="30%" h={12} mb={10} />
      <Sk h={44} r={12} />
    </div>
  )
}
