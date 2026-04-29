/**
 * PeakForm — Admin Panel
 */

onReady(async () => {
  requireAuth();
  const user = getUser();
  if (!user || user.role !== 'admin') {
    window.location.href = '/dashboard.html';
    return;
  }
  
  await renderSidebar();
  initMobileSidebar();
  loadPendingExercises();
});

async function loadPendingExercises() {
  const data = await apiFetch('/api/exercises/pending');
  const countEl = document.getElementById('pending-count');
  const listEl = document.getElementById('pending-list');
  
  if (data && !data._error) {
    countEl.textContent = data.length;
    
    if (!data.length) {
      listEl.innerHTML = '<div class="text-muted" style="padding:10px 0">No pending exercises.</div>';
      return;
    }
    
    listEl.innerHTML = data.map(ex => `
      <div class="pending-row">
        <div>
          <div class="pending-name">${escHtml(ex.name)}</div>
          <div class="pending-meta">
            ${categoryBadge(ex.category)}
            <span>· ${setTypeBadge(ex.set_type)}</span>
            <span>· 👤 ${escHtml(ex.submitted_by_email || 'Unknown')}</span>
            ${ex.muscles_tags ? `<span>· 🦾 ${escHtml(ex.muscles_tags)}</span>` : ''}
          </div>
        </div>
        <div style="display:flex;gap:8px">
          <button class="btn btn-sm btn-approve" onclick="approveExercise(${ex.id})">✓ Approve</button>
          <button class="btn btn-sm btn-reject" onclick="rejectExercise(${ex.id})">✕ Reject</button>
        </div>
      </div>
    `).join('');
  }
}

async function approveExercise(id) {
  const res = await apiFetch(`/api/exercises/${id}/approve`, { method: 'POST' });
  if (!res._error) {
    showToast('Exercise approved', 'success');
    loadPendingExercises();
  }
}

async function rejectExercise(id) {
  if (!confirm('Are you sure you want to reject this exercise?')) return;
  const res = await apiFetch(`/api/exercises/${id}/reject`, { method: 'POST' });
  if (!res._error) {
    showToast('Exercise rejected', 'info');
    loadPendingExercises();
  }
}
