import BackButton from '../components/BackButton.jsx'

export default function GarageHowItWorksPage({ onBack, onNavigate }) {
  return (
    <div className="page" style={{ paddingBottom: 32 }}>
      <BackButton onClick={onBack} />
      <div className="page-title">❓ איך מנהלים רכבים שקניתי?</div>

      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg,#1e40af,#0ea5e9)',
        borderRadius: 16, padding: '18px 18px', marginBottom: 16, color: '#fff', textAlign: 'center',
      }}>
        <div style={{ fontSize: 36, marginBottom: 8 }}>🚘</div>
        <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>מעקב קנייה־מכירה לכל רכב</div>
        <div style={{ fontSize: 13, opacity: 0.9 }}>מחיר רכישה, הוצאות, מכירה ורווח/הפסד — הכל במקום אחד</div>
      </div>

      <Section title="🚗 קניתי רכב">
        <Step num="1" text='חפשו את הרכב בבוט, ובדוח המלא לחצו על "קניתי את הרכב הזה"' />
        <Step num="2" text="הזינו מחיר רכישה (שדה חובה)" />
        <Step num="3" text='ק"מ בזמן הרכישה והערות — לא חובה, אפשר להשלים גם מאוחר יותר' />
        <p style={{ fontSize: 13, color: 'var(--hint)', margin: '8px 0 0', lineHeight: 1.5 }}>
          הרכב יתווסף לטאב "🚘 רכבים שקניתי" עם תגית <strong>"במלאי שלי"</strong>.
        </p>
      </Section>

      <Section title="🔍 הצג פרטים">
        <Row icon="👆" text='לחיצה על אזור הלוחית/הכותרת בכרטיס פותחת וסוגרת את הפרטים המלאים' />
        <Row icon="📋" text="יצרן, דגם, שנה, צבע, בעלויות, תוקף טסט, תאריך רכישה ועוד" />
        <Row icon="📝" text='ההערות שהוספתם מוצגות בתחתית הפרטים' />
      </Section>

      <Section title="➕ הוסף הוצאה">
        <Row icon="🧾" text='כפתור "הוצאה" פותח טופס עם תיאור וסכום — לדוגמה "החלפת מצבר" ו-₪500' />
        <Row icon="📊" text='כל הוצאה מופיעה בטבלת המחירים מתחת למחיר הרכישה, ומצטרפת להון המושקע' />
        <Row icon="🗑️" text="אפשר למחוק הוצאה בודדת בכל שלב עם ה-✕ לצידה" />
      </Section>

      <Section title="💰 מכרתי">
        <Step num="1" text='לחצו על "מכרתי" בכרטיס הרכב' />
        <Step num="2" text="הזינו את סכום המכירה ואשרו" />
        <Step num="3" text='הרכב מסומן "✅ נמכר", והמערכת מחשבת רווח/הפסד נטו אוטומטית (מחיר מכירה פחות מחיר רכישה והוצאות)' />
      </Section>

      <Section title="📈 שווי שוק משוער">
        <p style={{ fontSize: 14, lineHeight: 1.7, margin: 0 }}>
          לרכבים שעדיין במלאי מוצג שווי שוק משוער לפי מודעות Yad2, יחד עם הרווח/הפסד הלא-ממומש אילו הייתם מוכרים כרגע —
          תכונת מנוי בלבד ⭐.
        </p>
      </Section>

      <Section title="✏️ עריכה ומחיקה">
        <Row icon="✏️" text="עדכון מחיר רכישה, ק״מ, מחיר מכירה (לאחר מכירה) והערות בכל שלב" />
        <Row icon="🗑️" text="מחיקת רכב מהרשימה — פעולה בלתי הפיכה, כולל כל ההוצאות שנוספו לו" />
      </Section>

      <Section title="📊 כרטיס הסיכום">
        <Row icon="🚘" text="כמות הרכבים במלאי וכמות שנמכרו" />
        <Row icon="💵" text="ההון המושקע כרגע ברכבים שבמלאי (מחיר רכישה + הוצאות)" />
        <Row icon="📈" text="סך הרווח/הפסד הממומש מכל הרכבים שנמכרו" />
      </Section>

      <Section title="🔀 סינון ומיון">
        <Row icon="🗂️" text='כפתורי "הכל / במלאי / נמכרו" לסינון הרשימה' />
        <Row icon="↕️" text='מיון לפי "החדש ביותר" או לפי "רווח" (לרכבים שנמכרו)' />
      </Section>

      {/* Suggest a feature */}
      <div className="card" style={{
        marginBottom: 12, textAlign: 'center',
        background: 'linear-gradient(135deg,#4c1d95,#7c3aed)', color: '#fff',
      }}>
        <div style={{ fontSize: 28, marginBottom: 6 }}>💡</div>
        <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>יש לך רעיון לפיצ'ר או שיפור?</div>
        <div style={{ fontSize: 13, opacity: 0.9, marginBottom: 14, lineHeight: 1.6 }}>
          נשמח לשמוע! פתחו פנייה קצרה ונבדוק את זה.
        </div>
        <button
          onClick={() => onNavigate('ticket')}
          style={{
            width: '100%', padding: '11px 0', border: 'none', borderRadius: 12,
            background: '#fff', color: '#4c1d95', fontSize: 14, fontWeight: 700, cursor: 'pointer',
          }}
        >🎫 פתח פנייה</button>
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
