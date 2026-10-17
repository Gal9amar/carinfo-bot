import BackButton from '../components/BackButton.jsx'

const LAST_UPDATED = '17/10/2026'
const CONTACT_EMAIL = 'carsreport22@gmail.com'
const BOT_HANDLE = '@israelcarinfobot'

export default function AccessibilityPage({ onBack, onContact }) {
  return (
    <div className="page" style={{ paddingBottom: 40 }}>
      {onBack && <BackButton onClick={onBack} />}
      <h1 className="page-title" style={{ fontSize: 17 }}>♿ הצהרת נגישות</h1>
      <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 16 }}>עודכן לאחרונה: {LAST_UPDATED}</div>

      <Section title="מחויבות לנגישות">
        <p>
          אנו רואים חשיבות בהנגשת השירות לכלל המשתמשים, לרבות אנשים עם מוגבלות, ופועלים
          לשפר את חוויית השימוש בו, בהתאם לחוק שוויון זכויות לאנשים עם מוגבלות, התשנ"ח-1998,
          ולתקנות שוויון זכויות לאנשים עם מוגבלות (התאמות נגישות לשירות), התשע"ג-2013.
        </p>
      </Section>

      <Section title="רמת הנגישות">
        <p>
          האפליקציה (Mini App) פועלת בתוך טלגרם. אנו שואפים לעמוד בדרישות התקן הישראלי
          ת"י 5568 (בהתאם להנחיות WCAG 2.0 ברמה AA). הנגשת השירות מתבצעת באופן הדרגתי,
          ו<strong>נכון למועד זה השירות נגיש באופן חלקי</strong> — טרם בוצע ביקורת נגישות מקצועית מלאה.
        </p>
      </Section>

      <Section title="התאמות שבוצעו">
        <ul>
          <li>ממשק בעברית עם כיווניות מימין לשמאל (RTL) והגדרת שפת העמוד</li>
          <li>אפשרות הגדלה והקטנה של התצוגה באמצעות מחוות זום של המכשיר</li>
          <li>התאמה למצב תצוגה בהיר וכהה לפי הגדרות טלגרם והמכשיר</li>
          <li>סימון בולט של האלמנט הממוקד בניווט במקלדת</li>
          <li>כיבוד הגדרת "הפחתת תנועה" של מערכת ההפעלה</li>
          <li>שימוש בכפתורים וטפסים סטנדרטיים התומכים בקוראי מסך</li>
          <li>מקביל לאפליקציה, ניתן לקבל את כל מידע הרכב בצ'אט טקסטואלי עם הבוט {BOT_HANDLE}</li>
        </ul>
      </Section>

      <Section title="מגבלות ידועות">
        <ul>
          <li>חלק מהאיקונים והתמונות (למשל תמונות רכב ובאנרים) ללא תיאור טקסטואלי מלא</li>
          <li>חלק מהצבעים עשויים שלא לעמוד ביחס ניגודיות מלא בכל מצב תצוגה</li>
          <li>פאנל הניהול מיועד למפעיל השירות בלבד ואינו מותאם במלואו</li>
          <li>תוכן ומנגנונים של טלגרם עצמה כפופים לנגישות שלה</li>
        </ul>
      </Section>

      <Section title="פנייה בנושא נגישות">
        <p>
          נתקלת בבעיית נגישות או שיש לך הצעה לשיפור? נשמח לשמוע ונשתדל להשיב תוך 14 ימי עבודה.
          במידת הצורך נציע חלופה נגישה לקבלת השירות.
        </p>
        <ul>
          <li>רכז נגישות: מפעיל השירות</li>
          <li>דוא"ל: <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a></li>
          <li>דרך הבוט בטלגרם: {BOT_HANDLE}</li>
        </ul>
        <p>בפנייה אנא ציין את תיאור הבעיה, העמוד שבו התרחשה והמכשיר/קורא המסך שבו נעשה שימוש.</p>
      </Section>

      {onContact && (
        <button className="btn" style={{ marginTop: 8 }} onClick={onContact}>✉️ פנייה בנושא נגישות</button>
      )}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <section className="card" style={{ marginBottom: 10 }}>
      <h2 style={{
        fontSize: 14, fontWeight: 700, margin: '0 0 8px', color: 'var(--text)',
        borderBottom: '1px solid rgba(0,100,200,0.1)', paddingBottom: 6,
      }}>{title}</h2>
      <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.75, display: 'flex', flexDirection: 'column', gap: 6 }}>
        {children}
      </div>
    </section>
  )
}
