import { useState, useEffect } from 'react'
import { fetchSearchHistory } from '../api.js'
import LicensePlate from '../components/LicensePlate.jsx'
import BackButton from '../components/BackButton.jsx'
import { SkeletonHistoryCard } from '../components/SkeletonCard.jsx'

export default function HistoryPage({ onBack, onViewPlate }) {
  const [items, setItems] = useState(null)

  useEffect(() => {
    fetchSearchHistory().then(setItems).catch(() => setItems([]))
  }, [])

  return (
    <div className="page">
      <BackButton onClick={onBack} />
      <div className="page-title">📜 היסטוריית חיפושים</div>

      {items === null && [0,1,2].map(i => <SkeletonHistoryCard key={i} />)}

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
            const yad2  = item.yad2  || ''
            const title = [make, model].filter(Boolean).join(' ')

            return (
              <div key={plate} style={{
                background: 'var(--bg2)',
                borderRadius: 16,
                padding: 16,
                marginBottom: 12,
              }}>
                {/* Plate + vehicle info — one row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                  <LicensePlate plate={plate} size="sm" />
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
                </div>

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    onClick={() => onViewPlate(plate)}
                    style={{
                      flex: 1,
                      padding: '10px 0',
                      border: 'none',
                      borderRadius: 10,
                      background: 'var(--btn)',
                      color: 'var(--btn-text)',
                      fontSize: 14,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    📊 צפה בדוח
                  </button>
                  {yad2 && (
                    <a
                      href={yad2}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        flex: 1,
                        padding: '10px 0',
                        border: 'none',
                        borderRadius: 10,
                        background: '#FF4301',
                        color: '#fff',
                        fontSize: 15,
                        fontWeight: 800,
                        cursor: 'pointer',
                        textDecoration: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        letterSpacing: 0.5,
                      }}
                    >
                      Yad2
                    </a>
                  )}
                </div>
              </div>
            )
          })}
        </>
      )}
    </div>
  )
}
