const NAV = [
  { id: 'home',     icon: '🏠', label: 'בית' },
  { id: 'history',  icon: '📋', label: 'חיפושים שלי' },
  { id: 'garage',   icon: '🚘', label: 'רכבים שקניתי' },
  { id: 'packages', icon: '🛒', label: 'חנות' },
  { id: 'watches',  icon: '🔔', label: 'התראות' },
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
