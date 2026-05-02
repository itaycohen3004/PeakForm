/**
 * auth.js — קובץ שאחראי על ההתחברות וההרשמה לאתר (PeakForm)
 * כאן אנחנו בודקים מי נכנס לאתר, האם הסיסמה שלו נכונה, ומנהלים משתמשים חדשים.
 */

// ============================================================
// התחברות (LOGIN) - כשמשתמש קיים רוצה להיכנס לאתר
// ============================================================

async function handleLogin(e) {
  // עוצרים את הרענון הרגיל של הדף כשלוחצים על "שלח" בטופס
  e.preventDefault();
  const form = e.target; // הטופס שעליו לחצו
  clearFieldErrors(form); // מוחקים הודעות שגיאה ישנות שאולי מופיעות על המסך

  // לוקחים את האימייל והסיסמה שהמשתמש הקליד
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;

  // בודקים שהמשתמש באמת כתב משהו ולא השאיר ריק
  if (!email || !password) {
    showToast('אנא הכנס אימייל וסיסמה.', 'warning'); // מקפיצים הודעה צהובה
    return; // עוצרים את הפעולה
  }

  // מוצאים את כפתור ה"התחבר", שמים עליו אנימציה של טעינה ונועלים אותו כדי שלא ילחצו עליו מלא פעמים
  const btn = form.querySelector('[type="submit"]');
  btn.classList.add('loading');
  btn.disabled = true;

  // שולחים בקשה לשרת שלנו: "היי שרת, הנה האימייל והסיסמה, האם זה משתמש אמיתי?"
  const data = await apiFetch('/api/auth/login', {
    method: 'POST', // POST אומר שאנחנו שולחים נתונים
    body: { email, password }, // שולחים את מה שהוקלד
  }, false);

  // השרת ענה! עכשיו אפשר להחזיר את הכפתור למצב רגיל
  btn.classList.remove('loading');
  btn.disabled = false;

  // אם השרת לא ענה בכלל (אולי אין אינטרנט), פשוט מפסיקים
  if (!data) return;

  // אם השרת החזיר לנו שגיאה (סיסמה לא נכונה, משתמש לא קיים וכו')
  if (data._error) {
    const msg = data.error || 'ההתחברות נכשלה.'; // מחפשים את סיבת השגיאה
    showToast(msg, 'error'); // מציגים הודעה אדומה
    if (data.errors) showFieldErrors(data.errors); // מסמנים באדום את השדה הבעייתי
    return;
  }

  // אם הכל טוב! השרת שלח לנו "מפתח אבטחה" (טוקן). אנחנו שומרים אותו ואת פרטי המשתמש בדפדפן
  saveAuth(data.token, {
    user_id: data.user_id,
    role: data.role, // התפקיד שלו (מתאמן או מנהל)
    email: data.email,
    display_name: data.display_name,
  });

  // הודעת הצלחה שמחה
  showToast('התחברת בהצלחה! ברוך שובך.', 'success');
  
  // אחרי קצת פחות משנייה, מעבירים את המשתמש לדף המתאים לו
  setTimeout(() => {
    // אם זה מתאמן שעוד לא סיים למלא את כל הפרטים האישיים, נשלח אותו למסך ההשלמה
    if (data.role === 'athlete' && !data.onboarding_complete) {
        window.location.href = '/onboarding.html';
    } else {
        // אחרת, שולחים אותו ישר למסך הראשי שלו
        window.location.href = getDashboardUrl(data.role);
    }
  }, 800);
}

// ============================================================
// הרשמה (REGISTER) - כשמשתמש חדש רוצה ליצור חשבון
// ============================================================

async function handleRegister(e) {
  e.preventDefault(); // מונע מהדף להתרענן
  const form = e.target;
  clearFieldErrors(form); // מוחק שגיאות קודמות

  // אוספים את כל מה שהמשתמש החדש הקליד בטופס
  const payload = {
    email:        document.getElementById('email').value.trim(),
    password:     document.getElementById('password').value,
    display_name: document.getElementById('display_name')?.value.trim() || '', // שם התצוגה שלו
    training_type: document.getElementById('training_type')?.value || 'gym', // סוג האימון (למשל: חדר כושר)
  };

  // בודקים אם שדה "הקלד סיסמה שנית" תואם לסיסמה המקורית
  const confirm = document.getElementById('confirm_password')?.value;
  if (confirm && confirm !== payload.password) {
    showFieldErrors({ confirm_password: 'הסיסמאות לא תואמות.' }); // מציגים שגיאה אם הן שונות
    return;
  }

  // שמים את כפתור ההרשמה בטעינה ונועלים אותו
  const btn = form.querySelector('[type="submit"]');
  btn.classList.add('loading');
  btn.disabled = true;

  // שולחים את הבקשה לשרת כדי שייצור את המשתמש
  const data = await apiFetch('/api/auth/register', {
    method: 'POST',
    body: payload,
  }, false);

  // משחררים את הכפתור מנעילה
  btn.classList.remove('loading');
  btn.disabled = false;

  if (!data) return;

  // אם השרת אומר שההרשמה נכשלה (למשל האימייל כבר תפוס)
  if (data._error) {
    if (data.errors) showFieldErrors(data.errors);
    else showToast(data.error || 'ההרשמה נכשלה.', 'error');
    return;
  }

  // ההרשמה הצליחה! אנחנו רושמים אותו ומתחברים אוטומטית
  showToast('החשבון נוצר בהצלחה! מתחבר...', 'success');
  
  // שומרים את "מפתח האבטחה" שלו בדפדפן
  saveAuth(data.token, {
    user_id: data.user_id,
    role: data.role,
    email: data.email,
    display_name: data.display_name,
  });

  // אחרי קצת יותר משנייה, שולחים אותו למסך השלמת הפרטים הראשוניים
  setTimeout(() => {
    window.location.href = '/onboarding.html';
  }, 1200);
}

// ============================================================
// פונקציות עזר לתצוגה (UI HELPERS)
// ============================================================

// פונקציה שעושה שהסיסמה תהיה גלויה (טקסט רגיל) או נסתרת (כוכביות)
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId); // מוצאים את תיבת הסיסמה
  if (!input) return;
  
  if (input.type === 'password') {
    // אם הסיסמה מוסתרת - נציג אותה ונשנה את האימוג'י
    input.type = 'text';
    btn.textContent = '🙈'; // קוף מסתיר עיניים
  } else {
    // אם הסיסמה גלויה - נסתיר אותה ונשנה את האימוג'י
    input.type = 'password';
    btn.textContent = '👁️'; // עין רואה
  }
}

// פונקציה שמחשבת כמה הסיסמה שלך חזקה ומזיזה את הבר הצבעוני
function updateStrength(password) {
  const bar = document.getElementById('strength-bar'); // הקו הצבעוני
  const label = document.getElementById('strength-label'); // המילה ליד (חלש/חזק)
  if (!bar) return;

  // צוברים נקודות לפי החוזק של הסיסמה
  let score = 0;
  if (password.length >= 8) score++; // נקודה אם יש מעל 8 אותיות
  if (/[A-Z]/.test(password)) score++; // נקודה אם יש אות אנגלית גדולה
  if (/[0-9]/.test(password)) score++; // נקודה אם יש מספר
  if (/[^A-Za-z0-9]/.test(password)) score++; // נקודה אם יש סמל מיוחד (כמו % או !)

  // הרמות השונות של הסיסמה והצבע שלהן
  const levels = [
    { label: '', color: '' }, // 0 נקודות - ריק
    { label: 'חלש', color: 'var(--danger)' }, // 1 נקודה - אדום
    { label: 'סביר', color: 'var(--warning)' }, // 2 נקודות - כתום/צהוב
    { label: 'טוב', color: 'var(--info)' }, // 3 נקודות - תכלת
    { label: 'חזק', color: 'var(--success)' }, // 4 נקודות - ירוק!
  ];

  const level = levels[score];
  // משנים את האורך והצבע של הקו לפי הניקוד
  bar.style.width = `${(score / 4) * 100}%`;
  bar.style.background = level.color;
  
  if (label) {
    label.textContent = level.label; // כותבים את המילה למשתמש (חלש, חזק...)
    label.style.color = level.color;
  }
}

/*
English Summary:
This file manages the authentication logic for the frontend. It handles user login and registration 
by capturing form data, submitting it via API calls, and persisting the received authentication tokens 
in the browser. It also contains UI helpers for toggling password visibility and visually calculating 
password strength.

סיכום בעברית:
קובץ זה מנהל את תהליך ההתחברות וההרשמה של המשתמשים. הוא שואב את הנתונים מטופס 
ההתחברות, שולח אותם לשרת, ושומר את מפתח האבטחה (הטוקן) בדפדפן כדי שהמשתמש יישאר 
מחובר. הקובץ גם אחראי על עיצובים קטנים כמו הצגת מד חוזק לסיסמה והצגת/הסתרת הסיסמה.
*/
