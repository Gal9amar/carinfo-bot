import { useState, useEffect } from 'react'
import { fetchSearchHistory } from '../api.js'
import LicensePlate from '../components/LicensePlate.jsx'

export default function HistoryPage({ onBack, onViewPlate }) {
  const [plates, setPlates] = useState(null)

  useEffect(() => {
    fetchSearchHistory().then(setPlates).catch(() => setPlates([]))
  }, [])

  return (
    <div className="page">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <button
          onClick={onBack}
          style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: 'var(--btn)', padding: '0 4px' }}
          aria-label="חזרה"
        >
          ›
        </button>
        <div className="page-title" style={{ margin: 0 }}>📜 היסטוריית חיפושים</div>
      </div>

      {plates === null && <div className="loading">⏳</div>}

      {plates?.length === 0 && (
        <div className="card" style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14 }}>
          אין היסטוריית חיפושים עדיין
        </div>
      )}

      {plates?.length > 0 && (
        <>
          <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 12 }}>
            צפייה חוזרת אינה מנכה חיפוש
          </div>
          {plates.map(plate => (
            <button
              key={plate}
              onClick={() => onViewPlate(plate)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: 'var(--bg2)',
                border: 'none',
                borderRadius: 12,
                padding: '12px 16px',
                marginBottom: 8,
                cursor: 'pointer',
              }}
            >
              <LicensePlate plate={plate} size="sm" />
              <span style={{ fontSize: 13, color: 'var(--btn)', fontWeight: 600 }}>
                צפה בדוח ›
              </span>
            </button>
          ))}
        </>
      )}
    </div>
  )
}
