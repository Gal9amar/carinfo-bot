export default function BackButton({ onClick, label = 'חזרה לתפריט' }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        background: 'var(--bg2)',
        border: 'none',
        borderRadius: 10,
        padding: '9px 16px',
        fontSize: 14,
        fontWeight: 600,
        color: 'var(--text)',
        cursor: 'pointer',
        marginBottom: 16,
      }}
    >
      ← {label}
    </button>
  )
}
