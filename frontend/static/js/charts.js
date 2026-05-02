/**
 * charts.js — עמוד הגרפים והסטטיסטיקות!
 * הקובץ הזה אחראי לצייר את כל הגרפים היפים של ההתקדמות שלך:
 * כמה משקל הרמת, כמה אימונים עשית, ואיך משקל הגוף שלך משתנה.
 */

// משתנה ששומר את כל הגרפים שציירנו כדי שנוכל למחוק ולצייר אותם מחדש אם צריך
const chartInstances = {};

// כמה ימים אחורה אנחנו רוצים לראות בגרף משקל הגוף (ברירת מחדל: חודש אחורה)
let currentPeriodDays = 30;

// הגדרות עיצוב כלליות לכל הגרפים (צבעים, רקע שקוף, איך נראית התווית שקופצת כשעוברים עם העכבר)
const CHART_OPTS = {
  responsive: true, // שהגרף יתאים את עצמו למסך של טלפון או מחשב
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false }, // מסתירים את המקרא כדי לחסוך מקום
    tooltip: { // מה קורה כשמרחפים עם העכבר מעל נקודה בגרף
      backgroundColor: 'rgba(10,14,26,0.95)', // רקע כהה
      borderColor: 'rgba(139,92,246,0.3)', // מסגרת סגולה
      borderWidth: 1,
      titleColor: '#F0F4FF', // צבע הכותרת
      bodyColor: '#94A3B8', // צבע הטקסט
      padding: 10,
    },
  },
  scales: {
    x: { ticks: { color: '#475569', font: { size: 10 }, maxRotation: 45 }, grid: { color: 'rgba(255,255,255,0.04)' } }, // ציר למטה
    y: { ticks: { color: '#475569', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.06)' } }, // ציר בצד
  },
};

// פונקציה חכמה שמציירת גרף חדש על המסך
function makeChart(id, type, data, options = {}) {
  // אם כבר יש ציור ישן באותו מקום - נמחק אותו קודם
  if (chartInstances[id]) chartInstances[id].destroy();
  
  const ctx = document.getElementById(id)?.getContext('2d'); // מוצאים איפה לצייר
  if (!ctx) return;
  
  // מציירים את הגרף ושומרים אותו ברשימה שלנו
  chartInstances[id] = new Chart(ctx, { type, data, options: { ...CHART_OPTS, ...options } });
}

// פונקציה שלוקחת תאריך ארוך ומקצרת אותו (למשל מ- "2024-05-12" ל-"12 מאי") כדי שייראה יפה בגרף
function shortLabel(dateStr) {
  const d = new Date(dateStr);
  if (isNaN(d)) return dateStr;
  return d.toLocaleDateString('he-IL', { month: 'short', day: 'numeric' }); // מתרגמים לתבנית תאריך קצרה
}

// הפונקציה המרכזית שטוענת את כל הנתונים מהשרת ומציירת את הגרפים
async function loadAllCharts() {
  showLoading('טוען נתונים...'); // מציגים אנימציית טעינה למשתמש
  
  // פונים לשרת ומבקשים 3 דברים במקביל (כדי לחסוך זמן):
  // 1. נתוני נפח אימונים (משקל כולל) של 12 השבועות האחרונים
  // 2. היסטוריית משקל הגוף של התקופה שבחרנו
  // 3. הסטטיסטיקות הכלליות של המשתמש
  const [volumeData, weightData, statsData] = await Promise.all([
    apiFetch(`/api/workouts/weekly-volume?weeks=12`, {}, false),
    apiFetch(`/api/body-weight/history?days=${currentPeriodDays}`, {}, false),
    apiFetch(`/api/dashboard/stats`, {}, false),
  ]);

  hideLoading(); // מסתירים את הטעינה

  // מציירים את הריבועים היפים של "סיכום הנתונים" (למעלה)
  renderSummaryStats(statsData);

  // אם השרת שלח נתוני נפח (ולא שגיאה) - נצייר את הגרף!
  if (volumeData && !volumeData._error) {
    // מכינים את הנתונים לגרף: הופכים את הסדר כדי שהישן יהיה משמאל והחדש מימין
    const labels = volumeData.map(w => w.week).reverse(); // השבועות
    const volume = volumeData.map(w => w.total_volume_kg || 0).reverse(); // כמה משקל הרמנו
    const sets   = volumeData.map(w => w.total_sets || 0).reverse(); // כמה סטים עשינו

    // מציירים את גרף המשקל (גרף קווים עם מילוי סגול חצי שקוף)
    makeChart('chart-volume', 'line', {
      labels,
      datasets: [{
        label: 'נפח אימון (ק"ג)',
        data: volume,
        borderColor: '#8B5CF6',
        backgroundColor: 'rgba(139,92,246,0.1)',
        borderWidth: 3, 
        pointRadius: 4, 
        fill: true, 
        tension: 0.4, // עושה שהקווים יהיו עגולים ויפים
      }],
    });

    // מציירים את גרף הסטים (גרף עמודות כחול)
    makeChart('chart-sets', 'bar', {
      labels,
      datasets: [{
        label: 'סה"כ סטים',
        data: sets,
        backgroundColor: 'rgba(59,130,246,0.6)',
        borderColor: '#3B82F6',
        borderWidth: 1,
        borderRadius: 4, // פינות מעוגלות לעמודות
      }],
    });
  }

  // אם השרת שלח את נתוני משקל הגוף - נצייר את גרף המשקל
  if (weightData && !weightData._error) {
    const labels = weightData.map(d => shortLabel(d.logged_at)); // תאריכים
    const weights = weightData.map(d => d.weight_kg); // משקלים

    // מציירים גרף קווים בצבע תכלת (ללא מילוי)
    makeChart('chart-weight', 'line', {
      labels,
      datasets: [{
        label: 'משקל גוף (ק"ג)',
        data: weights,
        borderColor: '#14B8A6',
        backgroundColor: 'rgba(20,184,166,0.05)',
        borderWidth: 2, 
        pointRadius: 3, 
        fill: false, 
        tension: 0.2,
      }],
    }, {
      scales: {
        ...CHART_OPTS.scales,
        y: { ...CHART_OPTS.scales.y, beginAtZero: false } // אומרים לגרף לא להתחיל מאפס, אלא מהמשקל האמיתי
      }
    });
  }
}

// פונקציה שמייצרת את קוביות המידע הצבעוניות שבראש העמוד (כמו כרטיסיות עם סטטיסטיקות מדליקות)
function renderSummaryStats(stats) {
  const container = document.getElementById('chart-stats-row');
  if (!container || !stats || stats._error) return;

  // מייצרים HTML עם נתונים כמו: כמה ימים ברצף התאמנת, כמה אימונים עשית בסך הכל וכו'
  container.innerHTML = `
    <div class="stat-card violet">
      <div class="stat-icon violet">🔥</div>
      <div class="stat-value">${stats.streak || 0}</div>
      <div class="stat-label">ימים ברצף</div>
    </div>
    <div class="stat-card blue">
      <div class="stat-icon blue">🏋️</div>
      <div class="stat-value">${stats.total_workouts || 0}</div>
      <div class="stat-label">סה"כ אימונים</div>
    </div>
    <div class="stat-card success">
      <div class="stat-icon success">📦</div>
      <div class="stat-value">${parseInt(stats.total_volume || 0).toLocaleString()} <small>ק"ג</small></div>
      <div class="stat-label">סה"כ משקל שהורם</div>
    </div>
    <div class="stat-card teal">
      <div class="stat-icon teal">🎯</div>
      <div class="stat-value">${stats.prs_count || 0}</div>
      <div class="stat-label">שיאים אישיים</div>
    </div>
  `;
}

// כשהמשתמש משנה את התקופה של גרף המשקל (למשל: רוצה לראות 90 ימים אחורה במקום 30)
function setPeriod(days, btn) {
  currentPeriodDays = days; // שומרים את הבחירה שלו
  // מורידים את הסימון מהכפתור הקודם
  document.querySelectorAll('.chart-filter-btn').forEach(b => b.classList.remove('active'));
  // מסמנים את הכפתור שעליו הוא לחץ
  btn.classList.add('active');
  // קוראים מחדש לפונקציה שמביאה את הנתונים כדי שתצייר את הגרפים עם הנתונים החדשים
  loadAllCharts();
}

// כשהעמוד מוכן: מתחברים, מציגים תפריט, ומתחילים לטעון את כל הגרפים
onReady(() => {
  requireAuth();
  renderSidebar();
  initMobileSidebar();
  loadAllCharts();
});

/*
English Summary:
This file is responsible for the Dashboard charts and statistics. It uses Chart.js to render 
dynamic, visually appealing charts (e.g., Weekly Volume, Body Weight tracking). It fetches 
aggregated data from the backend APIs, handles filtering data by time periods, and renders 
the top-level KPI metric cards.

סיכום בעברית:
קובץ זה אחראי על ציור הגרפים והסטטיסטיקות במסך ה"התקדמות שלי". הוא משתמש בספריית עיצוב
(Chart.js) כדי לקחת את כל הנתונים היבשים מהשרת (כמו כמה משקל הרמנו כל שבוע) ולהפוך אותם 
לגרפים ויזואליים יפים ודינמיים. 
*/
