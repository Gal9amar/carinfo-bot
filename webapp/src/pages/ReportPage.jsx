import { useState, useEffect } from 'react'
import { fetchVehicle, fetchMarketPrice, requestPdfReport, fetchNote, saveNote, createUserWatch, fetchUserWatches } from '../api.js'
import { MAKE_EN, MODEL_EN } from '../vehicleNames.js'
import LicensePlate from '../components/LicensePlate.jsx'
import BackButton from '../components/BackButton.jsx'

// ── helpers ──────────────────────────────────────────────────────────────────

function yn(v) {
  if (v === null || v === undefined) return null
  const s = String(v).trim().toUpperCase()
  if (s === '' || s === 'NONE' || s === 'NAN') return null
  if (['1', 'Y', 'YES', 'TRUE'].includes(s)) return '✅ כן'
  if (['0', 'N', 'NO', 'FALSE'].includes(s)) return '❌ לא'
  return String(v)
}

function fmtDate(raw) {
  if (!raw) return null
  try {
    const d = new Date(String(raw).substring(0, 10) + 'T00:00:00')
    return d.toLocaleDateString('he-IL', { year: 'numeric', month: '2-digit', day: '2-digit' })
  } catch { return String(raw).substring(0, 10) }
}

function fmtBaalutDt(dt) {
  try {
    const s = String(dt)
    const months = ['', 'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
      'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
    return `${months[parseInt(s.substring(4, 6))]} ${s.substring(0, 4)}`
  } catch { return String(dt) }
}

function testStatus(tokefRaw) {
  if (!tokefRaw) return null
  try {
    const tokef = new Date(String(tokefRaw).substring(0, 10) + 'T00:00:00')
    const delta = Math.floor((tokef - new Date()) / (1000 * 60 * 60 * 24))
    if (delta < 0) return `🔴 פג תוקף לפני ${Math.abs(delta)} ימים`
    if (delta <= 30) return `🟡 פג תוקף בעוד ${delta} ימים`
    return `🟢 בתוקף עד ${tokef.toLocaleDateString('he-IL')}`
  } catch { return null }
}

function fmtNum(v) {
  if (v === null || v === undefined || v === '') return null
  try { return Number(v).toLocaleString('he-IL') }
  catch { return String(v) }
}

function v(record, w, ...keys) {
  for (const k of keys) {
    const src = k.startsWith('w.') ? w : record
    const key = k.startsWith('w.') ? k.slice(2) : k
    const val = src[key]
    if (val !== null && val !== undefined) {
      const s = String(val).trim()
      if (s && s !== 'None' && s !== 'nan' && s !== '0') return s
    }
  }
  return null
}

function row(label, value) {
  if (value === null || value === undefined || value === '') return ''
  return `• ${label}: ${String(value)}\n`
}

function buildFullText(record, ownership) {
  const w = record._wltp || {}
  const recalls = record._recalls || []
  const recallsByPlate = record._recalls_by_plate
  const plate = record.mispar_rechev || ''
  const make = record.tozeret_nm || ''
  const model = record.kinuy_mishari || record.degem_nm || ''
  const year = record.shnat_yitzur || ''
  const color = record.tzeva_rechev || ''
  const km = record.kilometer_test_aharon
  const baalut = record.baalut || ''
  const kmStr = km ? Number(km).toLocaleString('he-IL') : 'לא ידוע'
  const testStr = testStatus(record.tokef_dt) || 'לא ידוע'

  const flags = []
  if (record._scrapped_dt) flags.push('🚨 רכב גרוטאה — אינו רשאי לנסוע על הכביש')
  if (String(record.shinui_mivne_ind || '').trim() === '1') flags.push('⚠️ שינוי מבנה רשום')
  if (record._inactive_no_degem) flags.push('⚠️ רישום לא פעיל ללא קוד דגם')
  else if (record._inactive_registry || record._was_rental) flags.push('⚠️ רשום במאגר רכב לא פעיל')
  if (record._personal_import) flags.push('📦 רכב יבוא אישי')

  const auto = w.automatic_ind
  const gearbox = (auto === 1 || auto === '1') ? 'אוטומטית' : (auto === 0 || auto === '0') ? 'ידנית' : null

  let t = `🚗 דוח רכב — ${plate}\n`
  t += `━━━━━━━━━━━━━━━━━━━━━\n`
  t += `🏭 ${make} ${model} (${year})\n`
  if (color) t += `🎨 צבע: ${color}\n`
  t += `🔑 ק"מ: ${kmStr}\n`
  t += `🔧 טסט: ${testStr}\n`
  t += `👥 בעלויות: ${ownership.length} | נוכחית: ${baalut}\n`
  if (flags.length) { t += '\n'; flags.forEach(f => { t += `${f}\n` }) }

  if (record._same_model_count != null)
    t += `🇮🇱 ${Number(record._same_model_count).toLocaleString('he-IL')} מספר הרכבים לדגם זה על כבישי ישראל\n`

  t += `\n📋 פרטים כלליים\n${'─'.repeat(20)}\n`
  t += row('יצרן', make)
  t += row('דגם', model)
  t += row('רמת גימור', w.ramat_gimur)
  t += row('שנת ייצור', year)
  t += row('צבע', color)
  t += row('בעלות', baalut)
  t += row('ארץ ייצור', w.tozeret_eretz_nm)
  t += row('יבואן', w.tozar)
  t += row('סוג מרכב', w.merkav)
  t += row('מסגרת', record.misgeret)
  t += row('דגם מנוע', record.degem_manoa)
  t += row('מקוריות', record.mkoriut_nm)

  t += `\n⚙️ מפרט טכני\n${'─'.repeat(20)}\n`
  t += row('דלק', record.sug_delek_nm)
  t += row('הנעה', w.hanaa_nm)
  t += row('נפח מנוע', w.nefah_manoa || record.nefach_manoa ? `${w.nefah_manoa || record.nefach_manoa} סמ"ק` : null)
  t += row('כוח סוס', w.koah_sus)
  t += row('הילוכים', gearbox)
  t += row('מושבים', w.mispar_moshavim)
  t += row('דלתות', w.mispar_dlatot)
  t += row('משקל', w.mishkal_kolel ? `${w.mishkal_kolel} ק"ג` : null)
  t += row('גרירה עם בלמים', w.kosher_grira_im_blamim ? `${w.kosher_grira_im_blamim} ק"ג` : null)
  t += row('גרירה ללא בלמים', w.kosher_grira_bli_blamim ? `${w.kosher_grira_bli_blamim} ק"ג` : null)

  t += `\n🔧 גלגלים וצמיגים\n${'─'.repeat(20)}\n`
  t += row('צמיג קדמי', record.zmig_kidmi)
  t += row('צמיג אחורי', record.zmig_ahori || record.zmig_achori)

  t += `\n🛋️ ציוד\n${'─'.repeat(20)}\n`
  t += row('מיזוג', yn(w.mazgan_ind))
  t += row('הגה כוח', yn(w.hege_koah_ind))
  t += row('חלונות חשמל', w.mispar_halonot_hashmal ? `${w.mispar_halonot_hashmal} חלונות` : null)
  t += row('גג שמש', yn(w.halon_bagg_ind))

  t += `\n🛡️ בטיחות ופליטות\n${'─'.repeat(20)}\n`
  t += row('ניקוד בטיחות', w.nikud_betihut)
  t += row('כריות אוויר', w.mispar_kariot_avir ? `${w.mispar_kariot_avir} כריות` : null)
  t += row('ABS', yn(w.abs_ind))
  t += row('ESP', yn(w.bakarat_yatzivut_ind))
  t += row('CO₂ WLTP', w.CO2_WLTP || w.kamut_CO2 ? `${w.CO2_WLTP || w.kamut_CO2} גר'/ק"מ` : null)
  t += row('קבוצת זיהום', record.kvutzat_zihum || record.kvuzat_zihum)

  t += `\n🤖 ADAS\n${'─'.repeat(20)}\n`
  const adasFields = [
    ['שמירת נתיב', yn(w.bakarat_stiya_menativ_ind)],
    ['ניטור קדמי', yn(w.nitur_merhak_milfanim_ind)],
    ['שטח עיוור', yn(w.zihuy_beshetah_nistar_ind)],
    ['בקרת שיוט', yn(w.bakarat_shyut_adaptivit_ind)],
    ['זיהוי הולכי רגל', yn(w.zihuy_holchey_regel_ind)],
    ['בלימת חירום', yn(w.maarechet_ezer_labalam_ind)],
    ['מצלמת רוורס', yn(w.matzlemat_reverse_ind)],
    ['חיישני צמיגים', yn(w.hayshaney_lahatz_avir_batzmigim_ind)],
    ['זיהוי תמרורים', yn(w.zihuy_tamrurey_tnua_ind)],
  ]
  adasFields.forEach(([label, val]) => { t += row(label, val) })

  t += `\n📅 היסטוריה\n${'─'.repeat(20)}\n`
  t += row('רישום ראשון', fmtDate(record.rishum_rishon_dt))
  t += row('עלייה לכביש', fmtDate(record.moed_aliya_lakvish))
  t += row('ק"מ בטסט', km ? `${Number(km).toLocaleString('he-IL')} ק"מ` : null)
  t += row('טסט אחרון', fmtDate(record.mivchan_acharon_dt))
  t += row('תוקף טסט', testStr)
  t += row('שינוי מבנה', yn(record.shinui_mivne_ind))
  t += row('שינוי צבע', yn(record.shnui_zeva_ind))
  t += row('GAPAM', yn(record.gapam_ind))
  t += row('תו נכה', record._tag_nache ? '✅ כן' : '❌ לא')

  t += `\n👥 בעלויות (${ownership.length})\n${'─'.repeat(20)}\n`
  ownership.forEach((o, i) => {
    const emoji = o.baalut === 'פרטי' ? '👤' : o.baalut === 'סוחר' ? '🏢' : '❓'
    t += `${i + 1}. ${emoji} ${o.baalut} — ${fmtBaalutDt(o.baalut_dt)}\n`
  })

  if (recalls.length > 0) {
    t += `\n🔔 ריקולים (${recalls.length})\n${'─'.repeat(20)}\n`
    recalls.forEach(r => {
      if (recallsByPlate) {
        t += `• ${String(r.TAARICH_PTICHA || '').substring(0, 10)} ${r.TEUR_TAKALA || ''}\n`
      } else {
        t += `• ${r.SHNAT_RECALL || ''}: ${r.TEUR_TAKALA || ''}\n`
      }
    })
  } else {
    t += `\n🔔 ריקולים: לא נמצאו\n`
  }

  t += `\n━━━━━━━━━━━━━━━━━━━━━\n`
  t += `מופק על ידי @israelcarinfobot`
  return t
}

// ── sub-components ────────────────────────────────────────────────────────────

// ── SummaryTab ────────────────────────────────────────────────────────────────

function SummaryTab({ record, ownership, recalls, make, model, year, color, km, testStr,
  plateNum, score, flags, marketData, w, statusColor }) {

  const kmNum = km ? Number(km) : null
  const age = year ? new Date().getFullYear() - parseInt(year) : null

  const ownersPrivate = ownership.filter(o => o.baalut === 'פרטי').length
  const ownersDealer  = ownership.filter(o => o.baalut === 'סוחר').length

  return (
    <div>
      {/* ── Score card ── */}
      <div style={{
        borderRadius: 20, marginBottom: 14, overflow: 'hidden',
        background: 'var(--bg2)',
        boxShadow: `0 0 0 2px ${score.color}55, 0 8px 32px rgba(0,0,0,0.25)`,
      }}>
        <div style={{
          background: `linear-gradient(135deg, ${score.color}33, ${score.color}11)`,
          padding: '24px 20px', display: 'flex', alignItems: 'center', gap: 20,
        }}>
          {/* Grade circle */}
          <div style={{
            width: 72, height: 72, borderRadius: '50%', flexShrink: 0,
            background: score.bg, border: `3px solid ${score.color}`,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{ fontSize: 30, fontWeight: 900, color: score.color, lineHeight: 1 }}>{score.grade}</span>
          </div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, color: score.color }}>{score.label}</div>
            <div style={{ fontSize: 13, color: 'var(--hint)', marginTop: 3 }}>
              {make} {model} · {year}
            </div>
            {color && <div style={{ fontSize: 12, color: 'var(--hint)', marginTop: 1 }}>{color}</div>}
          </div>
        </div>

        {/* Quick 4 stats */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 1, background: 'var(--bg)' }}>
          {[
            { icon: '👥', val: ownership.length, label: 'בעלויות' },
            { icon: '🛣️', val: kmNum ? `${Math.round(kmNum / 1000)}K` : '—', label: 'ק"מ' },
            { icon: '📅', val: year || '—', label: 'שנה' },
            { icon: '🔔', val: recalls.length || '✓', label: 'ריקולים' },
          ].map(({ icon, val, label }) => (
            <div key={label} style={{
              background: 'var(--bg2)', padding: '12px 6px', textAlign: 'center',
            }}>
              <div style={{ fontSize: 16 }}>{icon}</div>
              <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text)', lineHeight: 1.2, marginTop: 2 }}>{val}</div>
              <div style={{ fontSize: 10, color: 'var(--hint)', marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Test status card ── */}
      {testStr && (
        <div style={{
          borderRadius: 14, padding: '14px 16px', marginBottom: 14,
          background: 'var(--bg2)', display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <span style={{ fontSize: 28 }}>🔧</span>
          <div>
            <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 2 }}>תוקף טסט</div>
            <div style={{ fontWeight: 700, fontSize: 15 }}>{testStr}</div>
          </div>
        </div>
      )}

      {/* ── Market price ── */}
      {marketData?.market && (() => {
        const authorized = marketData.authorized !== false
        const m   = marketData.market
        const yr  = marketData.year ? parseInt(marketData.year) : null
        const filtered = yr && m.items?.length
          ? m.items.filter(i => parseInt(i.vehicleDates?.yearOfProduction || 0) === yr)
          : m.items || []
        const prices = (filtered.length > 0 ? filtered : m.items || [])
          .map(i => i.price).filter(Boolean).sort((a, b) => a - b)
        if (!prices.length) return null
        const median = prices[Math.floor(prices.length / 2)]
        const min    = prices[0]
        const max    = prices[prices.length - 1]
        return (
          <div className="card" style={{ marginBottom: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
              <div>
                <div style={{
                  display: 'inline-block', fontSize: 11, fontWeight: 700,
                  background: '#8b5cf6', color: '#fff',
                  borderRadius: 20, padding: '4px 10px', marginBottom: 6,
                }}>למנויים בלבד</div>
                <div style={{ fontWeight: 700, fontSize: 15 }}>💰 מחיר שוק – Yad2</div>
              </div>
              {marketData.public_label && (
                <div style={{ fontSize: 11, color: 'var(--hint)', textAlign: 'left', whiteSpace: 'nowrap' }}>
                  {marketData.public_label}
                </div>
              )}
            </div>
            {[
              ['ממוצע שוק', `₪${median.toLocaleString()}`],
              ['מינימום',   `₪${min.toLocaleString()}`],
              ['מקסימום',   `₪${max.toLocaleString()}`],
            ].map(([label, val]) => (
              <div key={label} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '6px 0', borderBottom: '1px solid var(--bg)', fontSize: 14, gap: 8,
              }}>
                <span style={{ color: 'var(--hint)' }}>{label}</span>
                <span style={{
                  fontWeight: 600,
                  ...(authorized ? {} : { filter: 'blur(5px)', userSelect: 'none' }),
                }}>{val}</span>
              </div>
            ))}
          </div>
        )
      })()}

      {/* ── Ownership timeline ── */}
      {ownership.length > 0 && (
        <div style={{
          borderRadius: 14, padding: '14px 16px', marginBottom: 14,
          background: 'var(--bg2)',
        }}>
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12 }}>
            👥 היסטוריית בעלויות
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            {[
              { label: 'סה"כ', val: ownership.length, color: '#38bdf8' },
              { label: 'פרטי', val: ownersPrivate, color: '#38a169' },
              { label: 'סוחר', val: ownersDealer, color: '#d69e2e' },
            ].map(({ label, val, color }) => (
              <div key={label} style={{
                flex: 1, textAlign: 'center', background: 'var(--bg)',
                borderRadius: 10, padding: '8px 4px',
              }}>
                <div style={{ fontSize: 20, fontWeight: 800, color }}>{val}</div>
                <div style={{ fontSize: 11, color: 'var(--hint)' }}>{label}</div>
              </div>
            ))}
          </div>
          {/* Timeline */}
          <div style={{ position: 'relative', paddingRight: 20 }}>
            <div style={{
              position: 'absolute', right: 7, top: 6, bottom: 6,
              width: 2, background: 'rgba(255,255,255,0.08)', borderRadius: 2,
            }} />
            {ownership.map((o, i) => {
              const isDealer = o.baalut === 'סוחר'
              const dotColor = isDealer ? '#d69e2e' : '#38a169'
              return (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  paddingBottom: i < ownership.length - 1 ? 10 : 0,
                }}>
                  <div style={{
                    width: 14, height: 14, borderRadius: '50%', flexShrink: 0,
                    background: dotColor, border: '2px solid var(--bg2)',
                    position: 'relative', zIndex: 1,
                  }} />
                  <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                    <span style={{ color: 'var(--text)', fontWeight: 500 }}>
                      {isDealer ? '🏢' : '👤'} {o.baalut || '?'}
                    </span>
                    <span style={{ color: 'var(--hint)' }}>{fmtBaalutDt(o.baalut_dt)}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Key specs ── */}
      <div style={{
        borderRadius: 14, padding: '14px 16px', marginBottom: 14,
        background: 'var(--bg2)',
      }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10 }}>⚙️ פרטים עיקריים</div>
        {[
          ['סוג דלק',     record.sug_delek_nm],
          ['תיבת הילוכים', w.automatic_ind != null ? ((w.automatic_ind === 1 || w.automatic_ind === '1') ? 'אוטומטית' : 'ידנית') : null],
          ['כוח סוס',     w.koah_sus ? `${w.koah_sus} כ"ס` : null],
          ['מושבים',      w.mispar_moshavim],
          ['ניקוד בטיחות', w.nikud_betihut],
          ['בעלות נוכחית', record.baalut],
          ['יבואן',       w.tozar],
        ].filter(([, val]) => val != null && val !== '').map(([label, val]) => (
          <div key={label} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '6px 0', borderBottom: '1px solid var(--bg)', fontSize: 13,
          }}>
            <span style={{ color: 'var(--hint)' }}>{label}</span>
            <span style={{ fontWeight: 600 }}>{val}</span>
          </div>
        ))}
      </div>

      {/* ── Recalls summary ── */}
      <div style={{
        borderRadius: 14, padding: '14px 16px', marginBottom: 14,
        background: recalls.length > 0 ? '#e53e3e11' : '#38a16911',
        border: `1px solid ${recalls.length > 0 ? '#e53e3e33' : '#38a16933'}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 22 }}>{recalls.length > 0 ? '⚠️' : '✅'}</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14 }}>
              {recalls.length > 0 ? `${recalls.length} ריקולים ידועים` : 'אין ריקולים ידועים'}
            </div>
            {recalls.length > 0 && (
              <div style={{ fontSize: 12, color: 'var(--hint)', marginTop: 2 }}>
                {recalls[0].TEUR_TAKALA || recalls[0].SHNAT_RECALL || ''}
              </div>
            )}
          </div>
        </div>
      </div>

    </div>
  )
}

// ── Row & Sec ─────────────────────────────────────────────────────────────────

function Row({ label, value }) {
  if (value === null || value === undefined || value === '') return null
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
      padding: '6px 0', borderBottom: '1px solid var(--bg)', fontSize: 14, gap: 8,
    }}>
      <span style={{ color: 'var(--hint)', flexShrink: 0, minWidth: 120 }}>{label}</span>
      <span style={{ fontWeight: 500, textAlign: 'end' }}>{String(value)}</span>
    </div>
  )
}

function Sec({ title, children }) {
  const kids = Array.isArray(children) ? children.flat() : [children]
  if (!kids.some(c => c !== null && c !== undefined && c !== false)) return null
  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

export default function ReportPage({ plate, onBack, user }) {
  const [activeTab, setActiveTab] = useState('summary')
  const [record, setRecord] = useState(null)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)
  const [marketData, setMarketData] = useState(undefined) // undefined=loading, null=disabled/error
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfSent, setPdfSent] = useState(false)
  const [note, setNote] = useState('')
  const [noteSaved, setNoteSaved] = useState(false)
  const [noteDirty, setNoteDirty] = useState(false)
  const [noteSaving, setNoteSaving] = useState(false)
  const [watchState, setWatchState] = useState('idle') // idle | loading | done | error | exists

  useEffect(() => {
    if (!plate) { setError('לא צוין מספר רכב'); return }
    fetchVehicle(plate)
      .then(r => {
        setRecord(r)
        const mk = String(r.tozeret_nm || '').trim()
        const mdl = String(r.kinuy_mishari || r.degem_nm || '').trim()
        const yr = r.shnat_yitzur ? String(r.shnat_yitzur) : ''
        if (mk && user?.show_watch) {
          fetchUserWatches().then(watches => {
            const exists = watches.some(w =>
              w.make === mk && w.model === mdl &&
              String(w.year ?? '') === yr
            )
            if (exists) setWatchState('exists')
          }).catch(() => {})
        }
        return fetchMarketPrice(plate)
          .then(d => setMarketData(d))
          .catch(() => setMarketData(null))
      })
      .catch(() => setError('הרכב לא נמצא או שגיאה בטעינה'))
    fetchNote(plate).then(n => { setNote(n || ''); setNoteDirty(false) }).catch(() => {})
  }, [plate])

  if (error) return (
    <div className="page">
      <div className="loading">❌ {error}</div>
      <button className="btn btn-secondary" style={{ marginTop: 16 }}
        onClick={() => onBack ? onBack('home') : window.Telegram?.WebApp?.close()}>חזור</button>
    </div>
  )
  if (!record) return <div className="loading"></div>

  const w = record._wltp || {}
  const ownership = record._ownership || []
  const recalls = record._recalls || []
  const recallsByPlate = record._recalls_by_plate

  const plateNum = record.mispar_rechev || plate
  const make = record.tozeret_nm || ''
  const model = record.kinuy_mishari || record.degem_nm || ''
  const year = String(record.shnat_yitzur || '')
  const color = record.tzeva_rechev || ''
  const km = record.kilometer_test_aharon
  const testStr = testStatus(record.tokef_dt)

  // overall status
  const scrapped = record._scrapped_dt
  const inactive = record._inactive_registry || record._was_rental
  const inactiveNd = record._inactive_no_degem
  const bodyChange = String(record.shinui_mivne_ind || '').trim() === '1'
  const flags = []
  if (scrapped) flags.push('🚨 רכב גרוטאה — אינו רשאי לנסוע על הכביש')
  if (inactiveNd) flags.push('⚠️ רישום לא פעיל ללא קוד דגם')
  else if (inactive) flags.push('⚠️ רשום במאגר רכב לא פעיל')
  if (bodyChange) flags.push('⚠️ שינוי מבנה רשום')
  if (record._personal_import) flags.push('📦 רכב יבוא אישי')

  let statusLabel = '🟢 תקין'
  let statusColor = '#38a169'
  if (scrapped || inactive || inactiveNd) { statusLabel = '🔴 דורש בדיקה'; statusColor = '#e53e3e' }
  else if (bodyChange || (testStr && (testStr.startsWith('🟡') || testStr.startsWith('🔴')))) {
    statusLabel = '🟡 שים לב'; statusColor = '#d69e2e'
  }

  const auto = w.automatic_ind
  const gearbox = (auto === 1 || auto === '1') ? 'אוטומטית' : (auto === 0 || auto === '0') ? 'ידנית' : null

  const engineCc = w.nefah_manoa || record.nefach_manoa
  const weight = w.mishkal_kolel
  const height = w.gova
  const towWith = w.kosher_grira_im_blamim
  const towWithout = w.kosher_grira_bli_blamim

  async function handleCopy() {
    const text = buildFullText(record, ownership)
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2200)
    } catch { /* ignore */ }
  }

  // ── score calculation ────────────────────────────────────────────────────
  function calcScore() {
    let score = 100
    if (scrapped || inactive || inactiveNd) score -= 50
    if (bodyChange) score -= 20
    const owners = ownership.length
    if (owners >= 5) score -= 20
    else if (owners >= 3) score -= 10
    else if (owners >= 2) score -= 5
    const age = year ? new Date().getFullYear() - parseInt(year) : 0
    const kmNum = km ? Number(km) : 0
    const expectedKm = age * 15000
    if (kmNum > expectedKm * 1.4) score -= 15
    if (testStr && testStr.startsWith('🔴')) score -= 15
    else if (testStr && testStr.startsWith('🟡')) score -= 5
    if (recalls.length >= 3) score -= 10
    else if (recalls.length >= 1) score -= 5
    score = Math.max(0, Math.min(100, score))
    if (score >= 80) return { grade: 'A', label: 'מצוין', color: '#38a169', bg: '#38a16922' }
    if (score >= 60) return { grade: 'B', label: 'טוב', color: '#d69e2e', bg: '#d69e2e22' }
    if (score >= 40) return { grade: 'C', label: 'בינוני', color: '#dd6b20', bg: '#dd6b2022' }
    return { grade: 'D', label: 'דורש בדיקה', color: '#e53e3e', bg: '#e53e3e22' }
  }
  const score = calcScore()


  return (
    <div className="page">
      {onBack && <BackButton onClick={onBack} />}

      {/* ── Header ── */}
      <div style={{ textAlign: 'center', marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 8 }}>דוח רכב</div>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 10 }}>
          <LicensePlate plate={plateNum} size="lg" />
        </div>
        <div style={{ fontSize: 16, fontWeight: 600 }}>
          {[make, model, year].filter(Boolean).join(' · ')}
        </div>
        {color && <div style={{ fontSize: 13, color: 'var(--hint)', marginTop: 2 }}>{color}</div>}
        <div style={{
          display: 'inline-block', marginTop: 8, padding: '4px 14px', borderRadius: 20,
          background: statusColor + '22', color: statusColor, fontSize: 13, fontWeight: 600,
        }}>{statusLabel}</div>
      </div>

      {/* ── Tab bar ── */}
      <div style={{
        display: 'flex', gap: 6, marginBottom: 16,
        background: 'var(--bg2)', borderRadius: 14, padding: 4,
      }}>
        {[
          { id: 'summary', label: '✨ סיכום' },
          { id: 'full',    label: '📋 דוח מלא' },
        ].map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
            flex: 1, padding: '9px 0', border: 'none', borderRadius: 11,
            fontSize: 14, fontWeight: 600, cursor: 'pointer', transition: 'all 0.15s',
            background: activeTab === tab.id ? 'linear-gradient(135deg,#1e40af,#0ea5e9)' : 'transparent',
            color: activeTab === tab.id ? '#fff' : 'var(--hint)',
          }}>{tab.label}</button>
        ))}
      </div>

      {/* ── Flags (always visible) ── */}
      {flags.length > 0 && (
        <div style={{
          background: '#fff3cd22', border: `1px solid ${statusColor}55`,
          borderRadius: 10, padding: '10px 14px', marginBottom: 12, fontSize: 13,
        }}>
          {flags.map((f, i) => <div key={i} style={{ marginBottom: i < flags.length - 1 ? 4 : 0 }}>{f}</div>)}
        </div>
      )}

      {/* ══════════════ SUMMARY TAB ══════════════ */}
      {activeTab === 'summary' && (
        <SummaryTab
          record={record} ownership={ownership} recalls={recalls}
          make={make} model={model} year={year} color={color}
          km={km} testStr={testStr} plateNum={plateNum}
          score={score} flags={flags} marketData={marketData}
          w={w} statusColor={statusColor}
        />
      )}

      {activeTab === 'full' && <>

      {/* ── Quick stats ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
        <div className="stat-card">
          <div className="stat-value">{ownership.length}</div>
          <div className="stat-label">בעלויות</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ fontSize: km ? 18 : 22 }}>
            {km ? Number(km).toLocaleString('he-IL') : '—'}
          </div>
          <div className="stat-label">ק"מ</div>
        </div>
        <div className="stat-card" style={{ gridColumn: 'span 2' }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: statusColor }}>
            {testStr || '—'}
          </div>
          <div className="stat-label">תוקף טסט</div>
        </div>
        <div className="stat-card" style={{ gridColumn: 'span 2' }}>
          <div style={{ fontSize: 22, fontWeight: 600, color: 'var(--text)' }}>
            {record._same_model_count != null
              ? Number(record._same_model_count).toLocaleString('he-IL')
              : '—'}
          </div>
          <div className="stat-label">🇮🇱 מספר הרכבים לדגם זה על כבישי ישראל</div>
        </div>
      </div>

      {/* ── Market Price ── */}
      {(() => {
        if (!marketData?.market) return null
        const authorized = marketData.authorized !== false
        const m   = marketData.market
        const yr  = marketData.year ? parseInt(marketData.year) : null
        const filtered = yr && m.items?.length
          ? m.items.filter(i => parseInt(i.vehicleDates?.yearOfProduction || 0) === yr)
          : m.items || []
        const prices = (filtered.length > 0 ? filtered : m.items || [])
          .map(i => i.price).filter(Boolean).sort((a, b) => a - b)
        const kms = (filtered.length > 0 ? filtered : m.items || [])
          .map(i => i.km).filter(Boolean)
        if (!prices.length) return null
        const median = prices[Math.floor(prices.length / 2)]
        const min    = prices[0]
        const max    = prices[prices.length - 1]
        const avgKm  = kms.length ? Math.round(kms.reduce((a, b) => a + b, 0) / kms.length) : null
        return (
          <div className="card" style={{ marginBottom: 12 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
              <div>
                <div style={{
                  display: 'inline-block', fontSize: 11, fontWeight: 700,
                  background: '#8b5cf6', color: '#fff',
                  borderRadius: 20, padding: '4px 10px', marginBottom: 6,
                }}>למנויים בלבד</div>
                <div style={{ fontWeight: 700, fontSize: 15 }}>💰 מחיר שוק – Yad2</div>
              </div>
              {marketData.public_label && (
                <div style={{ fontSize: 11, color: 'var(--hint)', textAlign: 'left', whiteSpace: 'nowrap' }}>
                  {marketData.public_label}
                </div>
              )}
            </div>
            {/* Stats — only values blurred for unauthorized users */}
            {[
              ['ממוצע שוק',  `₪${median.toLocaleString()}`],
              ['מינימום',    `₪${min.toLocaleString()}`],
              ['מקסימום',    `₪${max.toLocaleString()}`],
              ...(avgKm ? [['ק״מ ממוצע', `${avgKm.toLocaleString()} ק״מ`]] : []),
            ].map(([label, val]) => (
              <div key={label} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
                padding: '6px 0', borderBottom: '1px solid var(--bg)', fontSize: 14, gap: 8,
              }}>
                <span style={{ color: 'var(--hint)', flexShrink: 0, minWidth: 120 }}>{label}</span>
                <span style={{
                  fontWeight: 500, textAlign: 'end',
                  ...(authorized ? {} : { filter: 'blur(5px)', userSelect: 'none' }),
                }}>{val}</span>
              </div>
            ))}
            {/* Yad2 button — active for authorized, disabled for others */}
            {authorized && marketData.yad2_url ? (
              <a href={marketData.yad2_url} target="_blank" rel="noopener noreferrer" style={{
                display: 'block', marginTop: 10, padding: '8px 0',
                background: '#FF4301', color: '#fff',
                borderRadius: 10, textAlign: 'center', fontSize: 13,
                fontWeight: 700, textDecoration: 'none',
              }}>חפש ב-Yad2</a>
            ) : (
              <div style={{
                display: 'block', marginTop: 10, padding: '8px 0',
                background: '#55555544', color: 'var(--hint)',
                borderRadius: 10, textAlign: 'center', fontSize: 13,
                fontWeight: 700, cursor: 'not-allowed',
              }}>חפש ב-Yad2</div>
            )}
            {/* Facebook Marketplace button — always active, search in English */}
            {(() => {
              const makeEn  = MAKE_EN[make]  || make
              const modelEn = MODEL_EN[model] || model
              const query = [makeEn, modelEn, year].filter(Boolean).join(' ')
              if (!query) return null
              const fbUrl = `https://www.facebook.com/marketplace/search/?query=${encodeURIComponent(query)}&category_id=vehicles`
              return (
                <a href={fbUrl} target="_blank" rel="noopener noreferrer" style={{
                  display: 'block', marginTop: 8, padding: '8px 0',
                  background: '#1877F2', color: '#fff',
                  borderRadius: 10, textAlign: 'center', fontSize: 13,
                  fontWeight: 700, textDecoration: 'none',
                }}>חפש ב-Facebook Marketplace</a>
              )
            })()}
          </div>
        )
      })()}

      {/* ── Yad2 Watch ── */}
      {user?.show_watch && make && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
            <div>
              <div style={{
                display: 'inline-block', fontSize: 11, fontWeight: 700,
                background: '#8b5cf6', color: '#fff',
                borderRadius: 20, padding: '4px 10px', marginBottom: 6,
              }}>למנויים בלבד</div>
              <div style={{ fontWeight: 700, fontSize: 15 }}>🔔 התראות יד2</div>
            </div>
            {user?.watch_public_label && (
              <div style={{ fontSize: 11, color: 'var(--hint)', textAlign: 'left', whiteSpace: 'nowrap' }}>
                {user.watch_public_label}
              </div>
            )}
          </div>
          <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 12 }}>
            קבל התראה בטלגרם כשתתווסף מודעה חדשה ל-Yad2 עבור <strong>{[make, model, year].filter(Boolean).join(' ')}</strong>
          </div>
          {(watchState === 'exists') ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ textAlign: 'center', color: '#38bdf8', fontWeight: 700, fontSize: 14, padding: '4px 0' }}>
                🔔 מעקב פעיל לרכב זה
              </div>
              <button
                onClick={() => onBack('watches')}
                style={{
                  display: 'block', width: '100%', padding: '9px 0',
                  background: '#8b5cf622', color: '#a78bfa',
                  borderRadius: 10, fontSize: 13, fontWeight: 600,
                  border: '1px solid #8b5cf644', cursor: 'pointer',
                }}
              >📋 עבור לרשימת המעקבים שלי</button>
            </div>
          ) : watchState === 'done' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ textAlign: 'center', color: '#38a169', fontWeight: 700, fontSize: 14, padding: '4px 0' }}>
                ✅ המעקב נוסף בהצלחה!
              </div>
              <button
                onClick={() => onBack('watches')}
                style={{
                  display: 'block', width: '100%', padding: '9px 0',
                  background: '#8b5cf622', color: '#a78bfa',
                  borderRadius: 10, fontSize: 13, fontWeight: 600,
                  border: '1px solid #8b5cf644', cursor: 'pointer',
                }}
              >📋 עבור לרשימת המעקבים שלי</button>
            </div>
          ) : watchState === 'error' ? (
            <div style={{ textAlign: 'center', color: '#e53e3e', fontSize: 13, padding: '8px 0' }}>
              ❌ שגיאה בהוספת המעקב. ייתכן שהגעת למגבלת המעקבים.
            </div>
          ) : (
            <button
              onClick={async () => {
                setWatchState('loading')
                try {
                  await createUserWatch({ make, model, year: year ? parseInt(year) : null })
                  setWatchState('done')
                } catch {
                  setWatchState('error')
                }
              }}
              disabled={watchState === 'loading'}
              style={{
                display: 'block', width: '100%', padding: '9px 0',
                background: watchState === 'loading' ? '#55555544' : '#8b5cf6',
                color: watchState === 'loading' ? 'var(--hint)' : '#fff',
                borderRadius: 10, fontSize: 13, fontWeight: 700,
                border: 'none', cursor: watchState === 'loading' ? 'not-allowed' : 'pointer',
              }}
            >
              {watchState === 'loading' ? '⏳ מוסיף מעקב...' : '🔔 הוסף מעקב ביד2'}
            </button>
          )}
        </div>
      )}

      {/* ── General ── */}
      <Sec title="📋 פרטים כלליים">
        <Row label="יצרן" value={make} />
        <Row label="דגם" value={model} />
        <Row label="רמת גימור" value={w.ramat_gimur} />
        <Row label="שנת ייצור" value={year} />
        <Row label="צבע" value={color} />
        <Row label="בעלות נוכחית" value={record.baalut} />
        <Row label="ארץ ייצור" value={w.tozeret_eretz_nm} />
        <Row label="יבואן" value={w.tozar} />
        <Row label="סוג מרכב" value={w.merkav} />
        <Row label="סוג תקינה" value={w.sug_tkina_nm} />
        <Row label="מסגרת (שלדה)" value={record.misgeret} />
        <Row label="דגם מנוע" value={record.degem_manoa} />
        <Row label="מספר מנוע" value={record.mispar_manoa} />
        <Row label="מקוריות" value={record.mkoriut_nm} />
        {record._personal_import && (
          <Row label="יבוא" value={record._personal_import.sug_yevu || 'יבוא אישי'} />
        )}
      </Sec>

      {/* ── Tech specs ── */}
      <Sec title="⚙️ מפרט טכני">
        <Row label="סוג דלק" value={record.sug_delek_nm} />
        <Row label="טכנולוגיית הנעה" value={w.technologiat_hanaa_nm} />
        <Row label="סוג הנעה" value={w.hanaa_nm} />
        <Row label='נפח מנוע (סמ"ק)' value={engineCc} />
        <Row label="כוח סוס" value={w.koah_sus} />
        <Row label="תיבת הילוכים" value={gearbox} />
        <Row label="סוג ממיר" value={w.sug_mamir_nm} />
        <Row label="מושבים" value={w.mispar_moshavim} />
        <Row label="דלתות" value={w.mispar_dlatot} />
        <Row label='משקל כולל (ק"ג)' value={weight} />
        <Row label='גובה (מ"מ)' value={height} />
        <Row label='גרירה עם בלמים (ק"ג)' value={towWith} />
        <Row label='גרירה ללא בלמים (ק"ג)' value={towWithout} />
      </Sec>

      {/* ── Tires ── */}
      <Sec title="🔧 גלגלים וצמיגים">
        <Row label="צמיג קדמי" value={record.zmig_kidmi} />
        <Row label="צמיג אחורי" value={record.zmig_ahori || record.zmig_achori} />
        <Row label="עומס צמיג קדמי" value={record.kod_omes_tzmig_kidmi} />
        <Row label="עומס צמיג אחורי" value={record.kod_omes_tzmig_ahori} />
        <Row label="מהירות צמיג קדמי" value={record.kod_mehirut_tzmig_kidmi} />
        <Row label="מהירות צמיג אחורי" value={record.kod_mehirut_tzmig_ahori} />
        <Row label="וו גרירה" value={record.grira_nm} />
      </Sec>

      {/* ── Equipment ── */}
      <Sec title="🛋️ ציוד ונוחות">
        <Row label="מיזוג אוויר" value={yn(w.mazgan_ind)} />
        <Row label="הגה כוח" value={yn(w.hege_koah_ind)} />
        <Row label="חלונות חשמל"
          value={w.mispar_halonot_hashmal ? `${w.mispar_halonot_hashmal} חלונות` : null} />
        <Row label="גג פנורמי/שמש" value={yn(w.halon_bagg_ind)} />
        <Row label="חישוקי סגסוגת" value={yn(w.galgaley_sagsoget_kala_ind)} />
        <Row label="ארגז/תא מטען" value={yn(w.argaz_ind)} />
      </Sec>

      {/* ── Safety ── */}
      <Sec title="🛡️ בטיחות ופליטות">
        <Row label="ניקוד בטיחות" value={w.nikud_betihut} />
        <Row label="רמת ציוד בטיחותי" value={w.ramat_eivzur_betihuty} />
        <Row label="כריות אוויר"
          value={w.mispar_kariot_avir ? `${w.mispar_kariot_avir} כריות` : null} />
        <Row label="ABS" value={yn(w.abs_ind)} />
        <Row label="ESP" value={yn(w.bakarat_yatzivut_ind)} />
        <Row label="קבוצת זיהום" value={record.kvutzat_zihum || record.kvuzat_zihum} />
        <Row label="מדד ירוק" value={w.madad_yarok} />
        <Row label='CO₂ WLTP (גר/ק"מ)' value={w.CO2_WLTP || w.kamut_CO2} />
        <Row label="CO₂ NEDC" value={w.CO2_WLTP_NEDC} />
        <Row label="CO₂ בעיר" value={w.kamut_CO2_city} />
        <Row label="CO₂ בכביש" value={w.kamut_CO2_hway} />
        <Row label="NOX" value={w.NOX_WLTP || w.kamut_NOX} />
        <Row label="HC" value={w.HC_WLTP || w.kamut_HC} />
        <Row label="PM10" value={w.PM_WLTP || w.kamut_PM10} />
        <Row label="CO" value={w.CO_WLTP || w.kamut_CO} />
      </Sec>

      {/* ── ADAS ── */}
      <Sec title="🤖 מערכות ADAS">
        <Row label="שמירת נתיב" value={yn(w.bakarat_stiya_menativ_ind)} />
        <Row label="בקרת סטייה אקטיבית" value={yn(w.bakarat_stiya_activ_s)} />
        <Row label="ניטור מרחק קדמי" value={yn(w.nitur_merhak_milfanim_ind)} />
        <Row label="זיהוי שטח עיוור" value={yn(w.zihuy_beshetah_nistar_ind)} />
        <Row label="בקרת שיוט אדפטיבית" value={yn(w.bakarat_shyut_adaptivit_ind)} />
        <Row label="בקרת מהירות ISA" value={yn(w.bakarat_mehirut_isa)} />
        <Row label="זיהוי הולכי רגל" value={yn(w.zihuy_holchey_regel_ind)} />
        <Row label="בלימת חירום אוטומטית" value={yn(w.maarechet_ezer_labalam_ind)} />
        <Row label="בלימה לפני הולכי רגל" value={yn(w.blimat_hirum_lifnei_holhei_regel_ofanaim)} />
        <Row label="בלימה אוטו' לאחור" value={yn(w.blima_otomatit_nesia_leahor)} />
        <Row label="מצלמת רוורס" value={yn(w.matzlemat_reverse_ind)} />
        <Row label="חיישני לחץ צמיגים" value={yn(w.hayshaney_lahatz_avir_batzmigim_ind)} />
        <Row label="חיישן עייפות נהג" value={yn(w.hayshaney_hagorot_ind)} />
        <Row label="זיהוי תמרורים" value={yn(w.zihuy_tamrurey_tnua_ind)} />
        <Row label="שליטה אוטו' בפנסי גבוה" value={yn(w.shlita_automatit_beorot_gvohim_ind)} />
        <Row label="התראת נסיעה קדימה" value={yn(w.teura_automatit_benesiya_kadima_ind)} />
        <Row label="זיהוי התקרבות מסוכנת" value={yn(w.zihuy_matzav_hitkarvut_mesukenet_ind)} />
        <Row label="זיהוי אופניים/קורקינט" value={yn(w.zihuy_rechev_do_galgali)} />
        <Row label="נעילת אלכוהול" value={yn(w.alco_lock)} />
        <Row label="מתח סולל" value={w.dg_metach_solela} />
      </Sec>

      {/* ── History ── */}
      <Sec title="📅 היסטוריה ורישום">
        <Row label="רישום ראשון" value={fmtDate(record.rishum_rishon_dt)} />
        <Row label="עלייה לכביש" value={fmtDate(record.moed_aliya_lakvish)} />
        <Row label='ק"מ בטסט אחרון'
          value={km ? `${Number(km).toLocaleString('he-IL')} ק"מ` : null} />
        <Row label="טסט אחרון" value={fmtDate(record.mivchan_acharon_dt)} />
        <Row label="תוקף טסט" value={testStr} />
        <Row label="שינוי מבנה" value={yn(record.shinui_mivne_ind)} />
        <Row label="שינוי צבע" value={yn(record.shnui_zeva_ind)} />
        <Row label="שינוי צמיגים" value={yn(record.shinui_zmig_ind)} />
        <Row label="GAPAM" value={yn(record.gapam_ind)} />
        <Row label="תו נכה" value={record._tag_nache ? '✅ כן' : '❌ לא'} />
        {scrapped && <Row label="תאריך גרוטאה" value={fmtDate(scrapped)} />}
      </Sec>

      {/* ── Ownership history ── */}
      {ownership.length > 0 && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10 }}>👥 היסטוריית בעלויות</div>
          <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
            {[
              { label: 'סה"כ', val: ownership.length },
              { label: 'פרטיות', val: ownership.filter(o => o.baalut === 'פרטי').length },
              { label: 'דרך סוחר', val: ownership.filter(o => o.baalut === 'סוחר').length },
            ].map(({ label, val }) => (
              <div key={label} className="stat-card" style={{ flex: 1, padding: 10 }}>
                <div className="stat-value" style={{ fontSize: 20 }}>{val}</div>
                <div className="stat-label">{label}</div>
              </div>
            ))}
          </div>
          {ownership.map((o, i) => {
            const emoji = o.baalut === 'פרטי' ? '👤' : o.baalut === 'סוחר' ? '🏢' : '❓'
            return (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '6px 0', borderBottom: '1px solid var(--bg)', fontSize: 14,
              }}>
                <span style={{ color: 'var(--hint)' }}>{i + 1}. {emoji} {o.baalut || '?'}</span>
                <span style={{ fontWeight: 500 }}>{fmtBaalutDt(o.baalut_dt)}</span>
              </div>
            )
          })}
        </div>
      )}

      {/* ── Recalls ── */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10 }}>
          🔔 ריקולים{recalls.length > 0 ? ` (${recalls.length})` : ''}
          {recalls.length > 0 && (
            <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--hint)', marginRight: 6 }}>
              {recallsByPlate ? '— ספציפי ללוחית' : '— לדגם'}
            </span>
          )}
        </div>
        {recalls.length === 0 ? (
          <div style={{ fontSize: 13, color: 'var(--hint)' }}>✅ לא נמצאו ריקולים</div>
        ) : recalls.map((r, i) => (
          <div key={i} style={{
            padding: '8px 0', borderBottom: i < recalls.length - 1 ? '1px solid var(--bg)' : 'none',
            fontSize: 13,
          }}>
            {recallsByPlate ? (
              <>
                <div style={{ fontWeight: 600 }}>
                  {r.TAARICH_PTICHA ? String(r.TAARICH_PTICHA).substring(0, 10) : ''}
                  {r.SUG_TAKALA ? ` · ${r.SUG_TAKALA}` : ''}
                </div>
                <div style={{ marginTop: 2 }}>{r.TEUR_TAKALA || ''}</div>
                {r.SUG_RECALL && <div style={{ color: 'var(--hint)', marginTop: 2 }}>סוג: {r.SUG_RECALL}</div>}
              </>
            ) : (
              <>
                <div style={{ fontWeight: 600 }}>{r.SHNAT_RECALL || ''}</div>
                <div style={{ marginTop: 2 }}>{r.TEUR_TAKALA || ''}</div>
                {r.OFEN_TIKUN && <div style={{ color: 'var(--hint)', marginTop: 2 }}>תיקון: {r.OFEN_TIKUN}</div>}
                {r.TELEPHONE && <div style={{ color: 'var(--hint)', marginTop: 2 }}>📞 {r.TELEPHONE}</div>}
              </>
            )}
          </div>
        ))}
      </div>

      {/* ── PDF Report + Notes ── */}
      {(() => {
        const authorized = !!user?.show_pdf_report
        async function handleDownload() {
          setPdfLoading(true)
          try {
            if (note.trim()) await saveNote(plateNum, note)
            await requestPdfReport(plateNum)
            setPdfSent(true)
          } catch {
            window.Telegram?.WebApp?.showAlert('שגיאה ביצירת הדוח. נסה שוב.')
          } finally {
            setPdfLoading(false)
          }
        }
        async function handleNoteSave() {
          setNoteSaving(true)
          try {
            await saveNote(plateNum, note)
            setNoteSaved(true)
            setNoteDirty(false)
            setTimeout(() => setNoteSaved(false), 2000)
          } catch { /* silent */ }
          setNoteSaving(false)
        }
        return (
          <div className="card" style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
              <div>
                <div style={{
                  display: 'inline-block', fontSize: 11, fontWeight: 700,
                  background: '#8b5cf6', color: '#fff',
                  borderRadius: 20, padding: '4px 10px', marginBottom: 6,
                }}>למנויים בלבד</div>
                <div style={{ fontWeight: 700, fontSize: 15 }}>📄 דוח PDF + הערות אישיות</div>
              </div>
              {user?.pdf_public_label && (
                <div style={{ fontSize: 11, color: 'var(--hint)', textAlign: 'left', whiteSpace: 'nowrap' }}>
                  {user.pdf_public_label}
                </div>
              )}
            </div>

            {/* Notes */}
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 6, fontWeight: 600 }}>
                📝 הערות אישיות לרכב זה
              </div>
              {authorized ? (
                <>
                  <textarea
                    value={note}
                    onChange={e => { setNote(e.target.value); setNoteDirty(true) }}
                    rows={4}
                    style={{
                      width: '100%', boxSizing: 'border-box',
                      background: 'var(--bg)', border: `1px solid ${noteDirty ? '#8b5cf6' : 'rgba(255,255,255,0.12)'}`,
                      borderRadius: 10, padding: '10px 12px', color: 'var(--text)',
                      fontSize: 14, lineHeight: 1.6, resize: 'vertical',
                      fontFamily: 'inherit', direction: 'rtl',
                    }}
                    placeholder={'מחיר סגירה 70,000\nטלפון 052-12345678\nמול אמיר.'}
                  />
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                    {noteDirty && (
                      <button
                        onClick={handleNoteSave}
                        disabled={noteSaving}
                        style={{
                          padding: '7px 18px', borderRadius: 8, border: 'none',
                          background: '#8b5cf6', color: '#fff', fontSize: 13,
                          fontWeight: 600, cursor: 'pointer', opacity: noteSaving ? 0.6 : 1,
                        }}
                      >{noteSaving ? '...' : '💾 שמור הערה'}</button>
                    )}
                    {noteSaved && (
                      <span style={{ fontSize: 11, color: '#38a169' }}>✅ נשמר</span>
                    )}
                  </div>
                </>
              ) : note ? (
                <div style={{
                  background: 'var(--bg)', borderRadius: 10, padding: '10px 12px',
                  fontSize: 14, color: 'var(--hint)', lineHeight: 1.6, direction: 'rtl',
                  whiteSpace: 'pre-wrap',
                }}>{note}</div>
              ) : (
                <div style={{
                  fontSize: 12, color: 'rgba(255,255,255,0.25)', fontStyle: 'italic',
                  padding: '8px 0',
                }}>🔒 הערות אישיות — זמין למנויים</div>
              )}
            </div>

            <div style={{ height: 1, background: 'rgba(255,255,255,0.07)', margin: '0 0 12px' }} />

            {/* Download */}
            <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 8, lineHeight: 1.5 }}>
              דוח PDF מלא כולל הערות אישיות — יישלח לצ'אט שלך לשמירה ולשיתוף.
            </div>
            {authorized ? (
              pdfSent ? (
                <div style={{
                  width: '100%', padding: '10px 0', borderRadius: 10,
                  background: '#1a4731', color: '#38a169',
                  textAlign: 'center', fontSize: 14, fontWeight: 700, marginBottom: 8,
                }}>✅ הדוח נשלח לצ'אט שלך!</div>
              ) : (
                <button
                  onClick={handleDownload}
                  disabled={pdfLoading}
                  style={{
                    width: '100%', padding: '10px 0', border: 'none', borderRadius: 10,
                    background: pdfLoading ? '#444' : 'linear-gradient(135deg,#4c1d95,#7c3aed)',
                    color: '#fff', fontSize: 14, fontWeight: 700, cursor: pdfLoading ? 'default' : 'pointer',
                    marginBottom: 8,
                  }}
                >
                  {pdfLoading ? '⏳ מכין דוח...' : '📤 שלח דוח PDF לצ\'אט'}
                </button>
              )
            ) : (
              <div style={{
                width: '100%', padding: '10px 0', borderRadius: 10,
                background: '#55555544', color: 'var(--hint)',
                textAlign: 'center', fontSize: 14, fontWeight: 700, cursor: 'not-allowed',
                marginBottom: 8,
              }}>📥 הורד דוח PDF</div>
            )}
            <button
              className="btn btn-secondary"
              style={{ width: '100%', marginTop: 0 }}
              onClick={handleCopy}
            >
              {copied ? '✅ הועתק!' : '📋 העתק דוח'}
            </button>
          </div>
        )
      })()}

      {/* ── Actions ── */}
      <button className="btn btn-secondary" style={{ marginBottom: 20 }}
        onClick={() => window.Telegram?.WebApp?.close()}>
        סגור
      </button>

      </> /* end full tab */}
    </div>
  )
}
