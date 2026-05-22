export default function PrivacyPolicyPage({ onBack, onContact }) {
  return (
    <div className="page" style={{ paddingBottom: 32 }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 20, gap: 10 }}>
        {onBack && (
          <button
            onClick={onBack}
            style={{
              background: 'none',
              border: 'none',
              fontSize: 22,
              cursor: 'pointer',
              color: 'var(--btn)',
              padding: '0 4px',
            }}
            aria-label="חזרה"
          >
            ›
          </button>
        )}
        <div className="page-title" style={{ margin: 0 }}>🔒 מדיניות פרטיות</div>
      </div>

      <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 20 }}>
        עודכן לאחרונה: מאי 2026
      </div>

      <Section title="1. כללי">
        <p>
          ברוכים הבאים לבוט מידע על רכב ("השירות"). אנו מכבדים את פרטיותך ומחויבים להגן על
          המידע האישי שלך. מדיניות פרטיות זו מסבירה אילו נתונים אנו אוספים, כיצד אנו משתמשים
          בהם ואת זכויותיך בהתאם לחוק הגנת הפרטיות, התשמ"א-1981 ותקנותיו.
        </p>
      </Section>

      <Section title="2. המידע שאנו אוספים">
        <SubHeading>מידע שמועבר מטלגרם / ווטסאפ</SubHeading>
        <ul>
          <li>מזהה משתמש (User ID)</li>
          <li>שם פרטי ושם משפחה (כפי שמופיע בפרופיל)</li>
          <li>שם משתמש (username), אם קיים</li>
          <li>שפת הממשק</li>
        </ul>

        <SubHeading>מידע שנוצר בעת השימוש בשירות</SubHeading>
        <ul>
          <li>מספרי לוחיות רישוי שנחפשו</li>
          <li>מספר החיפושים שנותרו לך</li>
          <li>תאריך הצטרפות ותאריך פעילות אחרון</li>
          <li>פרטי רכישת חבילות (לא כולל פרטי תשלום מלאים)</li>
        </ul>

        <SubHeading>מידע שאינו נאסף</SubHeading>
        <ul>
          <li>פרטי כרטיס אשראי — תשלומים מבוצעים ישירות דרך PayPal</li>
          <li>מיקום גיאוגרפי</li>
          <li>תוכן הודעות פרטיות שאינן קשורות לחיפוש</li>
        </ul>
      </Section>

      <Section title="3. מקורות המידע על הרכב">
        <p>
          מידע על רכבים נשלף בזמן אמת ממקורות ציבוריים ורשמיים בלבד:
        </p>
        <ul>
          <li>
            <strong>data.gov.il</strong> — פורטל הנתונים הפתוחים של ממשלת ישראל (נתוני רישוי
            רכב ממשרד התחבורה)
          </li>
          <li>
            <strong>מאגר רכבים גנובים</strong> — מערכת המשטרה לבדיקת רכבים גנובים
          </li>
          <li>
            <strong>Yad2</strong> — נתוני מחירי שוק ומודעות מכירה (לפי זמינות)
          </li>
        </ul>
        <p>
          אנו לא שומרים את תוצאות החיפוש על שרתינו לאחר שנשלחו למשתמש.
        </p>
      </Section>

      <Section title="4. כיצד אנו משתמשים במידע">
        <ul>
          <li>מתן השירות — הצגת מידע על הרכב לפי מספר לוחית</li>
          <li>ניהול מכסת חיפושים ומנויים</li>
          <li>אישור תשלומים ועדכון חשבון</li>
          <li>שיפור השירות ואבטחתו</li>
          <li>שליחת התראות מערכת (למשל: אישור רכישה, תפוגת מכסה)</li>
          <li>מניעת שימוש לרעה ואכיפת תנאי השימוש</li>
        </ul>
        <p>
          <strong>אנו לא מוכרים, משכירים או מעבירים את פרטיך לצדדים שלישיים למטרות שיווק.</strong>
        </p>
      </Section>

      <Section title="5. שיתוף מידע">
        <p>המידע שלך לא יועבר לגורמים חיצוניים, למעט במקרים הבאים:</p>
        <ul>
          <li>
            <strong>PayPal</strong> — לצורך עיבוד תשלומים (כפוף למדיניות הפרטיות של PayPal)
          </li>
          <li>
            <strong>Telegram / WhatsApp</strong> — הפלטפורמות דרכן השירות מסופק
          </li>
          <li>
            <strong>דרישה חוקית</strong> — אם מחויב על-פי דין, צו שיפוטי או גורם רגולטורי
          </li>
        </ul>
      </Section>

      <Section title="6. אחסון ואבטחת מידע">
        <p>
          המידע שלך מאוחסן בשרתים מאובטחים. אנו נוקטים באמצעי אבטחה טכניים וארגוניים סבירים
          כדי להגן על המידע מפני גישה בלתי מורשית, אובדן, שינוי או חשיפה.
        </p>
        <p>
          אנו שומרים את הנתונים כל עוד חשבונך פעיל, ולאחר מכן למשך 12 חודשים לצורך תיעוד
          עסקי, אלא אם תבקש מחיקה מוקדמת יותר.
        </p>
      </Section>

      <Section title="7. זכויותיך">
        <p>בהתאם לחוק הגנת הפרטיות הישראלי, עומדות לך הזכויות הבאות:</p>
        <ul>
          <li><strong>עיון</strong> — לקבל עותק של המידע שלך השמור אצלנו</li>
          <li><strong>תיקון</strong> — לבקש תיקון מידע שגוי</li>
          <li><strong>מחיקה</strong> — לבקש מחיקת חשבונך ונתוניך</li>
          <li><strong>הגבלת עיבוד</strong> — לבקש הגבלת השימוש בנתוניך</li>
        </ul>
        <p>
          לממש את זכויותיך, פנה אלינו בהודעה ישירה דרך הבוט.
        </p>
      </Section>

      <Section title="8. עוגיות (Cookies)">
        <p>
          האפליקציה הוטמעת בתוך ממשק טלגרם (Mini App) ואינה משתמשת בעוגיות מעקב. ייתכן שטלגרם
          עצמה משתמשת בעוגיות בהתאם למדיניות הפרטיות שלה.
        </p>
      </Section>

      <Section title="9. שינויים במדיניות">
        <p>
          אנו עשויים לעדכן מדיניות זו מעת לעת. שינויים מהותיים יפורסמו בהודעה בבוט לפחות
          7 ימים לפני כניסתם לתוקף. המשך השימוש בשירות לאחר השינוי מהווה הסכמה לתנאים
          המעודכנים.
        </p>
      </Section>

      <Section title="10. יצירת קשר">
        <p>
          לשאלות, בקשות מימוש זכויות או דיווח על בעיות פרטיות, ניתן לפנות אלינו ישירות דרך
          הבוט בטלגרם. נשתדל להגיב תוך 7 ימי עבודה.
        </p>
      </Section>

      <button
        className="btn"
        style={{ marginTop: 8 }}
        onClick={() => {
          if (onContact) {
            onContact()
          } else {
            const tg = window.Telegram?.WebApp
            if (tg?.openTelegramLink) {
              tg.openTelegramLink('https://t.me/israelcarinfobot')
            } else {
              window.open('https://t.me/israelcarinfobot', '_blank')
            }
          }
        }}
      >
        ✉️ צור קשר עם התמיכה
      </button>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div
        style={{
          fontSize: 15,
          fontWeight: 700,
          marginBottom: 10,
          color: 'var(--text)',
          borderBottom: '1px solid var(--bg)',
          paddingBottom: 8,
        }}
      >
        {title}
      </div>
      <div
        style={{
          fontSize: 14,
          color: 'var(--text)',
          lineHeight: 1.7,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        {children}
      </div>
    </div>
  )
}

function SubHeading({ children }) {
  return (
    <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--hint)', marginTop: 4 }}>
      {children}
    </div>
  )
}
