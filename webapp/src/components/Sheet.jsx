import { useEffect, useId, useRef, cloneElement } from 'react'
import { createPortal } from 'react-dom'

// Shared bottom sheet for every admin form: it always fits the visible
// viewport (dvh / Telegram stable height), the body scrolls on its own and
// the footer (Save / Cancel) stays pinned and reachable.
// a11y: role=dialog + aria-modal + labelled title, Escape closes, focus moves
// in and is restored, Tab is kept inside.
export default function Sheet({ title, onClose, footer, children, dismissOnBackdrop = false }) {
  const ref = useRef(null)
  const titleId = useId()

  useEffect(() => {
    const prev = document.activeElement
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    ref.current?.focus({ preventScroll: true })
    const onKey = e => {
      if (e.key === 'Escape') { e.stopPropagation(); onClose?.(); return }
      if (e.key !== 'Tab' || !ref.current) return
      const f = [...ref.current.querySelectorAll('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])')]
        .filter(el => !el.disabled && el.type !== 'hidden' && el.offsetParent !== null)
      if (!f.length) return
      const first = f[0], last = f[f.length - 1]
      if (e.shiftKey && (document.activeElement === first || document.activeElement === ref.current)) { e.preventDefault(); last.focus() }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
      try { prev?.focus?.({ preventScroll: true }) } catch { /* element gone */ }
    }
  }, [])

  return createPortal(
    <div className="sheet-overlay" onClick={dismissOnBackdrop ? onClose : undefined}>
      <div
        ref={ref}
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onClick={e => e.stopPropagation()}
      >
        <div className="sheet-head">
          <h2 id={titleId} className="sheet-title">{title}</h2>
          <button type="button" className="sheet-close" aria-label="סגור" onClick={onClose}>✕</button>
        </div>
        <div className="sheet-body">{children}</div>
        {footer && <div className="sheet-foot">{footer}</div>}
      </div>
    </div>,
    document.body
  )
}

// Visible label bound to a single control (htmlFor / id).
export function Field({ label, hint, children, style }) {
  const id = useId()
  const hintId = hint ? id + '-h' : undefined
  return (
    <div className="field" style={style}>
      <label className="field-label" htmlFor={id}>{label}</label>
      {cloneElement(children, { id, 'aria-describedby': hintId })}
      {hint && <div className="field-hint" id={hintId}>{hint}</div>}
    </div>
  )
}

// Label for a group of controls (chips, toggles).
export function FieldGroup({ label, hint, children }) {
  const id = useId()
  return (
    <div className="field" role="group" aria-labelledby={id}>
      <div className="field-label" id={id}>{label}{hint && <span className="field-hint-inline"> · {hint}</span>}</div>
      {children}
    </div>
  )
}
