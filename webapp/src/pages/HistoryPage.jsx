import { useState, useEffect } from 'react'
import { fetchSearchHistory } from '../api.js'
import LicensePlate from '../components/LicensePlate.jsx'
import BackButton from '../components/BackButton.jsx'
import PageBanners from '../components/PageBanners.jsx'

const PAGE_SIZE = 8

export default function HistoryPage({ onBack, onViewPlate, onNavigate }) {
  const [items, setItems]     = useState(null)
  const [query, setQuery]     = useState('')
  const [visible, setVisible] = useState(PAGE_SIZE)

  useEffect(() => {
    fetchSearchHistory()
      .catch(() => [])
      .then(data => setItems(data))
  }, [])

  useEffect(() => { setVisible(PAGE_SIZE) }, [query])

  const filtered = items?.filter(item => {
    const plate = typeof item === 'string' ? item : item.plate
    return plate.replace('-', '').includes(query.replace('-', '').trim())
  }) ?? []

  const shown = filtered.slice(0, visible)

  return (
    <div className="page">
      <BackButton onClick={onBack} />
      <div className="page-title">📜 היסטוריית חיפושים</div>

      <PageBanners page="history" onNavigate={onNavigate} />

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
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {shown.map(item => {
                  const plate = typeof item === 'string' ? item : item.plate
                  const make  = item.make  || ''
                  const model = item.model || ''
                  const year  = item.year  || ''
                  const details = [make, model, year].filter(Boolean).join(' ')

                  return (
                    <div key={plate} style={{
                      background: 'var(--bg2)',
                      borderRadius: 14,
                      padding: 12,
                      display: 'flex',
                      alignItems: 'stretch',
                      gap: 12,
                    }}>
                      {/* Column 1: plate row + make/model/year row */}
                      <div style={{
                        flex: 1, minWidth: 0,
                        display: 'flex', flexDirection: 'column',
                        justifyContent: 'center', gap: 6,
                      }}>
                        {/* Row 1: plate number */}
                        <div style={{ alignSelf: 'flex-start' }}>
                          <LicensePlate plate={plate} size="sm" />
                        </div>

                        {/* Row 2: make, model, year */}
                        {details && (
                          <div style={{
                            fontSize: 12, color: 'var(--hint)',
                            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                          }}>{details}</div>
                        )}
                      </div>

                      {/* Column 2: button spanning both rows */}
                      <button
                        onClick={() => onViewPlate(plate)}
                        style={{
                          flexShrink: 0,
                          alignSelf: 'stretch',
                          padding: '8px 14px',
                          border: 'none',
                          borderRadius: 10,
                          background: 'var(--btn)',
                          color: 'var(--btn-text)',
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: 'pointer',
                          whiteSpace: 'nowrap',
                        }}
                      >הצג פרטים</button>
                    </div>
                  )
                })}
              </div>

              {visible < filtered.length && (
                <button
                  onClick={() => setVisible(v => v + PAGE_SIZE)}
                  className="btn"
                  style={{ marginTop: 12 }}
                >הצג עוד</button>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
