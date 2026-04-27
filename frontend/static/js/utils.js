/**
 * PeakForm — Shared Utilities
 * Core helpers used across all pages.
 */

// ── Toast ──────────────────────────────────────────────────

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

// ── Loading ─────────────────────────────────────────────────

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

// ── Date Formatting ─────────────────────────────────────────

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

// ── Duration formatting ─────────────────────────────────────

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

// ── Badges ──────────────────────────────────────────────────

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

// ── Progress Bars ───────────────────────────────────────────

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

// ── Auth Helpers ─────────────────────────────────────────────

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

// ── Sidebar ──────────────────────────────────────────────────

async function renderSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  const user = getUser();
  if (!user) return;
  const initials = (user.display_name || user.email || 'P').substring(0, 2).toUpperCase();

  // Get unread notification count
  let unreadCount = 0;
  try {
    const r = await apiFetch('/api/notifications/unread-count');
    unreadCount = r?.count || 0;
  } catch { }

  sidebar.innerHTML = `
    <a href="/dashboard.html" class="sidebar-logo">
      <img src="/static/assets/logo.png" alt="PeakForm" onerror="this.style.display='none'" style="width:32px;height:32px;border-radius:8px;object-fit:cover">
      <span class="sidebar-logo-text">PeakForm</span>
    </a>
    <nav class="sidebar-nav">
      <div class="nav-section-label">Training</div>
      <a href="/dashboard.html" class="nav-item" data-page="dashboard">
        <span class="nav-icon">📊</span> Dashboard
        ${unreadCount > 0 ? `<span class="nav-badge">${unreadCount}</span>` : ''}
      </a>
      <a href="/log-workout.html" class="nav-item" data-page="log-workout">
        <span class="nav-icon">💪</span> Log Workout
      </a>
      <a href="/workout-history.html" class="nav-item" data-page="workout-history">
        <span class="nav-icon">📅</span> History
      </a>
      <a href="/templates.html" class="nav-item" data-page="templates">
        <span class="nav-icon">📋</span> Templates
      </a>
      <a href="/exercise-library.html" class="nav-item" data-page="exercise-library">
        <span class="nav-icon">🔍</span> Exercises
      </a>
      <div class="nav-section-label">Analytics</div>
      <a href="/progress.html" class="nav-item" data-page="progress">
        <span class="nav-icon">📈</span> Progress
      </a>
      <a href="/body-weight.html" class="nav-item" data-page="body-weight">
        <span class="nav-icon">⚖️</span> Body Weight
      </a>
      <a href="/pr-tracker.html" class="nav-item" data-page="pr-tracker">
        <span class="nav-icon">🏅</span> PR Tracker
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
      <a href="/profile.html" class="nav-item" data-page="profile">
        <span class="nav-icon">👤</span> Profile
      </a>
    </nav>
    <div class="sidebar-footer">
      <div class="sidebar-user">
        <div class="sidebar-user-avatar">${initials}</div>
        <div class="sidebar-user-info">
          <div class="sidebar-user-name">${escHtml(user.display_name || user.email)}</div>
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
}

// ── Logout ───────────────────────────────────────────────────

async function logout() {
  try { await apiFetch('/api/auth/logout', { method: 'POST' }); } catch { }
  clearAuth();
  window.location.href = '/login.html';
}

// ── Mobile Sidebar ───────────────────────────────────────────

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

// ── XSS Protection ───────────────────────────────────────────

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ── Form Helpers ─────────────────────────────────────────────

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

// ── Workout helpers ──────────────────────────────────────────

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

// ── Weight color logic ────────────────────────────────────────

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

// ── Modal helpers ─────────────────────────────────────────────

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

// ── Confetti ──────────────────────────────────────────────────

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

// ── Clipboard ────────────────────────────────────────────────

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

// ── Draft / AutoSave helpers ──────────────────────────────────

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

// ── DOM Ready ─────────────────────────────────────────────────

function onReady(fn) {
  // Force HTTPS in production
  if (window.location.protocol === 'http:' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    window.location.href = window.location.href.replace('http:', 'https:');
    return;
  }
  if (document.readyState !== 'loading') fn();
  else document.addEventListener('DOMContentLoaded', fn);
}
