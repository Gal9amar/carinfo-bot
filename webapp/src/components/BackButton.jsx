export default function BackButton({ onClick, label = 'חזרה לתפריט' }) {
  return (
    <button
      className="card"
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '10px 18px',
        fontSize: 14,
        fontWeight: 700,
        color: 'var(--primary)',
        cursor: 'pointer',
        marginBottom: 24,
        boxShadow: '0 4px 15px rgba(0, 122, 255, 0.15)',
        border: '1px solid rgba(0, 122, 255, 0.2)',
        background: 'rgba(255, 255, 255, 0.7)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
      }}
    >
      ← {label}
    </button>
  )
}
