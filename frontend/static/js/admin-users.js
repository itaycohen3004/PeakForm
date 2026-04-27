/**
 * admin-users.js — PeakForm Admin User Management
 * Manage Athletes and Admins. Toggle status, reset passwords, delete accounts.
 */

let allUsers = [];

onReady(async () => {
  requireAuth('admin');
  renderSidebar();
  initMobileSidebar();
  await loadUsers();
});

async function loadUsers() {
  const data = await apiFetch('/api/admin/users?limit=200', {}, false);
  if (!data || data._error) return;
  allUsers = data.users || data || [];
  renderUsers(allUsers);
}

function filterUsers() {
  const search = document.getElementById('search-input').value.toLowerCase();
  const role   = document.getElementById('role-filter').value;
  const status = document.getElementById('status-filter').value;

  let filtered = Array.isArray(allUsers) ? allUsers : [];
  if (search) filtered = filtered.filter(u => u.email.toLowerCase().includes(search));
  if (role)   filtered = filtered.filter(u => u.role === role);
  
  if (status === 'locked') filtered = filtered.filter(u => u.is_locked);
  if (status === 'active') filtered = filtered.filter(u => !u.is_locked);
  
  renderUsers(filtered);
}

function renderUsers(users) {
  const container = document.getElementById('users-table');
  if (!container) return;

  if (!users.length) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">👥</div><h3>No users found</h3></div>`;
    return;
  }

  container.innerHTML = `
    <div class="table-wrapper">
      <table class="table">
        <thead>
          <tr><th>Email</th><th>Role</th><th>Status</th><th>Joined</th><th>Actions</th></tr>
        </thead>
        <tbody>
          ${users.map(u => `
            <tr>
              <td>
                <div style="display:flex;align-items:center;gap:8px">
                  <div class="sidebar-user-avatar" style="width:32px;height:32px;font-size:0.75rem">${u.email.substring(0,2).toUpperCase()}</div>
                  <div style="font-weight:600">${u.email}</div>
                </div>
              </td>
              <td>${roleBadge(u.role)}</td>
              <td><span class="badge ${u.is_locked ? 'badge-danger' : 'badge-green'}">${u.is_locked ? 'Locked' : 'Active'}</span></td>
              <td>${formatDate(u.created_at)}</td>
              <td>
                <div style="display:flex;gap:4px;flex-wrap:wrap">
                  <button class="btn btn-outline btn-xs" onclick="toggleLock(${u.id}, ${u.is_locked})">
                    ${u.is_locked ? '🔓 Unlock' : '🔒 Lock'}
                  </button>
                  <button class="btn btn-danger btn-xs" onclick="deleteUser(${u.id}, '${u.email}')">🗑 Delete</button>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
    <div style="padding:var(--space-md);font-size:0.8rem;color:var(--text-muted)">
      Showing ${users.length} user${users.length !== 1 ? 's' : ''}
    </div>
  `;
}

async function toggleLock(userId, currentStatus) {
  const action = currentStatus ? 'unlock' : 'lock';
  const result = await apiFetch(`/api/admin/users/${userId}/${action}`, { method: 'POST' });
  if (result && !result._error) {
    showToast(`User ${action}ed successfully.`, 'success');
    await loadUsers();
  }
}

async function deleteUser(userId, email) {
  if (!confirm(`Permanently delete account ${email}? Historical workout data will be preserved but anonymized.`)) return;
  const result = await apiFetch(`/api/admin/users/${userId}`, { method: 'DELETE' });
  if (result && !result._error) {
    showToast('User account deleted.', 'success');
    await loadUsers();
  }
}

function openCreateModal() {
  document.getElementById('new-email').value = '';
  openModal('create-modal');
}

async function createUser() {
  const email    = document.getElementById('new-email').value.trim();
  const password = document.getElementById('new-password').value;
  const role     = document.getElementById('new-role').value;

  if (!email || !password) {
    showToast('Email and password required.', 'warning');
    return;
  }

  const result = await apiFetch('/api/auth/register_admin', {
    method: 'POST',
    body: { email, password, role },
  });

  if (result && !result._error) {
    showToast(`✅ User ${email} created!`, 'success');
    closeModal('create-modal');
    await loadUsers();
  }
}
