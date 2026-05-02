/**
 * templates.js — מנהל תוכניות האימון המוכנות (תבניות)
 * הקובץ הזה אחראי על הדף שבו אתה בונה לעצמך "תבניות" של אימונים שתוכל להשתמש בהן שוב ושוב.
 * אפשר גם לשתף את התבניות האלו עם חברים בקהילה!
 */

let _templates = []; // רשימה ששומרת את כל התבניות שלי
let _allExercises = []; // רשימה של כל התרגילים שקיימים במערכת
let _newTplExercises = []; // התרגילים שבחרתי להוסיף לתבנית שאני בונה עכשיו
let _editTplId = null; // מספר מזהה של התבנית שאני עורך כרגע (אם יש)
let _isViewMode = false; // האם אני רק מסתכל על תבנית או שאני עורך אותה?

// כשהעמוד עולה, אנחנו מכינים הכל:
onReady(async () => {
  requireAuth(); // בודק שאתה מחובר
  await renderSidebar(); // תפריט בצד
  initMobileSidebar(); // תפריט לטלפון
  
  loadTemplates(); // טוען את התבניות שלך מהשרת
  loadExercises(); // טוען את כל התרגילים שקיימים באתר למקרה שתרצה להוסיף אחד
});

// פונקציה שמבקשת מהשרת את רשימת התבניות שלך
async function loadTemplates() {
  const data = await apiFetch('/api/templates');
  if (data && !data._error) {
    _templates = data;
    renderTemplates(); // ברגע שיש נתונים, מציירים אותם על המסך
  }
}

// פונקציה שמבקשת מהשרת את רשימת התרגילים (בשביל החיפוש)
async function loadExercises() {
  const data = await apiFetch('/api/exercises', {}, false);
  if (data && !data._error) {
    _allExercises = data;
  }
}

// מציירת את "כרטיסיות" התבניות על המסך
function renderTemplates() {
  const list = document.getElementById('templates-list');
  // אם אין לך אף תבנית, מראים הודעה יפה
  if (!_templates.length) {
    list.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><p>עדיין לא יצרת אף תבנית.</p></div>`;
    return;
  }
  
  // עוברים על כל התבניות ומייצרים HTML (כרטיסיה יפה לכל תבנית)
  list.innerHTML = _templates.map(t => `
    <div class="template-card">
      <div class="template-header">
        <div>
          <div class="template-title">${escHtml(t.name)}</div> <!-- שם התבנית -->
          <div class="template-meta">${trainingTypeBadge(t.training_type || 'gym')} · ${t.exercise_count || 0} תרגילים</div> <!-- כמה תרגילים יש בה -->
        </div>
        <div style="display:flex;gap:6px">
          <!-- כפתור להתחלת אימון עם התבנית הזו -->
          <a href="/log-workout.html?from_template=${t.id}" class="btn btn-sm btn-primary">התחל</a>
          <button class="btn btn-sm btn-ghost" onclick="viewTemplate(${t.id})" style="color:var(--text-muted)">👁 הצג</button>
          <button class="btn btn-sm btn-ghost" onclick="editTemplate(${t.id})" style="color:var(--text-muted)">✏️ ערוך</button>
          <!-- כפתור לשתף את התבנית עם הקהילה! -->
          <button class="btn btn-sm btn-ghost" onclick="shareTemplate(${t.id})" style="color:var(--accent-teal)">📢 שתף</button>
          <button class="btn btn-sm btn-ghost" onclick="deleteTemplate(${t.id})" style="color:var(--text-muted)">🗑</button>
        </div>
      </div>
    </div>
  `).join('');
}

// פותחת את החלון הגדול שבו יוצרים או עורכים תבנית
function openTemplateModal(mode, tpl = null) {
  _editTplId = tpl ? tpl.id : null; // אם עורכים תבנית, שומרים את המספר שלה
  _isViewMode = mode === 'view'; // האם אני רק מסתכל או גם עורך?
  
  // משנים את הכותרת של החלון בהתאם לפעולה
  const title = mode === 'view' ? '📋 צפייה בתבנית' : (tpl ? '✏️ עריכת תבנית' : '✨ יצירת תבנית חדשה');
  document.getElementById('tpl-modal-title').innerHTML = title;
  
  // ממלאים את השדות הקיימים (אם זו תבנית קיימת)
  document.getElementById('tpl-name').value = tpl ? tpl.name : '';
  document.getElementById('tpl-type').value = tpl ? (tpl.training_type || 'gym') : 'gym';
  
  // אם אנחנו רק במצב צפייה, נועלים את השדות כדי שלא נשנה בטעות
  document.getElementById('tpl-name').disabled = _isViewMode;
  document.getElementById('tpl-type').disabled = _isViewMode;
  document.getElementById('tpl-exercise-search-wrap').style.display = _isViewMode ? 'none' : 'block'; // מסתירים את החיפוש בצפייה
  document.getElementById('save-tpl-btn').style.display = _isViewMode ? 'none' : 'block'; // מסתירים כפתור שמירה
  
  _newTplExercises = [];
  if (tpl && tpl.exercises) {
    // שומרים ברשימה את התרגילים שיש בתבנית כרגע
    _newTplExercises = tpl.exercises.map(e => ({ 
      id: e.exercise_id, 
      name: e.exercise_name, 
      default_sets: e.default_sets || 3, // בדרך כלל יש 3 סטים לתרגיל
      _te_id: e.id 
    }));
  }
  
  renderNewTplExercises(); // מציג את התרגילים בחלון
  openModal('template-modal'); // מפעיל את האנימציה שפותחת את החלון
}

// פונקציות שמביאות מהשרת את התבנית ופותחות את החלון עליה (לצפייה או לעריכה)
async function viewTemplate(id) {
  const data = await apiFetch(`/api/templates/${id}`);
  if (!data._error) openTemplateModal('view', data);
}

async function editTemplate(id) {
  const data = await apiFetch(`/api/templates/${id}`);
  if (!data._error) openTemplateModal('edit', data);
}

// הפונקציה שעובדת כשאתה מקליד שם של תרגיל בחיפוש בתוך התבנית
async function searchTplExercises(query) {
  const dropdown = document.getElementById('tpl-exercise-dropdown'); // הריבוע הקטן עם התוצאות
  const q = query.toLowerCase().trim();
  if (!q) { dropdown.style.display = 'none'; return; } // אם לא הקלדת כלום, נחביא
  
  // 1. מחפשים קודם כל ברשימה שיש לנו כבר על המחשב
  let matches = _allExercises.filter(e => 
    e.name.toLowerCase().includes(q) || 
    e.category.toLowerCase().includes(q)
  );

  // 2. אם לא מצאנו הרבה, אנחנו מבקשים מהשרת לבדוק אם יש לו עוד תרגילים
  if (q.length >= 2 && matches.length < 5) {
    try {
      const serverMatches = await apiFetch(`/api/exercises?q=${encodeURIComponent(q)}`, {}, false);
      if (serverMatches && !serverMatches._error) {
        const existingIds = new Set(matches.map(m => m.id));
        serverMatches.forEach(sm => {
          if (!existingIds.has(sm.id)) matches.push(sm); // מוסיפים אם לא היה לנו
        });
      }
    } catch(e) {}
  }
  
  // אם לא מצאנו כלום, מראים הודעה. ואם מצאנו, מראים את האפשרויות בלחיצה!
  if (!matches.length) {
    dropdown.innerHTML = '<div style="padding:10px;color:var(--text-muted)">לא נמצאו תרגילים</div>';
  } else {
    dropdown.innerHTML = matches.slice(0, 20).map(e => `
      <div class="exercise-option" onclick="addTplExercise(${e.id}, '${escHtml(e.name).replace(/'/g, "\\'")}')">
        <div>
          <div class="exercise-option-name">
            ${escHtml(e.name)}
            ${e.status === 'pending' ? '<span class="badge badge-amber" style="font-size:0.6rem;margin-left:4px">בהמתנה לאישור מנהל</span>' : ''}
          </div>
          <div class="exercise-option-meta">${escHtml(e.category)}</div>
        </div>
        <span style="color:var(--violet)">+ הוסף</span>
      </div>
    `).join('');
  }
  dropdown.style.display = 'block'; // מראים את התוצאות
}

// פונקציה להוספת תרגיל לתוך התבנית שלנו!
function addTplExercise(id, name) {
  // מוודאים שהוא לא כבר קיים שם
  if (_newTplExercises.find(e => e.id === id)) {
    showToast('התרגיל כבר קיים בתבנית', 'warning');
    return;
  }
  _newTplExercises.push({ id, name, default_sets: 3 }); // מוסיפים עם 3 סטים כברירת מחדל
  document.getElementById('tpl-exercise-search').value = ''; // מנקים את החיפוש
  document.getElementById('tpl-exercise-dropdown').style.display = 'none'; // מעלימים תוצאות
  renderNewTplExercises(); // מציירים מחדש את הרשימה
}

// כפתור ה-X שמוחק תרגיל מהתבנית
function removeTplExercise(idx) {
  _newTplExercises.splice(idx, 1);
  renderNewTplExercises();
}

// מעדכן כמה סטים הגדרנו לתרגיל הזה בתבנית
function updateTplSets(idx, val) {
  _newTplExercises[idx].default_sets = parseInt(val) || 3;
}

// מציירת את כל התרגילים שכבר הוספנו לתבנית בתוך החלון יצירה
function renderNewTplExercises() {
  const container = document.getElementById('tpl-exercises-container');
  if (!_newTplExercises.length) {
    container.innerHTML = '<div style="font-size:.8rem;color:var(--text-xmuted);text-align:center;padding:10px;border:1px dashed var(--bg-border);border-radius:var(--radius-sm)">עדיין לא הוספו תרגילים.</div>';
    return;
  }
  
  // על כל תרגיל ברשימה מייצרים שורה יפה עם שדה לשינוי מספר הסטים
  container.innerHTML = _newTplExercises.map((e, idx) => `
    <div class="template-exercise-item">
      <div class="ex-item-info">
        <div class="ex-item-name">${escHtml(e.name)}</div>
      </div>
      <div style="display:flex;align-items:center;gap:6px">
        <label style="font-size:.7rem;color:var(--text-muted)">סטים</label>
        <input type="number" value="${e.default_sets}" min="1" max="10" 
          onchange="updateTplSets(${idx}, this.value)" 
          ${_isViewMode ? 'disabled' : ''}
          style="width:50px;background:var(--bg-input);border:1px solid var(--bg-border);border-radius:4px;padding:4px;color:var(--text-primary);text-align:center">
      </div>
      ${_isViewMode ? '' : `<button class="btn btn-ghost btn-sm" onclick="removeTplExercise(${idx})" style="padding:4px">✕</button>`}
    </div>
  `).join('');
}

// כפתור השמירה הגדול בתחתית החלון! פונה לשרת לשמור הכל.
async function saveTemplate() {
  const name = document.getElementById('tpl-name').value.trim();
  const type = document.getElementById('tpl-type').value;
  
  if (!name) { showToast('חובה להזין שם תבנית', 'error'); return; }
  if (!_newTplExercises.length) { showToast('יש להוסיף לפחות תרגיל אחד', 'error'); return; }
  
  const btn = document.getElementById('save-tpl-btn');
  btn.disabled = true; btn.textContent = 'שומר...';
  
  // אם אנחנו עורכים תבנית קיימת
  if (_editTplId) {
    // 1. מעדכנים את השם והסוג
    await apiFetch(`/api/templates/${_editTplId}`, {
      method: 'PATCH',
      body: { name, training_type: type }
    });
    
    // 2. מסנכרנים מול השרת איזה תרגילים הוספנו ואיזה מחקנו
    const existing = await apiFetch(`/api/templates/${_editTplId}`);
    if (!existing._error) {
      const newExIds = _newTplExercises.map(e => e.id);
      for (const ex of existing.exercises) {
        if (!newExIds.includes(ex.exercise_id)) {
          await apiFetch(`/api/templates/exercises/${ex.id}`, { method: 'DELETE' }); // תרגיל שנמחק
        }
      }
      const oldExIds = existing.exercises.map(e => e.exercise_id);
      for (const [idx, ex] of _newTplExercises.entries()) {
        if (!oldExIds.includes(ex.id)) {
          await apiFetch(`/api/templates/${_editTplId}/exercises`, {
            method: 'POST',
            body: { exercise_id: ex.id, position: idx, default_sets: ex.default_sets } // תרגיל חדש
          });
        }
      }
    }
    showToast('התבנית עודכנה בהצלחה!', 'success');
  } else {
    // אם זו תבנית חדשה לגמרי
    const payload = {
      name,
      training_type: type,
      exercises: _newTplExercises.map(e => ({ name: e.name, default_sets: e.default_sets }))
    };
    const res = await apiFetch('/api/templates', { method: 'POST', body: payload });
    if (!res._error) showToast('התבנית נוצרה בהצלחה!', 'success');
  }
  
  btn.disabled = false; btn.textContent = 'שמור תבנית';
  closeModal('template-modal'); // סוגר את החלון
  loadTemplates(); // מרענן את העמוד
}

// כפתור פח אשפה למחיקת תבנית
async function deleteTemplate(id) {
  if (!confirm('האם אתה בטוח שאתה רוצה למחוק תבנית זו?')) return;
  const res = await apiFetch(`/api/templates/${id}`, { method: 'DELETE' });
  if (!res._error) {
    showToast('תבנית נמחקה', 'success');
    loadTemplates();
  }
}

// שיתוף התבנית שלי בקהילה! לוקח את כל התרגילים ושולח כפוסט לעמוד הקהילה
async function shareTemplate(id) {
  // מושך את המידע המלא של התבנית
  const tpl = await apiFetch(`/api/templates/${id}`);
  if (tpl._error) {
    showToast('לא ניתן לטעון תבנית לשיתוף', 'error');
    return;
  }

  // בונה רשימה טקסטואלית של כל התרגילים בתבנית
  const exList = (tpl.exercises || []).map(e =>
    `  • ${e.exercise_name} — ${e.default_sets || 3} סטים`
  ).join('\n');

  // כותב פוסט מוכן מראש
  const content = `📋 אני רוצה לשתף אתכם בתבנית אימון שלי: ${tpl.name}\n\n${exList}\n\n[הוסיפו את התבנית הזו לאוסף שלכם!]`;

  // מצרף נתונים טכניים (מטא-דאטה) כדי שחברים בקהילה יוכלו פשוט ללחוץ "העתק אלי"
  const metaData = {
    template_id: id,
    template_name: tpl.name,
    training_type: tpl.training_type,
    exercises: (tpl.exercises || []).map(e => ({
      name: e.exercise_name,
      default_sets: e.default_sets || 3,
    }))
  };

  // שולח את הפוסט לשרת הקהילה!
  const res = await apiFetch('/api/community/posts', {
    method: 'POST',
    body: { content, post_type: 'template', meta_data: metaData }
  });

  if (!res._error) {
    showToast('התבנית שותפה בקהילה!', 'success');
    alert('הצלחה! התבנית פורסמה בקיר הקהילה.');
    window.location.href = '/community.html'; // עובר לעמוד הקהילה לראות את הפוסט
  } else {
    showToast('שגיאה בשיתוף התבנית', 'error');
  }
}

/*
English Summary:
This file implements the frontend logic for managing workout templates. It allows users to 
create, edit, view, and delete their own custom training routines. It includes a dynamic search 
feature for adding exercises to a template and a feature that securely serializes the template's 
configuration to share it as a playable post on the Community Feed.

סיכום בעברית:
קובץ זה מטפל בכל מה שקשור לתבניות האימון השמורות של המשתמש. המתאמן יכול ליצור 
שגרת אימונים קבועה (תבנית), לערוך אותה, להוסיף לה תרגילים מתוך רשימת חיפוש חכמה,
ואפילו ללחוץ על כפתור "שתף בקהילה" כדי ששאר החברים באתר יוכלו לראות ולהעתיק את התבנית!
*/
