import BackButton from '../components/BackButton.jsx'

export default function LeviInfoPage({ onBack, onPrivacy }) {
  return (
    <div className="page" style={{ paddingBottom: 32 }}>
      <BackButton onClick={onBack} />
      <h1 className="page-title">📗 מחירון לוי יצחק</h1>

      <div style={{
        background: 'linear-gradient(135deg,#15803d,#166534)',
        borderRadius: 16, padding: '18px 18px', marginBottom: 16, color: '#fff', textAlign: 'center',
      }}>
        <div style={{ fontSize: 36, marginBottom: 8 }} aria-hidden="true">📗</div>
        <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>הערכת מחיר לרכב יד שנייה לפי מחירון לוי יצחק</div>
        <div style={{ fontSize: 13 }}>מההזדהות ועד המחיר — ישירות מהבוט</div>
      </div>

      <Section title="❓ למה מחירון לוי יצחק?">
        <p style={P}>
          לפני קנייה, מכירה או החלפת רכב, כדאי לדעת בערך כמה שווה רכב דומה בשוק — ולא רק מה שמופיע ברישוי של משרד התחבורה.
          מחירון לוי יצחק (levi-itzhak.co.il) הוא מקור מקובל בישראל להערכת מחיר רכב יד שנייה לפי דגם ושנה.
        </p>
        <p style={P}>
          זה שונה מדוח הרכב של CarInfo (רישוי, טסט, ק״מ בביקורת, ריקולים — מנתוני הממשלה) ומשווי השוק לפי מודעות Yad2.
        </p>
      </Section>

      <Section title="⚡ איך זה עובד">
        <Step num="1" text="מחפשים רכב בבוט ולוחצים על ״📗 מחירון לוי יצחק״ בכרטיס התוצאה" />
        <Step num="2" text="בפעם הראשונה מזדהים מול לוי יצחק, כמו באפליקציה שלהם: שולחים מספר נייד" />
        <Step num="3" text="לוי יצחק שולחים SMS עם קוד בן 6 ספרות — מקלידים אותו בבוט" />
        <Step num="4" text="הבוט ממשיך ישר לרכב שחיפשת ומציג את מחיר המחירון לדגם. בפעמים הבאות אין צורך להזדהות שוב, עד שההתחברות פגה או שמתנתקים" />
      </Section>

      <Section title="📋 מה מוצג">
        <Row icon="🔎" text="זיהוי הדגם והגרסה במחירון לפי לוחית הרישוי" />
        <Row icon="💰" text="מחיר מחירון בסיס לדגם ולשנה" />
        <Row icon="⭐" text="הכלי זמין למנויים, ופתיחתו נתונה לשיקול דעת המפעיל" />
      </Section>

      <Section title="🚫 מה הכלי לא נותן">
        <Row icon="📄" text="לא דוח רישוי, עבר תביעות או בדיקת גניבה — לכך יש את דוח הרכב הרגיל" />
        <Row icon="⚖️" text="לא אישור רשמי למכירה, לביטוח או למימון — רק הערכה לפי מחירון" />
        <Row icon="🧑‍🔧" text="לא מחליף שמאי, סוכן או בדיקה מכנית. לפני עסקה גדולה כדאי לאמת באתר לוי יצחק או מול יועץ" />
        <p style={{ ...P, color: 'var(--hint)', fontSize: 12 }}>
          CarInfo הוא שירות עצמאי ואינו קשור ללוי יצחק. המחיר המוצג מגיע ממחירון לוי יצחק ועשוי להשתנות או להיות שונה ממחיר המכירה בפועל.
        </p>
      </Section>

      <Section title="🔒 פרטיות והנתונים שלך">
        <Row icon="📱" text="מספר הנייד והקוד שאתה מקליד עוברים ללוי יצחק לצורך האימות, דרך השרת שמפעיל את הבוט" />
        <Row icon="💾" text="אצלנו נשמרים רק מספר הנייד, מזהה מכשיר טכני ואסימון הגישה שלוי יצחק מחזירים — כדי שלא תצטרך SMS בכל בדיקה" />
        <Row icon="🔢" text="קוד ה־SMS עצמו לא נשמר אצלנו" />
        <Row icon="📊" text="תוצאות בדיקות המחירון לא נשמרות אצלנו" />
        <Row icon="🗑️" text="אפשר להתנתק ולמחוק את הנתונים האלה בכל רגע עם הפקודה /levi_logout בבוט, או על ידי מחיקת החשבון" />
        <p style={{ ...P, color: 'var(--hint)', fontSize: 12 }}>
          ההתחברות היא לחשבון שלך מול לוי יצחק, והם מחליטים עד מתי היא תקפה. אם היא פגה, הבוט יבקש להזדהות מחדש.
        </p>
      </Section>

      <div style={{ textAlign: 'center', marginTop: 8 }}>
        <button
          onClick={onPrivacy}
          style={{ background: 'none', border: 'none', color: 'var(--hint)', fontSize: 12, cursor: 'pointer', textDecoration: 'underline', padding: '12px 8px', minHeight: 44 }}
        >
          🔒 מדיניות פרטיות ותנאי שימוש
        </button>
      </div>
    </div>
  )
}

const P = { fontSize: 14, lineHeight: 1.7, margin: 0 }

function Section({ title, children }) {
  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 10, borderBottom: '1px solid rgba(0,100,200,0.1)', paddingBottom: 8 }}>
        {title}
      </h2>
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
