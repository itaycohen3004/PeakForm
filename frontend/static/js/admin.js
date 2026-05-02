/**
 * admin.js — עמוד ניהול האתר (למנהלים בלבד!)
 * העמוד הזה הוא "מאחורי הקלעים". כאן המנהלים יכולים לראות כמה 
 * משתמשים יש, לאשר תרגילים חדשים שאנשים הציעו, ולפתוח חדרי צ'אט.
 */

// כשהעמוד מוכן, נבדוק שאנחנו באמת מנהלים ולא סתם משתמשים
onReady(async () => {
  requireAuth(); // מוודאים שיש לנו משתמש מחובר
  const user = getUser();
  
  // אם לא מחובר משתמש, או שהתפקיד שלו הוא לא 'מנהל' (admin), נזרוק אותו חזרה הביתה!
  if (!user || user.role !== 'admin') {
    window.location.href = '/dashboard.html';
    return;
  }
  
  await renderSidebar(); // טוענים תפריט צד
  initMobileSidebar(); // טוענים תפריט לטלפון
  loadPendingExercises(); // מבקשים מהשרת את רשימת התרגילים שמחכים לאישור מנהל
  loadAdminStats(); // טוענים נתונים סטטיסטיים כלליים (כמה אנשים רשומים לאתר)
});

// פונקציה שמביאה את כל התרגילים שמתאמנים הציעו לאתר, אבל הם "בהמתנה"
async function loadPendingExercises() {
  const data = await apiFetch('/api/exercises/pending');
  const countEl = document.getElementById('pending-count'); // העיגול שמראה כמה תרגילים ממתינים
  const listEl = document.getElementById('pending-list'); // הרשימה עצמה
  
  if (data && !data._error) {
    countEl.textContent = data.length; // רושמים כמה תרגילים יש
    
    // אם אין תרגילים בהמתנה, מראים הודעה קצרה
    if (!data.length) {
      listEl.innerHTML = '<div class="text-muted" style="padding:10px 0">אין תרגילים בהמתנה.</div>';
      return;
    }
    
    // בונים שורה עבור כל תרגיל שצריך לאשר או לדחות
    listEl.innerHTML = data.map(ex => `
      <div class="pending-row" id="pending-${ex.id}">
        <div>
          <div class="pending-name">${escHtml(ex.name)}</div> <!-- שם התרגיל -->
          <div class="pending-meta">
            ${categoryBadge(ex.category)} <!-- איזה סוג זה? חזה? ידיים? -->
            <span>· ${setTypeBadge(ex.set_type)}</span>
            ${ex.equipment ? `<span>· 🛠 ${escHtml(ex.equipment)}</span>` : ''} <!-- איזה ציוד צריך? -->
            <span>· 👤 הוצע על ידי: ${escHtml(ex.submitted_by_email || 'לא ידוע')}</span> <!-- מי הציע? -->
            ${ex.muscles_tags ? `<span>· 🦴 שרירים: ${escHtml(ex.muscles_tags)}</span>` : ''}
          </div>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <!-- כפתור אישור! -->
          <button class="btn btn-sm btn-approve" onclick="approveExercise(${ex.id}, this)">&#10003; אשר</button>
          <!-- כפתור דחייה -->
          <button class="btn btn-sm btn-reject" onclick="confirmReject(${ex.id}, this)">✕ דחה</button>
        </div>
        <!-- אזור שמזהיר אותנו לפני דחייה סופית (שלא נמחק בטעות) -->
        <div id="confirm-reject-${ex.id}" style="display:none;width:100%;margin-top:8px;padding:8px;background:rgba(239,68,68,.1);border-radius:8px;border:1px solid rgba(239,68,68,.3)">
          <span style="font-size:.85rem;color:var(--red)">לדחות תרגיל זה? פעולה זו סופית.</span>
          <div style="display:flex;gap:6px;margin-top:6px">
            <button class="btn btn-sm btn-reject" onclick="rejectExercise(${ex.id}, this)">❌ כן, דחה</button>
            <button class="btn btn-sm btn-ghost" onclick="cancelReject(${ex.id})">ביטול</button>
          </div>
        </div>
      </div>
    `).join('');
  }
}

// כשהמנהל לוחץ "אשר" על תרגיל - זה שומר אותו באתר לכולם!
async function approveExercise(id, btn) {
  if (btn) { btn.disabled = true; btn.textContent = 'מאשר...'; }
  const res = await apiFetch(`/api/exercises/${id}/approve`, { method: 'POST' });
  if (!res._error) {
    showToast('תרגיל אושר ✅', 'success');
    document.getElementById(`pending-${id}`)?.remove(); // מעלימים אותו מהרשימה
    const countEl = document.getElementById('pending-count'); // מורידים אחד מהמספר
    if (countEl) countEl.textContent = Math.max(0, (parseInt(countEl.textContent) || 1) - 1);
  } else {
    if (btn) { btn.disabled = false; btn.textContent = '✓ אשר'; }
  }
}

// פותח אזהרה "האם אתה בטוח שאתה רוצה לדחות?"
function confirmReject(id, btn) {
  const confirmRow = document.getElementById(`confirm-reject-${id}`);
  if (confirmRow) confirmRow.style.display = 'block';
}

// סוגר את האזהרה אם התחרטנו
function cancelReject(id) {
  const confirmRow = document.getElementById(`confirm-reject-${id}`);
  if (confirmRow) confirmRow.style.display = 'none';
}

// כשהמנהל לוחץ שוב ומוחק את התרגיל לתמיד!
async function rejectExercise(id, btn) {
  if (btn) { btn.disabled = true; btn.textContent = 'דוחה...'; }
  const res = await apiFetch(`/api/exercises/${id}/reject`, { method: 'POST' });
  if (!res._error) {
    showToast('תרגיל נדחה', 'info');
    document.getElementById(`pending-${id}`)?.remove();
    const countEl = document.getElementById('pending-count');
    if (countEl) countEl.textContent = Math.max(0, (parseInt(countEl.textContent) || 1) - 1);
  } else {
    if (btn) { btn.disabled = false; btn.textContent = '❌ כן, דחה'; }
  }
}

// יצירת חדר צ'אט חדש לקהילה על ידי מנהל
async function createChatRoom() {
  const name = (document.getElementById('new-room-name')?.value || '').trim(); // לוקחים את שם החדר
  const desc = (document.getElementById('new-room-desc')?.value || '').trim(); // לוקחים את התיאור של החדר
  if (!name) { showToast('חובה להכניס שם לחדר', 'warning'); return; }

  const btn = document.querySelector('[onclick="createChatRoom()"]');
  if (btn) { btn.disabled = true; btn.textContent = 'יוצר...'; }

  // שולחים בקשה לשרת ליצור את החדר
  const res = await apiFetch('/api/chat/rooms', { method: 'POST', body: { name, description: desc } });
  if (btn) { btn.disabled = false; btn.textContent = '➕ צור חדר'; }

  if (!res._error) {
    showToast(`החדר "${name}" נוצר בהצלחה! ✅`, 'success');
    // מנקים את השדות
    document.getElementById('new-room-name').value = '';
    document.getElementById('new-room-desc').value = '';
  }
}

// טוען נתונים למספרים הגדולים בראש הדף (סה"כ משתמשים וסה"כ אימונים בכל האתר!)
async function loadAdminStats() {
  const el = document.getElementById('admin-stats');
  if (!el) return;
  const data = await apiFetch('/api/admin/stats', {}, false);
  if (!data || data._error) {
    el.innerHTML = '<span style="color:var(--text-muted);font-size:.85rem">לא הצלחנו לטעון נתונים.</span>';
    return;
  }
  
  // מציירים שני כרטיסים יפים עם הנתונים
  el.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:16px">
      <div class="card" style="text-align:center;padding:16px">
        <div style="font-size:1.8rem;font-weight:900;color:var(--violet-l)">${data.total_users ?? 0}</div>
        <div style="font-size:.75rem;color:var(--text-muted);margin-top:4px">סה"כ משתמשים רשומים</div>
      </div>
      <div class="card" style="text-align:center;padding:16px">
        <div style="font-size:1.8rem;font-weight:900;color:var(--green-l)">${data.total_workouts ?? 0}</div>
        <div style="font-size:.75rem;color:var(--text-muted);margin-top:4px">סה"כ אימונים שבוצעו באתר</div>
      </div>
    </div>
  `;
}

/*
English Summary:
This file contains the frontend logic for the main admin dashboard. It ensures only administrators 
can access the page, fetches pending custom exercises for approval/rejection, provides functionality 
for creating public chat rooms, and displays high-level system statistics (e.g., total users and workouts).

סיכום בעברית:
קובץ זה מיועד למנהלי המערכת בלבד. הוא מציג את לוח הבקרה (דשבורד) הראשי של המנהל,
בו ניתן לראות נתונים סטטיסטיים (כמה משתמשים נרשמו, כמה אימונים בוצעו), לאשר או לדחות 
תרגילים חדשים שמשתמשים הוסיפו למערכת, ולפתוח חדרי צ'אט ציבוריים חדשים לקהילה.
*/
