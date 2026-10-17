import { useState, useEffect } from 'react'
import LicensePlate from './LicensePlate.jsx'

const STEPS = [
  { icon: '🔗', text: 'מתחבר למאגר משרד התחבורה' },
  { icon: '📋', text: 'שולף נתוני רישוי ובעלות' },
  { icon: '🔧', text: 'בודק היסטוריית טסט שנתי' },
  { icon: '🔔', text: 'בודק ריקולים פתוחים' },
  { icon: '📊', text: 'מחשב שווי שוק עדכני' },
  { icon: '✅', text: 'מרכיב את הדוח שלך' },
]

const FACTS = [
  '💡 כל רכב בישראל מחויב בטסט שנתי החל מגיל 3 שנים.',
  '💡 בדוח המלא תוכל לראות את כל הבעלים הקודמים של הרכב.',
  '💡 רכב עם שינוי מבנה רשום חייב אישור מיוחד ברשות הרישוי.',
  '💡 שווי השוק מחושב מול מודעות רכב פעילות שמתעדכנות באופן שוטף.',
  '💡 קילומטראז׳ ממוצע לרכב פרטי בישראל הוא כ-15,000 ק"מ בשנה.',
  '💡 אפשר להוריד דוח PDF מלא לשמירה או שיתוף לאחר החיפוש.',
]

export default function VehicleLookupLoader({ plate }) {
  const [stepIdx, setStepIdx] = useState(0)
  const [factIdx, setFactIdx] = useState(0)

  useEffect(() => {
    const stepTimer = setInterval(() => {
      setStepIdx(i => Math.min(i + 1, STEPS.length - 1))
    }, 700)
    const factTimer = setInterval(() => {
      setFactIdx(i => (i + 1) % FACTS.length)
    }, 2800)
    return () => { clearInterval(stepTimer); clearInterval(factTimer) }
  }, [])

  return (
    <div style={{ padding: '28px 16px 16px', textAlign: 'center' }}>
      {plate && (
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 22, opacity: 0.9 }}>
          <LicensePlate plate={plate} size="lg" />
        </div>
      )}

      <div className="card" style={{
        padding: '14px 18px', marginBottom: 0,
        maxWidth: 340, margin: '0 auto', textAlign: 'right',
      }}>
        {STEPS.map((s, i) => {
          const done = i < stepIdx
          const active = i === stepIdx
          return (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '7px 0',
              opacity: done || active ? 1 : 0.35,
              transition: 'opacity 0.35s',
            }}>
              <span style={{ width: 20, textAlign: 'center', fontSize: 15 }}>
                {done ? '✅' : active ? s.icon : '⚪'}
              </span>
              <span style={{
                fontSize: 13.5,
                color: done ? 'var(--hint)' : active ? 'var(--text)' : 'var(--hint)',
                fontWeight: active ? 600 : 400,
                textDecoration: done ? 'none' : 'none',
              }}>
                {s.text}{active ? '…' : ''}
              </span>
            </div>
          )
        })}
      </div>

      <div style={{ maxWidth: 340, margin: '16px auto 0', height: 6, borderRadius: 99, background: 'rgba(0,100,200,0.1)', overflow: 'hidden' }}>
        <div style={{
          width: `${Math.round(((stepIdx + 1) / STEPS.length) * 100)}%`, height: '100%', borderRadius: 99,
          background: 'linear-gradient(90deg, #007aff, #00c6ff)', transition: 'width 0.5s ease',
        }} />
      </div>

      <div style={{
        marginTop: 20, background: 'rgba(0,122,255,0.06)', border: '1px solid var(--border)',
        borderRadius: 14, padding: '10px 14px', fontSize: 12.5, color: 'var(--text-muted)',
        maxWidth: 340, margin: '20px auto 0', minHeight: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'opacity 0.3s',
      }}>
        {FACTS[factIdx]}
      </div>
    </div>
  )
}
