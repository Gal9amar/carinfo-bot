import { useCallback } from 'react'

// Wraps a REAL premium component with placeholder content. When `locked`, the
// content is blurred and removed from the a11y tree + tab order (aria-hidden +
// inert) and an overlay explains the lock and links to the packages screen.
// When not locked, children render untouched.
export default function PremiumLock({ locked, title, publicLabel, onNavigate, children }) {
  const inertRef = useCallback(node => {
    if (node) node.setAttribute('inert', '')
  }, [])

  if (!locked) return children

  return (
    <section
      aria-label={`${title} — פיצ'ר פרימיום`}
      style={{ position: 'relative', marginBottom: 12, minHeight: 150, borderRadius: 'var(--radius)', overflow: 'hidden' }}
    >
      <div
        ref={inertRef}
        aria-hidden="true"
        style={{ filter: 'blur(4px)', pointerEvents: 'none', userSelect: 'none', WebkitUserSelect: 'none' }}
      >
        {children}
      </div>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 12,
      }}>
        <div style={{
          textAlign: 'center', padding: '10px 14px', maxWidth: 300,
          borderRadius: 16, background: 'rgba(255,255,255,0.92)',
          border: '1px solid var(--border)', boxShadow: 'var(--shadow)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
        }}>
          <div style={{ fontWeight: 800, fontSize: 14, color: 'var(--text-main)' }}>
            <span aria-hidden="true">🔒 </span>פיצ'ר פרימיום — {title}
          </div>
          {publicLabel && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{publicLabel}</div>
          )}
          {onNavigate && (
            <button
              type="button" className="btn"
              aria-label={`לחבילות ולמנוי — ${title}`}
              style={{ width: 'auto', padding: '0 20px', marginTop: 2, minHeight: 44 }}
              onClick={() => onNavigate('packages')}
            >לחבילות ולמנוי</button>
          )}
        </div>
      </div>
    </section>
  )
}
