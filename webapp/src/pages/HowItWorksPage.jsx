import BackButton from '../components/BackButton.jsx'
import PageBanners from '../components/PageBanners.jsx'

export default function HowItWorksPage({ onBack, freeSearches = 10, onPrivacy, onNavigate }) {
  return (
    <div className="page" style={{ paddingBottom: 32 }}>
      <BackButton onClick={onBack} />
      <div className="page-title">ℹ️ איך CarInfo עובד?</div>

      <PageBanners page="howItWorks" onNavigate={onNavigate} />

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
        <Row icon="💰" text="הערכת מחיר שוק על בסיס מודעות Yad2 — תכונת מנוי בלבד ⭐" />
        <Row icon="🚨" text="בדיקת גנבה — מאגר המשטרה לרכבים גנובים" />
        <Row icon="⚠️" text="ריקולים — תקלות ידועות ופתוחות של הדגם" />
      </Section>

      {/* Free searches */}
      <Section title="🆓 חיפושים חינמיים">
        <p style={{ fontSize: 14, lineHeight: 1.7, margin: 0 }}>
          משתמש חדש מקבל חיפושים חינמיים בהתאם להטבה התקפה במועד הצטרפותו.
          {freeSearches > 0 && <> כרגע: <strong>{freeSearches} חיפושים חינמיים</strong> לכל משתמש חדש.</>}
          המכסה נקבעת על-ידי המפעיל ועשויה להשתנות — החיפושים שהתקבלו תקפים לשימוש ללא הגבלת זמן.
        </p>
      </Section>

      {/* Referral */}
      <Section title="🎁 קבל חיפושים במתנה">
        <Row icon="🔗" text="שתף את הלינק האישי שלך עם חברים" />
        <Row icon="👤" text="כל חבר שמצטרף לבוט דרך הלינק שלך" />
        <Row icon="✅" text="מוסיף לך חיפושים אוטומטית — בלי לעשות כלום" />
        <p style={{ fontSize: 13, color: 'var(--hint)', margin: '8px 0 0', lineHeight: 1.5 }}>
          לחץ על "🎁 קבל חיפושים במתנה" בתפריט הראשי לשיתוף הלינק שלך.
        </p>
        <p style={{ fontSize: 12, color: 'var(--hint)', margin: '4px 0 0', lineHeight: 1.5 }}>
          * חיפושים שהתקבלו מהפניות אינם כוללים גישה לתכונות המיועדות למנויים.
        </p>
      </Section>

      {/* Packages */}
      <Section title="⭐ רכישת מנוי">
        <Row icon="🔍" text="רכישת מנוי מקנה סל חיפושים לשימוש בקצב שלך — ללא הגבלת זמן לניצול היתרה" />
        <Row icon="⭐" text="גישה לתכונות המיועדות למנויים בלבד — כגון מחיר שוק Yad2 ותכונות עתידיות" />
        <Row icon="💳" text="תשלום חד-פעמי בלבד — אין חיוב חוזר, אין מנוי אוטומטי" />
        <Row icon="🔓" text="המנוי תקף עד גמר יתרת החיפושים, ניתן לרכוש שוב ולצבור" />
        <p style={{ fontSize: 13, color: 'var(--hint)', margin: '8px 0 0', lineHeight: 1.5 }}>
          התשלום מתבצע דרך PayPal ומעובד אוטומטית — החיפושים מתווספים לחשבונך תוך שניות.
        </p>
      </Section>

      {/* Access codes */}
      <Section title="🔑 קודי גישה">
        <p style={{ fontSize: 14, lineHeight: 1.7, margin: 0 }}>
          קיבלת קוד גישה? שלח <strong>/code XXXXXXXX</strong> לבוט והחיפושים יתווספו לחשבונך אוטומטית.
          קודים יכולים להיות חד-פעמיים או לשימוש מרובה — תלוי בסוג שקיבלת.
        </p>
        <p style={{ fontSize: 12, color: 'var(--hint)', margin: '4px 0 0', lineHeight: 1.5 }}>
          * שימוש בקוד אינו מקנה סטטוס מנוי או גישה לתכונות מנוי.
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
