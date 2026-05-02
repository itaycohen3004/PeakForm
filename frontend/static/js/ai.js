/**
 * ai.js — מאמן הכושר החכם (בינה מלאכותית של גוגל)
 * הקובץ הזה מדבר עם "המאמן" האוטומטי. אפשר לבקש ממנו לנתח 
 * את ההתקדמות שלנו, להצביע על נקודות חולשה, ולתת טיפים מותאמים אישית.
 */

let selectedCards = null;

// כשהעמוד עולה ומוכן לשימוש
onReady(async () => {
  requireAuth(); // בודק שאתה משתמש רשום
  renderSidebar(); // שם את התפריט בצד
  initMobileSidebar();

  // בוחר אוטומטית את האפשרות הראשונה ברשימה
  const firstCard = document.querySelector('.analysis-type-card .card');
  if (firstCard) selectType(firstCard);

  await loadHistory(); // טוען היסטוריה של ניתוחים קודמים שעשינו עם המאמן

  // בדיקה מגניבה: אם הגענו מפוסט בקהילה שלחצנו עליו "שאל את המאמן"
  try {
    const prefill = sessionStorage.getItem('coach_prefill'); // בודק אם שמרנו שאלה מראש
    if (prefill) {
      sessionStorage.removeItem('coach_prefill');
      const chatInput = document.getElementById('chat-message') || document.getElementById('user-input');
      if (chatInput) {
        // מדביק את הפוסט לתוך השאלה כדי שהמאמן יראה אותו!
        chatInput.value = `האם אתה יכול לנתח את הפוסט הזה מהקהילה ולתת לי תובנות?\n\n"${prefill}"`;
        chatInput.focus(); // שם את העכבר בפנים שנוכל לשלוח
        chatInput.scrollIntoView({ behavior: 'smooth' }); // גולל אותנו ישר למטה
        showToast('הפוסט נטען בהצלחה - לחץ "שלח" כדי לדבר עם המאמן!', 'info');
      }
    }
  } catch(e) {}
});

// פונקציה לבחירת "כרטיסייה" - היא מדליקה למשתמש צבע סגול מסביב למה שהוא לחץ עליו
function selectType(card) {
  // קודם מעלימים את המסגרת מכולם
  document.querySelectorAll('.analysis-type-card .card').forEach(c => {
    c.style.borderColor = 'transparent';
    c.style.background = '';
  });
  // ואז צובעים רק את זה שלחצנו עליו
  card.style.borderColor = 'var(--violet-primary)';
  card.style.background = 'rgba(139, 92, 246, 0.05)';
}

// פונקציה שעוזרת לנו לדעת איזו אפשרות המשתמש בחר כדי לשלוח לשרת
function getSelectedType() {
  const radio = document.querySelector('input[name="analysis_type"]:checked');
  const highlighted = document.querySelector('.analysis-type-card .card[style*="border-color: var(--violet"]');
  if (highlighted) {
    const label = highlighted.closest('label');
    const input = label?.querySelector('input[type="radio"]');
    return input?.value || 'strength_progression';
  }
  return radio?.value || 'strength_progression'; // מחזירים את התשובה (למשל: התקדמות בכוח)
}

// לחיצה על כפתור הקסם! הפונקציה ששולחת לבינה המלאכותית את המידע שלנו
async function runAnalysis() {
  const analysisType = getSelectedType(); // איזה סוג ניתוח ביקשנו
  const btn = document.getElementById('analyze-btn');
  // משנים את הכפתור כדי שהמשתמש יראה שזה טוען (אנימציה של עיגול מסתובב)
  btn.classList.add('loading');
  btn.disabled = true;
  btn.textContent = '';

  // שולחים בקשה לשרת! השרת ידבר עם גוגל ג'מיני ואז יחזיר תשובה
  const result = await apiFetch('/api/ai/analyze', {
    method: 'POST',
    body: { analysis_type: analysisType },
  }, false);

  // מחזירים את הכפתור למצב רגיל
  btn.classList.remove('loading');
  btn.disabled = false;
  btn.textContent = '🤖 הפעל את המאמן החכם';

  // אם קרתה שגיאה בדרך
  if (!result || result._error) {
    showToast(result?.error || 'הניתוח נכשל.', 'error');
    return;
  }

  showToast('✅ ניתוח המאמן הושלם!', 'success');
  displayResult(result, analysisType); // פונקציה שתצייר את התשובה על המסך
  await loadHistory(); // מוסיפים את זה לרשימת היסטוריית הניתוחים
}

// פונקציה שמקבלת את התשובה החכמה מגוגל ומציגה אותה בצורה יפה באתר (קופסאות יפות, צבעים)
function displayResult(result, type) {
  const section = document.getElementById('result-section');
  if (!section) return;
  section.style.display = 'block';

  const badge = document.getElementById('result-type-badge');
  if (badge) badge.textContent = type.replace(/_/g, ' ').toUpperCase(); // מחליף קו-תחתון ברווח

  const cards = document.getElementById('result-cards');
  if (!cards) return;

  // בונה 3 כרטיסיות: 1. התקדמות (טרנדים). 2. אזהרות/הערות. 3. המלצות מקצועיות מהמאמן.
  cards.innerHTML = `
    <!-- כרטיסיית מגמות התקדמות (סגול) -->
    <div class="card" style="border-color:rgba(139,92,246,0.2)">
      <div style="display:flex;align-items:center;gap:var(--space-sm);margin-bottom:var(--space-md)">
        <div class="stat-icon violet" style="width:36px;height:36px;font-size:1rem">📈</div>
        <div style="font-weight:700">מגמות והתקדמות</div>
      </div>
      ${(result.trends || []).map(t => `
        <div style="display:flex;gap:8px;margin-bottom:var(--space-sm)">
          <span style="color:var(--violet-light);flex-shrink:0">→</span>
          <p style="font-size:0.88rem;margin:0">${t}</p>
        </div>
      `).join('') || '<p style="color:var(--text-muted);font-size:0.85rem">עדיין לא נמצאו מגמות מספיק ברורות.</p>'}
    </div>

    <!-- כרטיסיית אזהרות או דברים לשים אליהם לב (כתום) -->
    <div class="card" style="border-color:rgba(245,158,11,0.2)">
      <div style="display:flex;align-items:center;gap:var(--space-sm);margin-bottom:var(--space-md)">
        <div class="stat-icon warning" style="width:36px;height:36px;font-size:1rem">⚠️</div>
        <div style="font-weight:700">נקודות לשיפור</div>
      </div>
      ${(result.warnings || []).length ? (result.warnings || []).map(w => `
        <div style="display:flex;gap:8px;margin-bottom:var(--space-sm)">
          <span style="color:var(--warning);flex-shrink:0">⚠</span>
          <p style="font-size:0.88rem;margin:0;color:var(--text-secondary)">${w}</p>
        </div>
      `).join('') : '<p style="color:var(--success);font-size:0.85rem">מצוין! לא זיהינו בעיות התאוששות כרגע.</p>'}
    </div>

    <!-- כרטיסיית הטיפים וההמלצות הסופיות (טורקיז) -->
    <div class="card" style="border-color:rgba(20,184,166,0.2)">
      <div style="display:flex;align-items:center;gap:var(--space-sm);margin-bottom:var(--space-md)">
        <div class="stat-icon teal" style="width:36px;height:36px;font-size:1rem">💡</div>
        <div style="font-weight:700">המלצות המאמן</div>
      </div>
      ${(result.recommendations || []).map((r, i) => `
        <div style="display:flex;gap:8px;margin-bottom:var(--space-sm)">
          <span style="color:var(--accent-teal);flex-shrink:0;font-weight:700">${i+1}.</span>
          <p style="font-size:0.88rem;margin:0;color:var(--text-secondary)">${r}</p>
        </div>
      `).join('') || '<p style="color:var(--text-muted);font-size:0.85rem">אין המלצות מיוחדות כרגע.</p>'}
    </div>
  `;

  section.scrollIntoView({ behavior: 'smooth', block: 'start' }); // גולל אוטומטית שנוכל לראות את זה ישר
}

// טוענת מהשרת את כל העצות הקודמות שהמאמן נתן לנו
async function loadHistory() {
  const data = await apiFetch('/api/ai/results', {}, false);
  const container = document.getElementById('history-list');

  // אם אין לנו בכלל עצות ישנות
  if (!data || data._error || !data.length) {
    container.innerHTML = `
      <div class="empty-state" style="padding:var(--space-lg)">
        <div class="empty-icon">🤖</div>
        <h3>אין עדיין תובנות</h3>
        <p>הפעל את המאמן למעלה כדי לקבל לראות את ההמלצות הראשונות שלך.</p>
      </div>
    `;
    return;
  }

  // מציירים כל עצה כ"שורה" שאפשר ללחוץ עליה ולפתוח אותה שוב
  container.innerHTML = data.map(a => `
    <div style="padding:var(--space-md);border-bottom:1px solid var(--border);cursor:pointer"
      onclick="expandHistory(this, ${JSON.stringify(a).replace(/"/g, '&quot;')})">
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div>
          <span class="badge badge-violet">${a.analysis_type.replace(/_/g, ' ').toUpperCase()}</span>
          <span style="margin-left:8px;font-size:0.75rem;color:var(--text-muted)">${formatDateTime(a.generated_at)}</span>
        </div>
        <span style="color:var(--text-muted);font-size:0.8rem">לחץ להרחבה ▼</span>
      </div>
      <div class="history-detail" style="display:none;margin-top:var(--space-md)"></div>
    </div>
  `).join('');
}

// כשלוחצים על עצה מהיסטוריה, הפונקציה הזו "פותחת" אותה (מראה או מסתירה)
function expandHistory(el, analysis) {
  const detail = el.querySelector('.history-detail');
  if (detail.style.display === 'none') {
    detail.style.display = 'block';
    displayResult(analysis, analysis.analysis_type); // מציגים את התשובה כמו מקודם
  } else {
    detail.style.display = 'none'; // אם לחצנו שוב - סגור את זה
  }
}

/*
English Summary:
This file implements the AI Coach frontend interface. It handles user interactions with the AI, 
such as selecting an analysis type, sending analysis requests to the backend, rendering the AI's 
generated recommendations into formatted cards (trends, warnings, tips), and fetching the user's 
historical AI coaching sessions.

סיכום בעברית:
קובץ זה מפעיל את המסך של "המאמן החכם" באתר. הוא מאפשר למתאמן לבחור איזה סוג 
של ייעוץ הוא רוצה (למשל, בניית תוכנית או ניתוח אימונים קודמים). הקובץ שולח את הבקשה 
לשרת, ממתין לתשובה מהבינה המלאכותית (Gemini), ומצייר את התשובה על המסך בצורה מעוצבת
של כרטיסיות (טיפים, אזהרות, הצעות שיפור).
*/
