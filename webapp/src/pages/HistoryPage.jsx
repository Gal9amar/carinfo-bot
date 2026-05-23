import { useState, useEffect } from 'react'
import { fetchSearchHistory } from '../api.js'
import LicensePlate from '../components/LicensePlate.jsx'
import BackButton from '../components/BackButton.jsx'

export default function HistoryPage({ onBack, onViewPlate }) {
  const [items, setItems] = useState(null)

  useEffect(() => {
    fetchSearchHistory().then(setItems).catch(() => setItems([]))
  }, [])

  return (
    <div className="page">
      <BackButton onClick={onBack} />
      <div className="page-title">📜 היסטוריית חיפושים</div>

      {items === null && <div className="loading">⏳ טוען...</div>}

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
                {/* Plate + title row */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: title ? 10 : 0 }}>
                  <LicensePlate plate={plate} />
                  {(year || color) && (
                    <div style={{ textAlign: 'left', fontSize: 13, color: 'var(--hint)' }}>
                      {year && <div style={{ fontWeight: 600, color: 'var(--text)' }}>{year}</div>}
                      {color && <div>{color}</div>}
                    </div>
                  )}
                </div>

                {title && (
                  <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>
                    {title}
                  </div>
                )}

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
                        background: '#e8f5e9',
                        color: '#2e7d32',
                        fontSize: 14,
                        fontWeight: 600,
                        cursor: 'pointer',
                        textDecoration: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 4,
                      }}
                    >
                      🔍 יד2
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
