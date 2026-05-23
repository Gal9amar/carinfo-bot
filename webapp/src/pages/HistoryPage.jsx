import { useState, useEffect } from 'react'
import { fetchSearchHistory } from '../api.js'
import LicensePlate from '../components/LicensePlate.jsx'
import BackButton from '../components/BackButton.jsx'
import loaderImg from '../assets/loader.png'
export default function HistoryPage({ onBack, onViewPlate }) {
  const [items, setItems] = useState(null)

  useEffect(() => {
    const start = Date.now()
    fetchSearchHistory()
      .catch(() => [])
      .then(data => {
        const elapsed = Date.now() - start
        const remaining = Math.max(0, 3000 - elapsed)
        setTimeout(() => setItems(data), remaining)
      })
  }, [])

  return (
    <div className="page">
      <BackButton onClick={onBack} />
      <div className="page-title">📜 היסטוריית חיפושים</div>

      {items === null && (
        <div className="logo-loader">
          <div className="logo-loader-ring">
            <img src={loaderImg} alt="טוען" />
          </div>
          <span className="logo-loader-text">טוען היסטוריה...</span>
        </div>
      )}

      {items?.length === 0 && (
        <div className="card" style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14 }}>
          אין היסטוריית חיפושים עדיין
        </div>
      )}

      {items?.length > 0 && (
        <>
          <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 12 }}>
            צפייה חוזרת אינה מנכה חיפוש
          </div>
          {items.map(item => {
            const plate = typeof item === 'string' ? item : item.plate
            const make  = item.make  || ''
            const model = item.model || ''
            const year  = item.year  || ''
            const color = item.color || ''
            const title = [make, model].filter(Boolean).join(' ')

            return (
              <div key={plate} style={{
                background: 'var(--bg2)',
                borderRadius: 16,
                padding: 16,
                marginBottom: 12,
              }}>
                {/* Plate — full width */}
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 10 }}>
                  <LicensePlate plate={plate} size="md" />
                </div>

                {/* Vehicle info + report button — side by side */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {title && (
                      <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {title}
                      </div>
                    )}
                    {(year || color) && (
                      <div style={{ fontSize: 12, color: 'var(--hint)' }}>
                        {[year, color].filter(Boolean).join(' · ')}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => onViewPlate(plate)}
                    style={{
                      flexShrink: 0,
                      padding: '8px 14px',
                      border: 'none',
                      borderRadius: 10,
                      background: 'var(--btn)',
                      color: 'var(--btn-text)',
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    📊 צפה בדוח
                  </button>
                </div>
              </div>
            )
          })}
        </>
      )}
    </div>
  )
}
