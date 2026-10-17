const ICONS = {
  home:    <path d="M4 11 12 4l8 7v9h-5v-6H9v6H4z" />,
  history: <><path d="M7 3h7l5 5v13H7z" /><path d="M14 3v5h5M10 13h6M10 17h6" /></>,
  garage:  <><path d="M4 16v-4l2-5h12l2 5v4z" /><circle cx="8" cy="16" r="1.6" /><circle cx="16" cy="16" r="1.6" /></>,
  profile: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
}

const NAV = [
  { id: 'home',     label: 'בית' },
  { id: 'history',  label: 'חיפושים שלי' },
  { id: 'garage',   label: 'רכבים שקניתי' },
  { id: 'profile',  label: 'אזור אישי' },
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
          <span className="nav-icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[item.id]}</svg>
          </span>
          <span className="nav-label">{item.label}</span>
        </button>
      ))}
    </nav>
  )
}
