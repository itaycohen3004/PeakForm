/**
 * goals.js — עמוד היעדים וההישגים
 * הקובץ הזה אחראי על כל מה שקשור למטרות שלך: הצבת מטרות חדשות, 
 * מעקב אחרי ההתקדמות שלך, והצגת מטרות שכבר השגת!
 */

// כשהדף מסיים להיטען, אנחנו עושים כמה דברים חשובים:
onReady(async () => {
  requireAuth(); // בודקים שאתה מחובר לחשבון
  await renderSidebar(); // טוענים את התפריט בצד
  initMobileSidebar(); // מסדרים את התפריט אם אתה בטלפון
  await loadGoals(); // טוענים את כל היעדים שלך מהשרת
});

// הפונקציה שמביאה את היעדים מהשרת
async function loadGoals() {
  const goals = await apiFetch('/api/goals', {}, false); // בקשה לשרת
  if (!goals || goals._error) return; // אם יש תקלה, מפסיקים

  // מפצלים את המטרות לשתי קבוצות:
  const active    = goals.filter(g => !g.is_completed); // מטרות פעילות שעוד לא השגת
  const completed = goals.filter(g => g.is_completed); // מטרות שכבר סיימת (כל הכבוד!)

  // מציירים את המטרות על המסך בשני אזורים נפרדים
  renderGoals('active-goals-grid', active, false);
  renderGoals('completed-goals-grid', completed, true);
}

// מילון מיוחד שמגדיר איזה סמל, צבע ויחידת מידה יש לכל סוג של יעד
const GOAL_CONFIG = {
  exercise_weight:     { label: 'משקל תרגיל', unit: 'ק"ג', icon: '🏋️', color: 'violet' },
  exercise_reps:       { label: 'חזרות בתרגיל', unit: 'חזרות', icon: '🔁', color: 'teal' },
  exercise_1rm:        { label: 'יעד משקל מקסימלי', unit: 'ק"ג', icon: '💪', color: 'amber' },
  weekly_frequency:    { label: 'אימונים בשבוע', unit: 'אימונים', icon: '📅', color: 'blue' },
  body_weight_target:  { label: 'משקל גוף', unit: 'ק"ג', icon: '⚖️', color: 'emerald' },
  workout_count:       { label: 'סך הכל אימונים', unit: 'אימונים', icon: '📊', color: 'indigo' },
  volume_target:       { label: 'נפח אימון שבועי', unit: 'ק"ג', icon: '📈', color: 'rose' },
  streak_days:         { label: 'רצף ימים', unit: 'ימים', icon: '🔥', color: 'orange' },
  custom:              { label: 'יעד אישי', unit: '', icon: '⭐', color: 'slate' },
};

// הפונקציה שמציירת את כרטיסי היעדים על המסך
function renderGoals(containerId, goals, completed) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // אם אין יעדים בכלל, נראה הודעה ריקה
  if (!goals.length) {
    container.innerHTML = `
      <div style="grid-column:1/-1">
        <div class="empty-state" style="padding:var(--space-lg)">
          <div class="empty-icon">${completed ? '🏆' : '🎯'}</div>
          <h3>${completed ? 'עדיין אין יעדים שהושלמו' : 'אין יעדים פעילים'}</h3>
          ${!completed ? '<p><button class="btn btn-primary btn-sm" onclick="openGoalModal()">הצב את היעד הראשון שלך</button></p>' : ''}
        </div>
      </div>
    `;
    return;
  }

  // עוברים על כל היעדים ויוצרים כרטיסייה לכל אחד
  container.innerHTML = goals.map(g => {
    // מוצאים את ההגדרות של היעד (צבע, סמל)
    const config = GOAL_CONFIG[g.goal_type] || GOAL_CONFIG.custom;
    // מחשבים כמה אחוזים מהיעד השגת (מקסימום 100%)
    const pct    = Math.min(100, Math.round((g.current_value / Math.max(g.target_value, 0.01)) * 100));

    return `
      <div class="card" style="${completed ? 'border-color:rgba(16,185,129,0.3);background:rgba(16,185,129,0.03)' : ''}">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:var(--space-md)">
          <div style="display:flex;align-items:center;gap:var(--space-sm)">
            <div class="stat-icon ${config.color}" style="width:36px;height:36px;font-size:1rem">${config.icon}</div>
            <div>
              <div style="font-weight:700;color:var(--text-primary)">${escHtml(g.title)}</div>
              <div style="font-size:0.72rem;color:var(--text-muted)">${config.label} ${g.deadline ? `· עד ה- ${formatDate(g.deadline)}` : ''}</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:6px">
            ${completed ? '<span class="badge badge-success">🏆 הושלם</span>' : ''}
            ${!completed ? `<button class="btn btn-ghost btn-xs" onclick="updateProgress(${g.id}, ${g.current_value}, '${config.label}')">✏️</button>` : ''}
            <button class="btn btn-danger btn-xs" onclick="deleteGoal(${g.id})">🗑</button>
          </div>
        </div>

        <div style="display:flex;justify-content:space-between;margin-bottom:6px">
          <span style="font-size:0.82rem;color:var(--text-muted)">התקדמות</span>
          <span style="font-size:0.88rem;font-weight:700;color:${pct >= 100 ? 'var(--green-l)' : 'var(--violet-l)'}">
            ${g.current_value} / ${g.target_value} ${g.unit || config.unit}
          </span>
        </div>

        <div class="progress-wrap">
          <div class="progress-bar ${pct >= 100 ? 'success' : config.color}" style="width:${pct}%"></div>
        </div>

        <div style="display:flex;justify-content:space-between;margin-top:6px">
          <span style="font-size:0.78rem;color:var(--text-muted)">${pct}% הושלמו</span>
          ${pct >= 100 && !completed ? '<span style="font-size:0.8rem;color:var(--green)">🎉 היעד הושג!</span>' : ''}
        </div>
      </div>
    `;
  }).join('');
}

// פונקציה לפתיחת חלון יצירת יעד חדש
function openGoalModal() {
  openModal('goal-modal');
}

// פונקציה לסגירת החלון
function closeGoalModal() {
  closeModal('goal-modal');
}

// פונקציה לשמירת היעד החדש במסד הנתונים
async function saveGoal() {
  const type_el = document.getElementById('goal_type');
  const target_el = document.getElementById('target_value');
  const title_el = document.getElementById('goal_title');
  
  // אוספים את כל הפרטים מהטופס
  const payload = {
    goal_type:    type_el.value,
    title:        title_el.value.trim() || type_el.options[type_el.selectedIndex].text,
    target_value: parseFloat(target_el.value),
    deadline:     document.getElementById('deadline').value || null,
    unit:         GOAL_CONFIG[type_el.value]?.unit || '',
  };

  // מוודאים ששמו יעד הגיוני (גדול מאפס)
  if (!payload.target_value || payload.target_value <= 0) {
    showToast('אנא הכנס ערך יעד חוקי.', 'warning');
    return;
  }

  // שולחים לשרת לשמור
  const result = await apiFetch('/api/goals', { method: 'POST', body: payload });
  if (result && !result._error) {
    showToast('🎯 יעד נוצר בהצלחה!', 'success');
    closeGoalModal();
    target_el.value = '';
    title_el.value = '';
    await loadGoals(); // מרעננים את המסך לראות את היעד החדש
  }
}

// פונקציה שמאפשרת לעדכן את ההתקדמות ביעד (למשל, הוספת קילוגרמים למשקל)
async function updateProgress(goalId, currentVal, label) {
  // מקפיצים חלון קטן שמבקש את הערך החדש
  const val = prompt(`עדכן התקדמות עבור "${label}":`, currentVal);
  if (val === null) return; // אם המשתמש ביטל
  
  const num = parseFloat(val);
  if (isNaN(num)) { showToast('ערך לא חוקי.', 'error'); return; }

  // מעדכנים מול השרת
  const result = await apiFetch(`/api/goals/${goalId}/progress`, {
    method: 'PATCH',
    body: { current_value: num },
  });

  if (result && !result._error) {
    // אם ההתקדמות הגיעה ל-100%, היעד הושלם!
    if (result.is_completed) {
      showToast('🏆 היעד הושג! כל הכבוד!', 'success');
      launchConfetti(); // מפעילים זיקוקים!
    } else {
      showToast('ההתקדמות עודכנה!', 'success');
    }
    await loadGoals();
  }
}

// פונקציה למחיקת יעד שאתה לא רוצה יותר
async function deleteGoal(goalId) {
  // שואלים כדי להיות בטוחים
  if (!confirm('למחוק את היעד הזה?')) return;
  
  const result = await apiFetch(`/api/goals/${goalId}`, { method: 'DELETE' });
  if (result && !result._error) {
    showToast('היעד נמחק.', 'success');
    await loadGoals();
  }
}

/*
English Summary:
This file handles the frontend interface for goal management. It fetches the user's active 
and completed goals, dynamically renders goal cards with calculated progress bars, handles 
modals for creating new goals, allows updating progress incrementally, and triggers celebratory 
animations (like confetti) when a goal reaches 100% completion.

סיכום בעברית:
קובץ זה מנהל את מערכת המטרות האישיות של המתאמנים (כמו לרדת במשקל או להרים 100 קילו).
הוא מציג כל מטרה ככרטיסייה עם "מד התקדמות" (Progress Bar). כשמתאמן מצליח 
להגיע ל-100% מהמטרה, הקובץ מפעיל אנימציה חגיגית של זיקוקים וקונפטי!
*/
