import { useRef, useState } from 'react'
import { uploadTicketImage } from '../api.js'

const MAX_BYTES = 5 * 1024 * 1024

/** Picks + uploads one image. `value` = uploaded url ('' = none). */
export function useTicketImage() {
  const [url, setUrl] = useState('')
  const [local, setLocal] = useState('')      // object URL for the instant preview
  const [uploading, setUploading] = useState(false)

  async function pick(file) {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      window.Telegram?.WebApp?.showAlert('ניתן לצרף תמונות בלבד')
      return
    }
    if (file.size > MAX_BYTES) {
      window.Telegram?.WebApp?.showAlert('התמונה גדולה מדי (מקסימום 5MB)')
      return
    }
    setLocal(URL.createObjectURL(file))
    setUploading(true)
    try {
      const res = await uploadTicketImage(file)
      setUrl(res.url)
    } catch (e) {
      setLocal('')
      window.Telegram?.WebApp?.showAlert(e.message === 'TOO_LARGE' ? 'התמונה גדולה מדי (מקסימום 5MB)' : 'שגיאה בהעלאת התמונה')
    }
    setUploading(false)
  }

  function clear() {
    if (local) URL.revokeObjectURL(local)
    setUrl(''); setLocal('')
  }

  return { url, local, uploading, pick, clear }
}

/** 📎 button (hidden file input). */
export function AttachButton({ onPick, disabled, style }) {
  const ref = useRef(null)
  return (
    <>
      <input
        ref={ref} type="file" accept="image/png,image/jpeg,image/webp,image/gif"
        style={{ display: 'none' }}
        onChange={e => { onPick(e.target.files?.[0]); e.target.value = '' }}
      />
      <button
        type="button" disabled={disabled} onClick={() => ref.current?.click()}
        aria-label="צרף תמונה"
        style={{
          width: 44, height: 44, flexShrink: 0, borderRadius: 12, border: '1px solid var(--border)',
          background: 'var(--bg)', fontSize: 18, cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.5 : 1,
          ...style,
        }}
      >📎</button>
    </>
  )
}

/** Preview of the picked image with a remove button. */
export function ImagePreview({ img }) {
  if (!img.local) return null
  return (
    <div style={{ position: 'relative', display: 'inline-block', marginBottom: 8 }}>
      <img src={img.local} alt="תצוגה מקדימה" style={{ maxHeight: 90, maxWidth: 160, borderRadius: 10, display: 'block', opacity: img.uploading ? 0.5 : 1 }} />
      {img.uploading && <span style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>⏳</span>}
      <button
        type="button" onClick={img.clear} aria-label="הסר תמונה"
        style={{ position: 'absolute', top: -6, left: -6, width: 22, height: 22, borderRadius: 11, border: 'none', background: '#c53030', color: '#fff', fontSize: 12, cursor: 'pointer' }}
      >✕</button>
    </div>
  )
}

/** Image inside a message bubble — tap to open full size. */
export function BubbleImage({ src }) {
  const [full, setFull] = useState(false)
  if (!src) return null
  return (
    <>
      <img
        src={src} alt="תמונה מצורפת" loading="lazy" onClick={() => setFull(true)}
        style={{ display: 'block', maxWidth: '100%', maxHeight: 240, borderRadius: 10, marginTop: 6, cursor: 'zoom-in' }}
      />
      {full && (
        <div
          onClick={() => setFull(false)} role="dialog" aria-label="תמונה מוגדלת"
          style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.88)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 12 }}
        >
          <img src={src} alt="תמונה מצורפת" style={{ maxWidth: '100%', maxHeight: '100%', borderRadius: 8 }} />
        </div>
      )}
    </>
  )
}
