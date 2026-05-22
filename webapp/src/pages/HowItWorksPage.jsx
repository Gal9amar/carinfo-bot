export default function HowItWorksPage({ onBack, freeSearches = 10, onPrivacy }) {
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

      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg,#2481cc,#1a5fa8)',
        borderRadius: 16, padding: '18px 18px', marginBottom: 16, color: '#fff', textAlign: 'center',
      }}>
        <div style={{ fontSize: 36, marginBottom: 8 }}>🚗</div>
        <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>הבוט החכם לבדיקת רכבים בישראל</div>
        <div style={{ fontSize: 13, opacity: 0.85 }}>שלח מספר לוחית רישוי — קבל דוח מלא תוך שניות</div>
      </div>

      {/* Steps */}
      <Section title="⚡ שלושה צעדים פשוטים">
        <Step num="1" text="שלח מספר לוחית רישוי לבוט (לדוגמה: 1234567)" />
        <Step num="2" text="המערכת שולפת נתונים ממקורות ממשלתיים ועסקיים" />
        <Step num="3" text="תוך שניות מגיע דוח מקיף עם כל הפרטים" />
      </Section>

      {/* What you get */}
      <Section title="📋 מה מוצג על כל רכב">
        <Row icon="🚗" text="פרטים כלליים — יצרן, דגם, שנה, צבע, מסגרת" />
        <Row icon="⚙️" text="מפרט טכני — מנוע, הנעה, הילוכים, דלק, כוח סוס" />
        <Row icon="🛞" text="גלגלים וצמיגים — מידות ודגמים" />
        <Row icon="🪑" text="ציוד ונוחות — מיזוג, הגה כוח, חלונות חשמל" />
        <Row icon="🛡️" text="בטיחות ופליטות — ABS, ESP, כריות אוויר, CO₂" />
        <Row icon="🤖" text="מערכות ADAS — בלימה אוטומטית, שמירת נתיב ועוד" />
        <Row icon="📅" text="היסטוריה — רישום, טסט, ק״מ, שינויי מבנה" />
        <Row icon="👥" text="היסטוריית בעלויות — כמה בעלים, פרטי/סוחר" />
        <Row icon="💰" text="הערכת מחיר שוק — על בסיס מודעות Yad2" />
        <Row icon="🚨" text="בדיקת גנבה — מאגר המשטרה לרכבים גנובים" />
        <Row icon="⚠️" text="ריקולים — תקלות ידועות ופתוחות של הדגם" />
      </Section>

      {/* Free searches */}
      <Section title="🆓 חיפושים חינמיים">
        <p style={{ fontSize: 14, lineHeight: 1.7, margin: 0 }}>
          כל משתמש חדש מקבל <strong>{freeSearches} חיפושים חינמיים</strong> לניסיון ללא עלות.
        </p>
      </Section>

      {/* Referral */}
      <Section title="🎁 קבל חיפושים במתנה">
        <Row icon="🔗" text="שתף את הלינק האישי שלך עם חברים" />
        <Row icon="👤" text="כל חבר שמצטרף לבוט דרך הלינק שלך" />
        <Row icon="✅" text={`מוסיף לך חיפושים אוטומטית — בלי לעשות כלום`} />
        <p style={{ fontSize: 13, color: 'var(--hint)', margin: '8px 0 0', lineHeight: 1.5 }}>
          לחץ על "🎁 קבל חיפושים במתנה" בתפריט הראשי לשיתוף הלינק שלך.
        </p>
      </Section>

      {/* Packages */}
      <Section title="📦 חבילות חיפוש">
        <p style={{ fontSize: 14, lineHeight: 1.7, margin: 0 }}>
          לאחר שמיצית את החיפושים החינמיים, ניתן לרכוש חבילת חיפושים נוספת בעמוד הרכישה.
          התשלום מתבצע דרך PayPal ומאושר ידנית — החיפושים מתווספים לחשבון מיד לאחר האישור.
        </p>
      </Section>

      {/* Access codes */}
      <Section title="🔑 קודי גישה">
        <p style={{ fontSize: 14, lineHeight: 1.7, margin: 0 }}>
          קיבלת קוד גישה? שלח <strong>/code XXXXXXXX</strong> לבוט והחיפושים יתווספו לחשבונך אוטומטית.
          קודים יכולים להיות חד-פעמיים או לשימוש מרובה — תלוי בסוג שקיבלת.
        </p>
      </Section>

      {/* Support */}
      <Section title="🎫 תמיכה">
        <p style={{ fontSize: 14, lineHeight: 1.7, margin: 0 }}>
          נתקלת בבעיה? פתח טיקט תמיכה דרך כפתור <strong>"תמיכה"</strong> בתפריט.
          הצוות יחזור אליך בהקדם ישירות בבוט.
        </p>
      </Section>

      {/* Sources */}
      <Section title="🔗 מקורות המידע">
        <Row icon="🏛️" text="data.gov.il — פורטל הנתונים הפתוחים של ממשלת ישראל" />
        <Row icon="👮" text="מאגר רכבים גנובים — מערכת המשטרה" />
        <Row icon="🏷️" text="Yad2 — מחירי שוק ומודעות מכירה" />
      </Section>

      {/* Privacy link */}
      <div style={{ textAlign: 'center', marginTop: 8 }}>
        <button
          onClick={onPrivacy}
          style={{ background: 'none', border: 'none', color: 'var(--hint)', fontSize: 12, cursor: 'pointer', textDecoration: 'underline' }}
        >
          🔒 מדיניות פרטיות ותנאי שימוש
        </button>
      </div>
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

function Step({ num, text }) {
  return (
    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', fontSize: 14, lineHeight: 1.5 }}>
      <span style={{
        flexShrink: 0, width: 24, height: 24, borderRadius: '50%',
        background: 'var(--btn)', color: 'var(--btn-text)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, fontWeight: 700,
      }}>{num}</span>
      <span>{text}</span>
    </div>
  )
}
