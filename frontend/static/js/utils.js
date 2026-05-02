/**
 * utils.js — קובץ הכלים של האתר (PeakForm)
 * הקובץ הזה מלא בפונקציות קטנות שכולם משתמשים בהן בכל הדפים באתר.
 * למשל: להציג הודעות קופצות, לשמור מידע, או לצייר תפריט.
 */

// ── Toast (הודעות קופצות בתחתית המסך) ──────────────────────────

(function initToasts() {
  let c = document.getElementById('toast-container');
  if (!c) {
    c = document.createElement('div');
    c.id = 'toast-container';
    c.className = 'toast-container';
    document.body.appendChild(c);
  }
})();

function showToast(message, type = 'info', duration = 4000) {
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span>${message}</span><button class="toast-close" onclick="this.parentElement.remove()">✕</button>`;
  c.appendChild(t);
  setTimeout(() => { if (t.parentElement) { t.classList.add('removing'); setTimeout(() => t.remove(), 300); } }, duration);
}

// ── Loading (מסך טעינה שמסתובב) ──────────────────────────────

let _loadingCount = 0, _loadingEl = null;

function showLoading(msg = 'Loading...') {
  _loadingCount++;
  if (!_loadingEl) {
    _loadingEl = document.createElement('div');
    _loadingEl.className = 'loading-overlay';
    _loadingEl.innerHTML = `<div class="spinner"></div><p id="loading-msg">${msg}</p>`;
    document.body.appendChild(_loadingEl);
  }
}

function hideLoading() {
  _loadingCount = Math.max(0, _loadingCount - 1);
  if (_loadingCount === 0 && _loadingEl) { _loadingEl.remove(); _loadingEl = null; }
}

// ── Date Formatting (עיצוב של תאריכים ושעות) ──────────────────

function formatDate(d) {
  if (!d) return '—';
  try { return new Date(d + (d.includes('T') ? '' : 'T00:00:00')).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }); }
  catch { return d; }
}

function formatDateTime(d) {
  if (!d) return '—';
  try { return new Date(d).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch { return d; }
}

function formatTimeAgo(d) {
  if (!d) return '';
  const secs = Math.floor((Date.now() - new Date(d)) / 1000);
  const steps = [{ l: 'year', s: 31536000 }, { l: 'month', s: 2592000 }, { l: 'week', s: 604800 }, { l: 'day', s: 86400 }, { l: 'hour', s: 3600 }, { l: 'minute', s: 60 }];
  for (const i of steps) {
    const n = Math.floor(secs / i.s);
    if (n >= 1) return `${n} ${i.l}${n > 1 ? 's' : ''} ago`;
  }
  return 'Just now';
}

function todayISO() { return new Date().toISOString().slice(0, 10); }
function isoNow() { return new Date().toISOString().slice(0, 16); }

// ── Duration formatting (הצגת זמן בצורה יפה כמו 1h 30m) ───────

function formatSeconds(s) {
  if (!s) return '—';
  const m = Math.floor(s / 60), sec = s % 60;
  return m ? `${m}m ${sec}s` : `${sec}s`;
}

function formatDuration(mins) {
  if (!mins) return '—';
  const h = Math.floor(mins / 60), m = mins % 60;
  return h ? `${h}h ${m}m` : `${m}m`;
}

// ── Badges (תגיות צבעוניות וקטנות עם מילים כמו "מנהל" או "חזה") ──

function roleBadge(role) {
  const map = { athlete: 'violet', admin: 'amber' };
  return `<span class="badge badge-${map[role] || 'muted'}">${role}</span>`;
}

function trainingTypeBadge(type) {
  const labels = {
    gym: '🏋️ Gym', calisthenics: '🤸 Calisthenics', hybrid: '⚡ Hybrid',
    home: '🏠 Home', functional: '🔥 Functional', other: '💪 Other'
  };
  return `<span class="badge badge-violet">${labels[type] || type}</span>`;
}

function setTypeBadge(t) {
  const map = { reps_weight: 'badge-violet', reps_only: 'badge-teal', time_only: 'badge-amber', time_weight: 'badge-green' };
  const lbl = { reps_weight: 'Reps + Weight', reps_only: 'Reps only', time_only: 'Time hold', time_weight: 'Timed + Weight' };
  return `<span class="badge ${map[t] || 'badge-muted'}">${lbl[t] || t}</span>`;
}

function categoryBadge(cat) {
  return `<span class="badge badge-muted" style="text-transform:capitalize">${(cat || '').replace('_', ' ')}</span>`;
}

function goalTypeBadge(type) {
  const map = {
    exercise_weight: '🏋️ Weight', exercise_reps: '🔁 Reps',
    exercise_1rm: '💪 1RM', body_weight_target: '⚖️ Body Weight',
    weekly_frequency: '📅 Frequency', workout_count: '📊 Workouts',
    volume_target: '📈 Volume', streak_days: '🔥 Streak', custom: '⭐ Custom'
  };
  return `<span class="badge badge-muted">${map[type] || type}</span>`;
}

// ── Progress Bars (מד התקדמות שיורד ועולה) ──────────────────

function progressBar(current, target, cls = '') {
  const pct = Math.min(100, Math.round((current / Math.max(target, 0.01)) * 100));
  return `
    <div class="flex-between mb-sm">
      <span class="font-sm text-muted">${current} / ${target}</span>
      <span style="font-size:.8rem;font-weight:800;color:var(--violet-l)">${pct}%</span>
    </div>
    <div class="progress-wrap"><div class="progress-bar ${cls}" style="width:${pct}%"></div></div>
  `;
}

// ── Auth Helpers (כלי התחברות ובדיקה מי מחובר למערכת) ────────

function getToken() { return localStorage.getItem('pf_token'); }
function getUser() { try { return JSON.parse(localStorage.getItem('pf_user') || 'null'); } catch { return null; } }

function saveAuth(token, user) {
  localStorage.setItem('pf_token', token); // Legacy/Mobile support
  localStorage.setItem('pf_user', JSON.stringify(user));
  localStorage.setItem('pf_logged_in', 'true');
}

function clearAuth() {
  const prefixes = ['pf_', 'rp_', 'cd_'];
  const keys = ['token', 'user', 'logged_in', '2fa_user', '2fa_code', 'onboarding'];
  prefixes.forEach(p => keys.forEach(k => localStorage.removeItem(p + k)));
  sessionStorage.clear(); // Wipe any ephemeral 2FA/draft data
}

function isLoggedIn() { return localStorage.getItem('pf_logged_in') === 'true'; }

function requireAuth() {
  if (!isLoggedIn()) { window.location.href = '/login.html'; return false; }
  return true;
}

function getDashboardUrl() { return '/dashboard.html'; }

// ── Sidebar (התפריט צד שמופיע בכל העמודים באתר) ───────────────

async function renderSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;

  // Always refresh with decrypted values from server (non-blocking fallback)
  let user = getUser();
  if (!user) return;
  try {
    const me = await apiFetch('/api/auth/me', {}, false);
    if (me && !me._error && me.display_name) {
      const updated = { ...user, email: me.email, display_name: me.display_name, role: me.role, training_type: me.training_type };
      saveAuth(getToken(), updated);
      user = updated;
    }
  } catch(_) { /* non-fatal */ }

  const displayName = user.display_name || (user.email && !user.email.startsWith('gAAAA') ? user.email.split('@')[0] : 'Athlete');
  const initials = displayName.substring(0, 2).toUpperCase();

  sidebar.innerHTML = `
    <a href="/dashboard.html" class="sidebar-logo">
      <img src="/static/assets/logo.png" alt="PeakForm" onerror="this.style.display='none'" style="width:32px;height:32px;border-radius:8px;object-fit:cover">
      <span class="sidebar-logo-text">PeakForm</span>
    </a>
    <nav class="sidebar-nav">
      <div class="nav-section-label">Training</div>
      <a href="/dashboard.html" class="nav-item" data-page="dashboard">
        <span class="nav-icon">📊</span> Dashboard
      </a>
      <a href="/log-workout.html" class="nav-item" data-page="log-workout">
        <span class="nav-icon">💪</span> Log Workout
      </a>
      <a href="/workout-history.html" class="nav-item" data-page="workout-history">
        <span class="nav-icon">📅</span> History
      </a>
      <a href="/exercise-library.html" class="nav-item" data-page="exercise-library">
        <span class="nav-icon">🔍</span> Exercises
      </a>
      <div class="nav-section-label">Analytics</div>
      <a href="/body-weight.html" class="nav-item" data-page="body-weight">
        <span class="nav-icon">⚖️</span> Body Weight
      </a>
      <a href="/achievements.html" class="nav-item" data-page="achievements">
        <span class="nav-icon">🏆</span> Goals & Achievements
      </a>
      <div class="nav-section-label">Community</div>
      <a href="/community.html" class="nav-item" data-page="community">
        <span class="nav-icon">🌐</span> Feed
      </a>
      <a href="/community-chat.html" class="nav-item" data-page="community-chat">
        <span class="nav-icon">💬</span> Chat
      </a>
      <a href="/ai-coach.html" class="nav-item" data-page="ai-coach">
        <span class="nav-icon">🤖</span> AI Coach
      </a>
      <div class="nav-section-label">Account</div>
      <a href="/templates.html" class="nav-item" data-page="templates">
        <span class="nav-icon">📋</span> Templates
      </a>
      <a href="/profile.html" class="nav-item" data-page="profile">
        <span class="nav-icon">👤</span> Profile
      </a>
      ${user.role === 'admin' ? `
      <div class="nav-section-label">Admin</div>
      <a href="/admin.html" class="nav-item" data-page="admin" style="color:var(--amber)">
        <span class="nav-icon">🛡️</span> Admin Panel
      </a>
      ` : ''}
    </nav>
    <div class="sidebar-footer">
      <div class="sidebar-user">
        <div class="sidebar-user-avatar">${initials}</div>
        <div class="sidebar-user-info">
          <div class="sidebar-user-name">${escHtml(displayName)}</div>
          <div class="sidebar-user-role">${user.training_type || 'Athlete'}</div>
        </div>
      </div>
      <button class="btn btn-ghost btn-sm btn-full mt-md" onclick="logout()" style="justify-content:flex-start;gap:8px">
        <span>🚪</span> Sign Out
      </button>
    </div>
  `;

  const page = window.location.pathname.split('/').pop().replace('.html', '');
  sidebar.querySelectorAll('.nav-item').forEach(a => {
    if (a.dataset.page === page) a.classList.add('active');
  });

  // Inject bottom navigation for mobile
  if (!document.getElementById('bottom-nav')) {
    const bnav = document.createElement('nav');
    bnav.id = 'bottom-nav';
    bnav.className = 'bottom-nav';
    bnav.innerHTML = `
      <a href="/dashboard.html" class="bottom-nav-item" data-page="dashboard">
        <span class="nav-icon">📊</span><span>Home</span>
      </a>
      <a href="/log-workout.html" class="bottom-nav-item" data-page="log-workout">
        <span class="nav-icon">💪</span><span>Workouts</span>
      </a>
      <a href="/exercise-library.html" class="bottom-nav-item" data-page="exercise-library">
        <span class="nav-icon">🔍</span><span>Library</span>
      </a>
      <a href="/ai-coach.html" class="bottom-nav-item" data-page="ai-coach">
        <span class="nav-icon">🤖</span><span>AI Coach</span>
      </a>
      <div class="bottom-nav-item" id="mobile-hamburger" style="cursor:pointer">
        <span class="nav-icon">☰</span><span>More</span>
      </div>
    `;
    document.body.appendChild(bnav);

    bnav.querySelectorAll('.bottom-nav-item').forEach(a => {
      if (a.dataset.page === page) a.classList.add('active');
    });

    // Mobile menu modal for More Options
    const menuModal = document.createElement('div');
    menuModal.id = 'mobile-menu-modal';
    menuModal.className = 'modal-backdrop';
    menuModal.style.display = 'none';
    menuModal.innerHTML = `
      <div class="modal" style="margin-top:auto; margin-bottom:0; border-bottom-left-radius:0; border-bottom-right-radius:0;">
        <div class="modal-header">
          <h3 class="modal-title">More</h3>
          <button class="modal-close" onclick="closeModal('mobile-menu-modal')">✕</button>
        </div>
        <div class="more-menu-grid mb-md">
          <a href="/community-chat.html" class="more-menu-item"><span class="nav-icon">💬</span> Chat</a>
          <a href="/community.html" class="more-menu-item"><span class="nav-icon">🌐</span> Feed</a>
          <a href="/workout-history.html" class="more-menu-item"><span class="nav-icon">📅</span> History</a>
          <a href="/achievements.html" class="more-menu-item"><span class="nav-icon">🏆</span> Goals</a>
          <a href="/body-weight.html" class="more-menu-item"><span class="nav-icon">⚖️</span> Weight</a>
          <a href="/templates.html" class="more-menu-item"><span class="nav-icon">📋</span> Templates</a>
          <a href="/profile.html" class="more-menu-item"><span class="nav-icon">👤</span> Profile</a>
          ${user.role === 'admin' ? '<a href="/admin.html" class="more-menu-item" style="color:var(--amber)"><span class="nav-icon">🛡️</span> Admin</a>' : ''}
          <a href="#" class="more-menu-item" onclick="logout()" style="color:var(--red)"><span class="nav-icon">🚪</span> Sign Out</a>
        </div>
      </div>
    `;
    document.body.appendChild(menuModal);
    closeModalOnBackdrop('mobile-menu-modal');

    document.getElementById('mobile-hamburger').addEventListener('click', () => {
      openModal('mobile-menu-modal');
    });
  }
}

// ── Logout (התנתקות מהמערכת) ──────────────────────────────────

async function logout() {
  try { await apiFetch('/api/auth/logout', { method: 'POST' }); } catch { }
  clearAuth();
  window.location.href = '/login.html';
}

// ── Mobile Sidebar (תפריט מיוחד שמותאם למסכים של טלפונים) ─────

function initMobileSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const btn = document.getElementById('mobile-menu-btn');
  if (btn) btn.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('active');
  });
  if (overlay) overlay.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
  });
}

// ── XSS Protection (הגנה מפני האקרים שמנסים לכתוב קוד זדוני) ──

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ── Form Helpers (כלים לעבודה עם טפסים והצגת שגיאות) ──────────

function clearFieldErrors(form) {
  form.querySelectorAll('.field-error').forEach(e => e.remove());
  form.querySelectorAll('.form-control.error').forEach(e => e.classList.remove('error'));
}

function showFieldErrors(errors) {
  for (const [field, msg] of Object.entries(errors)) {
    const el = document.getElementById(field) || document.querySelector(`[name="${field}"]`);
    if (el) {
      el.classList.add('error');
      const e = document.createElement('div');
      e.className = 'field-error';
      e.textContent = Array.isArray(msg) ? msg.join('. ') : msg;
      el.parentElement.appendChild(e);
    }
  }
}

// ── Workout helpers (חישובים מיוחדים שקשורים לאימונים, סטים ומשקל)

const CATEGORY_ICONS = {
  chest: '🫀', back: '🦾', shoulders: '💪', arms: '💪',
  legs: '🦵', core: '🔥', full_body: '⚡', skill: '🤸', cardio: '🏃',
};

function categoryIcon(cat) { return CATEGORY_ICONS[cat] || '💪'; }

function formatSetSummary(ex) {
  if (!ex.sets || !ex.sets.length) return '—';
  const working = ex.sets.filter(s => !s.is_warmup);
  if (!working.length) return '—';
  const st = ex.set_type;
  if (st === 'reps_weight') {
    const s = working[0];
    return `${working.length} × ${s.reps || '?'} reps @ ${s.weight_kg || '?'}kg`;
  }
  if (st === 'reps_only') return `${working.length} × ${working[0].reps} reps`;
  if (st === 'time_only') return `${working.length} × ${formatSeconds(working[0].duration_seconds)}`;
  if (st === 'time_weight') return `${working.length} × ${formatSeconds(working[0].duration_seconds)} @ ${working[0].weight_kg}kg`;
  return `${working.length} sets`;
}

function calcVolume(exercises) {
  let vol = 0;
  for (const ex of (exercises || [])) {
    for (const s of (ex.sets || [])) {
      if (s.weight_kg && s.reps) vol += s.weight_kg * s.reps;
    }
  }
  return Math.round(vol);
}

function calc1RM(weight, reps) {
  if (!weight || !reps || reps <= 0) return 0;
  if (reps === 1) return weight;
  return Math.round(weight * (1 + reps / 30) * 10) / 10; // Epley formula
}

// ── Weight color logic (צביעת טקסט לירוק/אדום אם ירדנו/עלינו במשקל)

function weightChangeColor(change, goalDirection) {
  // goalDirection: 'gain' | 'lose' | 'maintain'
  if (!change) return '';
  if (goalDirection === 'gain') {
    return change > 0 ? 'text-green' : 'text-red';
  } else if (goalDirection === 'lose') {
    return change < 0 ? 'text-green' : 'text-red';
  }
  return 'text-muted';
}

// ── Modal helpers (פתיחה וסגירה של חלונות קופצים גדולים) ──────

function openModal(id) {
  const el = document.getElementById(id);
  if (el) { el.style.display = 'flex'; el.classList.add('modal-open'); }
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) { el.style.display = 'none'; el.classList.remove('modal-open'); }
}

function closeModalOnBackdrop(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.addEventListener('click', e => { if (e.target === el) closeModal(modalId); });
}

// ── Confetti (הזיקוקים והבלונים שקופצים שיש לך הישג!) ────────

function launchConfetti(duration = 3000) {
  const colors = ['#8B5CF6', '#14B8A6', '#F59E0B', '#10B981', '#3B82F6'];
  const count = 80;
  for (let i = 0; i < count; i++) {
    const el = document.createElement('div');
    el.style.cssText = `
      position:fixed;
      width:${Math.random() * 10 + 5}px;
      height:${Math.random() * 10 + 5}px;
      background:${colors[Math.floor(Math.random() * colors.length)]};
      left:${Math.random() * 100}vw;
      top:-20px;
      border-radius:${Math.random() > 0.5 ? '50%' : '2px'};
      z-index:9999;
      pointer-events:none;
      animation:confetti-fall ${Math.random() * 2 + 1.5}s ease-in forwards;
      animation-delay:${Math.random() * 0.5}s;
    `;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), duration + 500);
  }
}

// Inject confetti animation if not present
if (!document.getElementById('confetti-style')) {
  const style = document.createElement('style');
  style.id = 'confetti-style';
  style.textContent = `
    @keyframes confetti-fall {
      0%   { transform: translateY(0) rotate(0deg); opacity:1; }
      100% { transform: translateY(100vh) rotate(720deg); opacity:0; }
    }
  `;
  document.head.appendChild(style);
}

// ── Clipboard (העתקת טקסט ללוח של המחשב) ──────────────────────

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast('Copied to clipboard!', 'success');
    return true;
  } catch {
    showToast('Copy failed', 'error');
    return false;
  }
}

// ── Draft / AutoSave helpers (שמירה אוטומטית אם בטעות סגרנו את הדף)

function saveDraft(key, data) {
  try { localStorage.setItem(`pf_draft_${key}`, JSON.stringify({ data, ts: Date.now() })); } catch { }
}

function loadDraft(key) {
  try {
    const stored = localStorage.getItem(`pf_draft_${key}`);
    if (!stored) return null;
    const { data, ts } = JSON.parse(stored);
    // Only restore drafts less than 24 hours old
    if (Date.now() - ts > 86400000) { clearDraft(key); return null; }
    return data;
  } catch { return null; }
}

function clearDraft(key) {
  localStorage.removeItem(`pf_draft_${key}`);
}

function hasDraft(key) {
  return !!localStorage.getItem(`pf_draft_${key}`);
}

// ── DOM Ready (הפעלת פונקציות רק אחרי שהאתר סיים להיטען) ──────
function onReady(fn) {
  // Force HTTPS in production
  if (window.location.protocol === 'http:' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    window.location.href = window.location.href.replace('http:', 'https:');
    return;
  }
  if (document.readyState !== 'loading') fn();
  else document.addEventListener('DOMContentLoaded', fn);
}

/*
English Summary:
This file is the core utility library for the frontend. It provides globally accessible 
helper functions for date/time formatting, parsing data, rendering badges and progress bars, 
managing client-side authentication tokens (localStorage), rendering the dynamic application sidebar, 
displaying UI toast notifications, and securely sanitizing HTML to prevent cross-site scripting (XSS).

סיכום בעברית:
זהו ה"ארגז כלים" של האתר! קובץ זה מכיל המון פונקציות עזר קטנות שמשמשות את כל שאר הקבצים.
יש פה כלים להצגת תאריכים בצורה יפה, חישובים מתמטיים קטנים (כמו חישוב משקל מרבי), 
פונקציות להצגת הודעות קופצות (Toasts), יצירת אנימציית זיקוקים, והגנה על האתר מפני פריצות.
*/
