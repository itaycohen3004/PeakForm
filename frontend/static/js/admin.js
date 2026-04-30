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
  loadAdminStats();
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
      <div class="pending-row" id="pending-${ex.id}">
        <div>
          <div class="pending-name">${escHtml(ex.name)}</div>
          <div class="pending-meta">
            ${categoryBadge(ex.category)}
            <span>· ${setTypeBadge(ex.set_type)}</span>
            ${ex.equipment ? `<span>· 🛠 ${escHtml(ex.equipment)}</span>` : ''}
            <span>· 👤 ${escHtml(ex.submitted_by_email || 'Unknown')}</span>
            ${ex.muscles_tags ? `<span>· 🦴 ${escHtml(ex.muscles_tags)}</span>` : ''}
          </div>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="btn btn-sm btn-approve" onclick="approveExercise(${ex.id}, this)">&#10003; Approve</button>
          <button class="btn btn-sm btn-reject" onclick="confirmReject(${ex.id}, this)">✕ Reject</button>
        </div>
        <div id="confirm-reject-${ex.id}" style="display:none;width:100%;margin-top:8px;padding:8px;background:rgba(239,68,68,.1);border-radius:8px;border:1px solid rgba(239,68,68,.3)">
          <span style="font-size:.85rem;color:var(--red)">Reject this exercise? This cannot be undone.</span>
          <div style="display:flex;gap:6px;margin-top:6px">
            <button class="btn btn-sm btn-reject" onclick="rejectExercise(${ex.id}, this)">❌ Yes, Reject</button>
            <button class="btn btn-sm btn-ghost" onclick="cancelReject(${ex.id})">Cancel</button>
          </div>
        </div>
      </div>
    `).join('');
  }
}

async function approveExercise(id, btn) {
  if (btn) { btn.disabled = true; btn.textContent = 'Approving...'; }
  const res = await apiFetch(`/api/exercises/${id}/approve`, { method: 'POST' });
  if (!res._error) {
    showToast('Exercise approved ✅', 'success');
    document.getElementById(`pending-${id}`)?.remove();
    const countEl = document.getElementById('pending-count');
    if (countEl) countEl.textContent = Math.max(0, (parseInt(countEl.textContent) || 1) - 1);
  } else {
    if (btn) { btn.disabled = false; btn.textContent = '✓ Approve'; }
  }
}

function confirmReject(id, btn) {
  const confirmRow = document.getElementById(`confirm-reject-${id}`);
  if (confirmRow) confirmRow.style.display = 'block';
}

function cancelReject(id) {
  const confirmRow = document.getElementById(`confirm-reject-${id}`);
  if (confirmRow) confirmRow.style.display = 'none';
}

async function rejectExercise(id, btn) {
  if (btn) { btn.disabled = true; btn.textContent = 'Rejecting...'; }
  const res = await apiFetch(`/api/exercises/${id}/reject`, { method: 'POST' });
  if (!res._error) {
    showToast('Exercise rejected', 'info');
    document.getElementById(`pending-${id}`)?.remove();
    const countEl = document.getElementById('pending-count');
    if (countEl) countEl.textContent = Math.max(0, (parseInt(countEl.textContent) || 1) - 1);
  } else {
    if (btn) { btn.disabled = false; btn.textContent = '❌ Yes, Reject'; }
  }
}
async function createChatRoom() {
  const name = (document.getElementById('new-room-name')?.value || '').trim();
  const desc = (document.getElementById('new-room-desc')?.value || '').trim();
  if (!name) { showToast('Room name is required', 'warning'); return; }

  const btn = document.querySelector('[onclick="createChatRoom()"]');
  if (btn) { btn.disabled = true; btn.textContent = 'Creating...'; }

  const res = await apiFetch('/api/chat/rooms', { method: 'POST', body: { name, description: desc } });
  if (btn) { btn.disabled = false; btn.textContent = '➕ Create Room'; }

  if (!res._error) {
    showToast(`Room "${name}" created! ✅ It now appears in Live Chat.`, 'success');
    document.getElementById('new-room-name').value = '';
    document.getElementById('new-room-desc').value = '';
  }
}

async function loadAdminStats() {
  const el = document.getElementById('admin-stats');
  if (!el) return;
  const data = await apiFetch('/api/admin/stats', {}, false);
  if (!data || data._error) {
    el.innerHTML = '<span style="color:var(--text-muted);font-size:.85rem">Could not load stats.</span>';
    return;
  }
  el.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:16px">
      <div class="card" style="text-align:center;padding:16px">
        <div style="font-size:1.8rem;font-weight:900;color:var(--violet-l)">${data.total_users ?? 0}</div>
        <div style="font-size:.75rem;color:var(--text-muted);margin-top:4px">Total Users</div>
      </div>
      <div class="card" style="text-align:center;padding:16px">
        <div style="font-size:1.8rem;font-weight:900;color:var(--green-l)">${data.total_workouts ?? 0}</div>
        <div style="font-size:.75rem;color:var(--text-muted);margin-top:4px">Total Workouts</div>
      </div>
    </div>
  `;
}
