/**
 * api.js — קובץ שאחראי על התקשורת עם השרת
 * כאן אנחנו מגדירים פונקציות שעוזרות לאפליקציה "לדבר" עם מסד הנתונים והשרת
 */

// משתנה ששומר את כתובת הבסיס של השרת. כרגע הוא ריק כי אנחנו משתמשים באותה כתובת של האתר
const API_BASE = '';

/**
 * פונקציה apiFetch - זוהי פונקציית הקסם שלנו!
 * היא לוקחת בקשות רגילות לשרת ומוסיפה להן דברים חשובים כמו:
 * 1. הודעת "טוען..." כדי שהמשתמש יידע שקורא משהו.
 * 2. אבטחה - היא מוסיפה 'תעודת זהות' (טוקן) כדי שהשרת יידע מי אנחנו.
 * 3. טיפול בתקלות - אם משהו משתבש, היא קופצת ומודיעה לנו במקום שהאפליקציה תקרוס.
 */
async function apiFetch(url, options = {}, showLoad = true) {
  // בודקים אם ביקשו מאיתנו "להשתיק" הודעות שגיאה
  const silent           = options.silent           ?? false;
  // בודקים אם אנחנו רוצים למנוע העברה אוטומטית למסך ההתחברות אם המשתמש לא מחובר
  const skipAuthRedirect = options.skipAuthRedirect ?? false;

  // אם צריך, מראים אנימציה של "טוען..." למשתמש
  if (showLoad) showLoading();
  
  try {
    // לוקחים את מפתח האבטחה (טוקן) של המשתמש ששמור אצלנו
    const token = getToken();
    
    // מכינים את "המעטפה" של הבקשה - אומרים לשרת שאנחנו שולחים נתונים בצורת JSON
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    
    // אם יש לנו מפתח אבטחה, אנחנו מצרפים אותו למעטפה
    if (token) headers['Authorization'] = `Bearer ${token}`;

    // פה אנחנו אשכרה שולחים את הבקשה לשרת ומחכים לתשובה (בגלל זה יש await)
    const res = await fetch(API_BASE + url, {
      ...options,
      headers, // מצרפים את המעטפה שהכנו
      credentials: 'include', // מאפשרים לשלוח עוגיות (cookies) אם צריך
      // אם יש מידע לשלוח (body), הופכים אותו לטקסט מיוחד (JSON) כדי שהשרת יבין
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    // קוראים את התשובה שחזרה מהשרת בתור טקסט
    const text = await res.text();
    let data;
    
    // מנסים לתרגם את הטקסט בחזרה לאובייקט שאפשר לעבוד איתו ב-JavaScript
    try { 
      data = JSON.parse(text); 
    } catch { 
      // אם זה לא עבד (למשל, השרת החזיר סתם טקסט רגיל), שומרים אותו כמו שהוא
      data = { _raw: text }; 
    }

    // אם השרת אומר "אתה לא מחובר!" (שגיאה מספר 401) ולא אמרנו לפונקציה להתעלם
    if (res.status === 401 && !skipAuthRedirect) {
      clearAuth(); // מוחקים את פרטי ההתחברות הישנים
      window.location.href = '/login.html'; // זורקים את המשתמש חזרה למסך ההתחברות
      return { _error: true, status: 401 }; // מחזירים סימן שיש שגיאה
    }

    // אם השרת אומר "משהו השתבש בבקשה שלך" (הסטטוס לא תקין)
    if (!res.ok) {
      // מחפשים איזו הודעת שגיאה השרת שלח לנו
      const msg = data?.error || data?.message || `HTTP ${res.status}`;
      // אם לא ביקשו מאיתנו לשתוק, נקפיץ הודעה אדומה למשתמש
      if (!silent) showToast(msg, 'error');
      // מחזירים את השגיאה למי שקרא לפונקציה
      return { _error: true, status: res.status, message: msg, ...data };
    }

    // אם הכל עבר בשלום - מחזירים את הנתונים הטובים!
    return data;
    
  } catch (e) {
    // אם הייתה תקלה חמורה (למשל, אין אינטרנט בכלל)
    const friendly = 'שגיאת התחברות לשרת. אנא נסו שוב מאוחר יותר.';
    // אם לא ביקשו לשתוק, מראים הודעת שגיאה יפה למשתמש
    if (!silent) showToast(friendly, 'error');
    // מחזירים הודעת שגיאה מיוחדת כדי שהאפליקציה תדע שמשהו נכשל
    return { _error: true, status: 0, message: friendly };
    
  } finally {
    // "בסוף בסוף" - לא משנה אם הצליח או נכשל, מסתירים את אנימציית ה"טוען..."
    if (showLoad) hideLoading();
  }
}

/**
 * פונקציה apiUpload - משמשת להעלאת קבצים (כמו תמונות) לשרת
 */
async function apiUpload(url, formData) {
  // מראים הודעה חמודה שמתבצעת העלאה
  showLoading('מעלה קובץ...');
  try {
    const token = getToken(); // לוקחים את מפתח האבטחה
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`; // מוסיפים אבטחה
    
    // שולחים את הקובץ לשרת (פעולת POST אומרת שאנחנו שולחים מידע חדש)
    const res = await fetch(API_BASE + url, { 
      method: 'POST', 
      headers, 
      credentials: 'include',
      body: formData // הקובץ עצמו
    });
    
    // ממירים את התשובה לפורמט מובן (JSON)
    const data = await res.json();
    
    // אם השרת החזיר שגיאה
    if (!res.ok) { 
      // מציגים הודעת שגיאה שחזרה מהשרת, או הודעה כללית
      showToast(data?.error || 'העלאת הקובץ נכשלה', 'error'); 
      return { _error: true, ...data }; 
    }
    // אם הכל עבד, מחזירים את התשובה
    return data;
  } catch (e) {
    // אם הייתה תקלה רשת או משהו קרס
    showToast('העלאת הקובץ נכשלה. אנא נסו שוב.', 'error');
    return { _error: true };
  } finally {
    // בכל מקרה בסוף, מסתירים את ההודעה "מעלה קובץ..."
    hideLoading();
  }
}

/**
 * פונקציה apiDownload - משמשת להורדת קבצים מהשרת למחשב/פלאפון
 */
async function apiDownload(url, filename) {
  // מראים הודעה שאנחנו מורידים
  showLoading('מוריד קובץ...');
  try {
    const token = getToken(); // מפתח אבטחה
    
    // מבקשים מהשרת את הקובץ
    const res = await fetch(API_BASE + url, { 
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include'
    });
    
    // אם השרת סירב או הקובץ לא קיים
    if (!res.ok) { 
      showToast('הורדת הקובץ נכשלה', 'error'); 
      return; 
    }
    
    // הקובץ מגיע בתור "גוש נתונים" שנקרא blob
    const blob = await res.blob();
    
    // פה אנחנו עושים טריק של מתכנתים: 
    // אנחנו יוצרים קישור בלתי נראה לדף, שמים בו את הקובץ ולוחצים עליו אוטומטית!
    const a = document.createElement('a'); // יצירת הקישור
    a.href = URL.createObjectURL(blob); // חיבור הקובץ לקישור
    a.download = filename; // קביעת שם הקובץ שיישמר
    a.click(); // לחיצה וירטואלית כדי שההורדה תתחיל בדפדפן
    
  } catch (e) {
    // אם משהו התקלקל בדרך
    showToast('שגיאה בהורדת הקובץ', 'error');
  } finally {
    // מסתירים את חלונית הטעינה בסוף הפעולה
    hideLoading();
  }
}

/*
English Summary:
This file handles API communication between the frontend and the backend. It provides 
wrapper functions around the native fetch API to automatically inject authentication tokens, 
handle loading states, catch common network errors, and manage file uploads/downloads.

סיכום בעברית:
קובץ זה מנהל את התקשורת של האתר (הצד הקדמי) מול השרת (הצד האחורי). הוא מכיל פונקציות
שעוטפות את הבקשות הרגילות ומבצעות עבורנו פעולות אוטומטיות חשובות: הוספת "תעודת כניסה"
(טוקן) לכל בקשה כדי שהשרת יזהה אותנו, הצגת טעינה ויזואלית למשתמש, ותפיסת תקלות תקשורת כדי 
שהאתר לא יקרוס אלא יציג הודעה מסודרת למתאמן.
*/
