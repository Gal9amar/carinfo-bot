export default function BackButton({ onClick, label = 'חזרה לתפריט' }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '8px 14px',
        minHeight: 40,
        fontSize: 14,
        fontWeight: 700,
        color: 'var(--primary)',
        cursor: 'pointer',
        marginBottom: 20,
        border: '1px solid var(--border)',
        borderRadius: 99,
        background: 'rgba(255, 255, 255, 0.85)',
      }}
    >
      <span aria-hidden="true">→</span> {label}
    </button>
  )
}
