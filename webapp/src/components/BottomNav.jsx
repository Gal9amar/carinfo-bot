const NAV = [
  { id: 'home',     icon: '🏠', label: 'בית' },
  { id: 'history',  icon: '📋', label: 'חיפושים שלי' },
  { id: 'packages', icon: '⭐', label: 'הזמנות שלי' },
  { id: 'ticket',   icon: '🎫', label: 'תמיכה' },
]

export default function BottomNav({ screen, onNavigate }) {
  return (
    <nav className="bottom-nav">
      {NAV.map(item => (
        <button
          key={item.id}
          className={`bottom-nav-item${screen === item.id ? ' active' : ''}`}
          onClick={() => onNavigate(item.id)}
        >
          <span className="nav-icon">{item.icon}</span>
          <span className="nav-label">{item.label}</span>
        </button>
      ))}
    </nav>
  )
}
