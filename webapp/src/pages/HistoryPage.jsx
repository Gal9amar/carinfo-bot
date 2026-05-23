import { useState, useEffect } from 'react'
import { fetchSearchHistory } from '../api.js'
import LicensePlate from '../components/LicensePlate.jsx'
import BackButton from '../components/BackButton.jsx'

export default function HistoryPage({ onBack, onViewPlate }) {
  const [items, setItems]   = useState(null)
  const [query, setQuery]   = useState('')

  useEffect(() => {
    fetchSearchHistory()
      .catch(() => [])
      .then(data => setItems(data))
  }, [])

  const filtered = items?.filter(item => {
    const plate = typeof item === 'string' ? item : item.plate
    return plate.replace('-', '').includes(query.replace('-', '').trim())
  }) ?? []

  return (
    <div className="page">
      <BackButton onClick={onBack} />
      <div className="page-title">📜 היסטוריית חיפושים</div>

      {items === null && <div className="loading"></div>}

      {items !== null && (
        <>
          {/* Search */}
          <input
            type="text"
            className="input"
            placeholder="🔍 חפש לפי מספר רכב"
            value={query}
            onChange={e => setQuery(e.target.value)}
            style={{ marginBottom: 10 }}
          />

          {items.length === 0 && (
            <div className="card" style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14 }}>
              אין היסטוריית חיפושים עדיין
            </div>
          )}

          {items.length > 0 && filtered.length === 0 && (
            <div className="card" style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14 }}>
              לא נמצאו תוצאות
            </div>
          )}

          {filtered.length > 0 && (
            <>
              <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 12 }}>
                צפייה חוזרת אינה מנכה חיפוש
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {filtered.map(item => {
                  const plate = typeof item === 'string' ? item : item.plate
                  const make  = item.make  || ''
                  const model = item.model || ''
                  const year  = item.year  || ''
                  const color = item.color || ''
                  const title = [make, model].filter(Boolean).join(' ')

                  return (
                    <div key={plate} style={{
                      background: 'var(--bg2)',
                      borderRadius: 14,
                      padding: 12,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 8,
                    }}>
                      {/* Plate */}
                      <LicensePlate plate={plate} size="sm" />

                      {/* Info */}
                      <div style={{ width: '100%', textAlign: 'center', minHeight: 32 }}>
                        {title && (
                          <div style={{
                            fontSize: 12, fontWeight: 700, marginBottom: 2,
                            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                          }}>{title}</div>
                        )}
                        {(year || color) && (
                          <div style={{ fontSize: 11, color: 'var(--hint)' }}>
                            {[year, color].filter(Boolean).join(' · ')}
                          </div>
                        )}
                      </div>

                      {/* Button */}
                      <button
                        onClick={() => onViewPlate(plate)}
                        style={{
                          width: '100%',
                          padding: '8px 0',
                          border: 'none',
                          borderRadius: 10,
                          background: 'var(--btn)',
                          color: 'var(--btn-text)',
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >📊 צפה בדוח</button>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
