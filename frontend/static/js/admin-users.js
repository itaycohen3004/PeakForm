/**
 * admin-users.js — קובץ ניהול משתמשים (למנהלים בלבד)
 * זהו המסך הסודי של מנהלי האתר. כאן אפשר לראות מי רשום לאתר,
 * לנעול משתמשים בעייתיים, למחוק חשבונות, ולפתוח חשבונות חדשים של מנהלים.
 */

// רשימה שתשמור את כל המשתמשים שיש באתר
let allUsers = [];

// כשעמוד ניהול המשתמשים מסיים להיטען, אנחנו מריצים את הפעולות האלו:
onReady(async () => {
  requireAuth('admin'); // מוודאים שמי שנכנס זה באמת מנהל (Admin) ולא מתאמן רגיל!
  renderSidebar(); // טוענים את התפריט הצדדי
  initMobileSidebar(); // מסדרים את התפריט לטלפון הנייד
  await loadUsers(); // מושכים מהשרת את רשימת כל המשתמשים
});

// פונקציה שמבקשת מהשרת את רשימת כל האנשים הרשומים לאתר
async function loadUsers() {
  // מבקשים מהשרת עד 200 משתמשים
  const data = await apiFetch('/api/admin/users?limit=200', {}, false);
  if (!data || data._error) return; // אם יש שגיאה או שאין נתונים - עוצרים
  
  // שומרים את הנתונים מהשרת בתוך הרשימה שלנו
  allUsers = data.users || data || [];
  renderUsers(allUsers); // מציירים את המשתמשים על המסך
}

// פונקציה לסינון החיפוש - כשהמנהל מקליד שם או מסנן לפי תפקיד/מצב
function filterUsers() {
  // לוקחים את מה שהמנהל הקליד בתיבת החיפוש והופכים לאותיות קטנות (באנגלית)
  const search = document.getElementById('search-input').value.toLowerCase();
  // לוקחים את סוג התפקיד שסיננו (הכל / מתאמן / מנהל)
  const role   = document.getElementById('role-filter').value;
  // לוקחים את מצב החשבון (הכל / נעול / פעיל)
  const status = document.getElementById('status-filter').value;

  // בהתחלה הרשימה המסוננת שווה לכל המשתמשים
  let filtered = Array.isArray(allUsers) ? allUsers : [];
  
  // אם הקלידו משהו בחיפוש, נשאיר רק את מי שהאימייל שלו מכיל את מה שהוקלד
  if (search) filtered = filtered.filter(u => u.email.toLowerCase().includes(search));
  
  // אם בחרו תפקיד מסוים, נשאיר רק את מי שיש לו את התפקיד הזה
  if (role)   filtered = filtered.filter(u => u.role === role);
  
  // אם בחרו לראות רק חשבונות נעולים
  if (status === 'locked') filtered = filtered.filter(u => u.is_locked);
  // אם בחרו לראות רק חשבונות פעילים
  if (status === 'active') filtered = filtered.filter(u => !u.is_locked);
  
  // אחרי שסיננו את כולם, נצייר את הרשימה החדשה על המסך
  renderUsers(filtered);
}

// הפונקציה שלוקחת את רשימת המשתמשים ומציירת אותם בתוך טבלה
function renderUsers(users) {
  const container = document.getElementById('users-table'); // המקום ב-HTML שבו נצייר
  if (!container) return;

  // אם אין משתמשים בכלל (או שאין תוצאות לחיפוש), נציג הודעה עצובה
  if (!users.length) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">👥</div><h3>לא נמצאו משתמשים</h3></div>`;
    return;
  }

  // יוצרים טבלת HTML יפה
  container.innerHTML = `
    <div class="table-wrapper">
      <table class="table">
        <thead>
          <tr><th>אימייל</th><th>תפקיד</th><th>מצב חשבון</th><th>תאריך הצטרפות</th><th>פעולות</th></tr>
        </thead>
        <tbody>
          ${users.map(u => `
            <tr>
              <td>
                <div style="display:flex;align-items:center;gap:8px">
                  <!-- מציירים עיגול קטן עם 2 האותיות הראשונות של האימייל -->
                  <div class="sidebar-user-avatar" style="width:32px;height:32px;font-size:0.75rem">${u.email.substring(0,2).toUpperCase()}</div>
                  <div style="font-weight:600">${u.email}</div>
                </div>
              </td>
              <td>${roleBadge(u.role)}</td> <!-- שמים תג עם צבע לתפקיד -->
              <!-- אם החשבון נעול זה יהיה אדום, אם פעיל זה יהיה ירוק -->
              <td><span class="badge ${u.is_locked ? 'badge-danger' : 'badge-green'}">${u.is_locked ? 'נעול' : 'פעיל'}</span></td>
              <td>${formatDate(u.created_at)}</td> <!-- תאריך ההרשמה -->
              <td>
                <div style="display:flex;gap:4px;flex-wrap:wrap">
                  <!-- כפתור לנעילה או לשחרור המשתמש -->
                  <button class="btn btn-outline btn-xs" onclick="toggleLock(${u.id}, ${u.is_locked})">
                    ${u.is_locked ? '🔓 שחרר מנעילה' : '🔒 נעל חשבון'}
                  </button>
                  <!-- כפתור מסוכן למחיקת המשתמש! -->
                  <button class="btn btn-danger btn-xs" onclick="deleteUser(${u.id}, '${u.email}')">🗑 מחיקה</button>
                </div>
              </td>
            </tr>
          `).join('')} <!-- מחברים את כל השורות ביחד לאחת גדולה -->
        </tbody>
      </table>
    </div>
    <!-- סופרים כמה משתמשים מוצגים -->
    <div style="padding:var(--space-md);font-size:0.8rem;color:var(--text-muted)">
      מציג ${users.length} משתמשים
    </div>
  `;
}

// פונקציה שנועלת או משחררת משתמש כשהמנהל לוחץ על הכפתור
async function toggleLock(userId, currentStatus) {
  // אם הוא כרגע נעול - הפעולה תהיה 'שחרר'. אחרת הפעולה תהיה 'נעל'.
  const action = currentStatus ? 'unlock' : 'lock';
  
  // מודיעים לשרת מה החלטנו לעשות
  const result = await apiFetch(`/api/admin/users/${userId}/${action}`, { method: 'POST' });
  
  if (result && !result._error) {
    showToast(`פעולת ${action} בוצעה בהצלחה.`, 'success');
    await loadUsers(); // מרעננים את הרשימה כדי לראות את השינוי
  }
}

// פונקציה שמוחקת משתמש לתמיד!
async function deleteUser(userId, email) {
  // לפני שמוחקים - שואלים אם המנהל בטוח שזה מה שהוא רוצה (קופצת אזהרה במסך)
  if (!confirm(`האם למחוק לצמיתות את החשבון של ${email}? נתוני אימונים היסטוריים יישמרו אך ייהפכו לאנונימיים.`)) return;
  
  // אם אישרנו, שולחים בקשת מחיקה לשרת
  const result = await apiFetch(`/api/admin/users/${userId}`, { method: 'DELETE' });
  
  if (result && !result._error) {
    showToast('החשבון נמחק בהצלחה.', 'success');
    await loadUsers(); // מרעננים את הרשימה
  }
}

// כשרוצים לפתוח מסך יצירת משתמש חדש
function openCreateModal() {
  document.getElementById('new-email').value = ''; // מנקים את השדות למקרה שנשאר שם משהו מהפעם הקודמת
  openModal('create-modal'); // פותחים את החלון הקופץ
}

// כשלוחצים על "שמור" ביצירת משתמש חדש
async function createUser() {
  const email    = document.getElementById('new-email').value.trim();
  const password = document.getElementById('new-password').value;
  const role     = document.getElementById('new-role').value; // מנהל או מתאמן?

  // מוודאים שמילאו גם אימייל וגם סיסמה
  if (!email || !password) {
    showToast('חובה להזין אימייל וסיסמה.', 'warning');
    return;
  }

  // שולחים לשרת בקשה ליצור את המשתמש
  const result = await apiFetch('/api/auth/register_admin', {
    method: 'POST',
    body: { email, password, role },
  });

  if (result && !result._error) {
    showToast(`✅ משתמש ${email} נוצר בהצלחה!`, 'success');
    closeModal('create-modal'); // סוגרים את החלון הקופץ
    await loadUsers(); // מרעננים את הרשימה כדי לראות אותו
  }
}

/*
English Summary:
This file implements the user management interface for administrators. It allows admins to view a 
list of all registered users, filter them by search term, role, and lock status, manually lock/unlock 
specific user accounts, completely delete user accounts, and manually create new user accounts directly 
from the admin panel.

סיכום בעברית:
קובץ זה הוא מסך "ניהול המשתמשים" של המנהל. הוא מציג רשימה מפורטת של כל המתאמנים באתר,
ומאפשר למנהל לעשות פעולות חשובות כמו: חסימת משתמש (נעילה), מחיקת חשבון, חיפוש 
משתמשים ספציפיים, או אפילו יצירת משתמשים חדשים ידנית מתוך הפאנל.
*/
