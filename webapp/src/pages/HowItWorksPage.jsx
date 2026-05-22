export default function HowItWorksPage({ onBack, freeSearches = 10 }) {
  return (
    <div className="page" style={{ paddingBottom: 32 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <button
          onClick={onBack}
          style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: 'var(--btn)', padding: '0 4px' }}
          aria-label="חזרה"
        >
          ›
        </button>
        <div className="page-title" style={{ margin: 0 }}>ℹ️ איך CarInfo עובד?</div>
      </div>

      <Section title="🔍 מה מוצג על כל רכב">
        <Row icon="🚗" text="פרטים כלליים — יצרן, דגם, שנה, צבע, מסגרת" />
        <Row icon="⚙️" text="מפרט טכני — מנוע, הנעה, הילוכים, דלק, כוח סוס" />
        <Row icon="🛞" text="גלגלים וצמיגים" />
        <Row icon="🪑" text="ציוד ונוחות — מיזוג, הגה כוח, חלונות חשמל" />
        <Row icon="🛡️" text="בטיחות ופליטות — ABS, ESP, כריות אוויר, CO₂" />
        <Row icon="🤖" text="מערכות ADAS — בלימה אוטומטית, שמירת נתיב ועוד" />
        <Row icon="📅" text="היסטוריה — רישום, טסט, ק״מ, שינויי מבנה" />
        <Row icon="👥" text="היסטוריית בעלויות — כמה בעלים, פרטי/סוחר" />
        <Row icon="⚠️" text="ריקולים — תקלות ידועות של הדגם" />
        <Row icon="🚨" text="בדיקת גנבה — מאגר המשטרה לרכבים גנובים" />
      </Section>

      <Section title="🆓 חיפושים חינמיים">
        <p style={{ fontSize: 14, lineHeight: 1.7 }}>
          כל משתמש חדש מקבל <strong>{freeSearches} חיפושים חינמיים</strong> לניסיון ללא עלות.
        </p>
      </Section>

      <Section title="💡 איך משתמשים?">
        <p style={{ fontSize: 14, lineHeight: 1.7 }}>
          שלח מספר לוחית רישוי (לדוגמה: <strong>1234567</strong>) לבוט בטלגרם,
          והמערכת תחזיר לך דוח מלא תוך שניות.
        </p>
      </Section>

      <Section title="📦 חבילות חיפוש">
        <p style={{ fontSize: 14, lineHeight: 1.7 }}>
          לאחר שמיצית את החיפושים החינמיים, ניתן לרכוש חבילת חיפושים נוספת בעמוד הרכישה.
        </p>
      </Section>

      <Section title="🔗 מקורות המידע">
        <Row icon="🏛️" text="data.gov.il — פורטל הנתונים הפתוחים של ממשלת ישראל" />
        <Row icon="👮" text="מאגר רכבים גנובים — מערכת המשטרה" />
        <Row icon="🏷️" text="Yad2 — מחירי שוק ומודעות מכירה" />
      </Section>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 10, borderBottom: '1px solid var(--bg)', paddingBottom: 8 }}>
        {title}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {children}
      </div>
    </div>
  )
}

function Row({ icon, text }) {
  return (
    <div style={{ display: 'flex', gap: 8, fontSize: 14, lineHeight: 1.5 }}>
      <span style={{ flexShrink: 0 }}>{icon}</span>
      <span>{text}</span>
    </div>
  )
}
