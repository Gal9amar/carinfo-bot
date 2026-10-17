// Shared phone-first list card for admin lists (grants, codes, groups, ...).
// Slots: leading (chip/icon), title, subtitle, badge, meta (chips), actions, footer (e.g. inline confirm).
// Extra props (draggable, onDragStart, ...) are passed to the root element.
export function AdminItemBtn({ icon, label, onClick, disabled, danger, ariaLabel, title }) {
  return (
    <button type="button" className={'admin-item-btn' + (danger ? ' del' : '')} onClick={onClick}
      disabled={disabled} aria-label={ariaLabel || label} title={title || label}>
      <span className="ico" aria-hidden="true">{icon}</span>
      <span>{label}</span>
    </button>
  )
}

export function AdminItemConfirm({ text, yesLabel = 'כן, מחק', noLabel = 'ביטול', onYes, onNo, busy }) {
  return (
    <div className="admin-item-confirm" role="alertdialog" aria-label={text}>
      <p>{text}</p>
      <div className="row">
        <button type="button" className="admin-item-btn yes" onClick={onYes} disabled={busy}>{busy ? '...' : yesLabel}</button>
        <button type="button" className="admin-item-btn" onClick={onNo} disabled={busy}>{noLabel}</button>
      </div>
    </div>
  )
}

export default function AdminItemCard({ leading, title, subtitle, badge, badgeTone = '', meta, actions, cols = 4, footer, className = '', style, ...rest }) {
  return (
    <div className={'card admin-item ' + className} style={style} {...rest}>
      <div className="admin-item-head">
        {leading != null && <span className="admin-item-lead">{leading}</span>}
        <div className="admin-item-title">{title}</div>
        {badge != null && <span className={'admin-item-badge ' + badgeTone}>{badge}</span>}
      </div>
      {subtitle != null && subtitle !== '' && <p className="admin-item-sub">{subtitle}</p>}
      {meta != null && <div className="admin-item-meta">{meta}</div>}
      {actions != null && <div className="admin-item-actions" style={{ '--cols': cols }}>{actions}</div>}
      {footer}
    </div>
  )
}
