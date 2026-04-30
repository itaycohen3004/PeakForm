/**
 * PeakForm — Templates Manager
 */

let _templates = [];
let _allExercises = [];
let _newTplExercises = []; // { id, name, default_sets, _te_id }
let _editTplId = null;
let _isViewMode = false;

onReady(async () => {
  requireAuth();
  await renderSidebar();
  initMobileSidebar();
  
  loadTemplates();
  loadExercises();
});

async function loadTemplates() {
  const data = await apiFetch('/api/templates');
  if (data && !data._error) {
    _templates = data;
    renderTemplates();
  }
}

async function loadExercises() {
  const data = await apiFetch('/api/exercises', {}, false);
  if (data && !data._error) {
    _allExercises = data;
  }
}

function renderTemplates() {
  const list = document.getElementById('templates-list');
  if (!_templates.length) {
    list.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><p>You haven't created any templates yet.</p></div>`;
    return;
  }
  
  list.innerHTML = _templates.map(t => `
    <div class="template-card">
      <div class="template-header">
        <div>
          <div class="template-title">${escHtml(t.name)}</div>
          <div class="template-meta">${trainingTypeBadge(t.training_type || 'gym')} · ${t.exercise_count || 0} exercises</div>
        </div>
        <div style="display:flex;gap:6px">
          <a href="/log-workout.html?from_template=${t.id}" class="btn btn-sm btn-primary">Start</a>
          <button class="btn btn-sm btn-ghost" onclick="viewTemplate(${t.id})" style="color:var(--text-muted)">👁 View</button>
          <button class="btn btn-sm btn-ghost" onclick="editTemplate(${t.id})" style="color:var(--text-muted)">✏️ Edit</button>
          <button class="btn btn-sm btn-ghost" onclick="shareTemplate(${t.id})" style="color:var(--accent-teal)">📢 Share</button>
          <button class="btn btn-sm btn-ghost" onclick="deleteTemplate(${t.id})" style="color:var(--text-muted)">🗑</button>
        </div>
      </div>
    </div>
  `).join('');
}

function openTemplateModal(mode, tpl = null) {
  _editTplId = tpl ? tpl.id : null;
  _isViewMode = mode === 'view';
  
  const title = mode === 'view' ? '📋 View Template' : (tpl ? '✏️ Edit Template' : '✨ Create Template');
  document.getElementById('tpl-modal-title').innerHTML = title;
  
  document.getElementById('tpl-name').value = tpl ? tpl.name : '';
  document.getElementById('tpl-type').value = tpl ? (tpl.training_type || 'gym') : 'gym';
  
  document.getElementById('tpl-name').disabled = _isViewMode;
  document.getElementById('tpl-type').disabled = _isViewMode;
  document.getElementById('tpl-exercise-search-wrap').style.display = _isViewMode ? 'none' : 'block';
  document.getElementById('save-tpl-btn').style.display = _isViewMode ? 'none' : 'block';
  
  _newTplExercises = [];
  if (tpl && tpl.exercises) {
    _newTplExercises = tpl.exercises.map(e => ({ 
      id: e.exercise_id, 
      name: e.exercise_name, 
      default_sets: e.default_sets || 3,
      _te_id: e.id // existing template_exercise.id
    }));
  }
  
  renderNewTplExercises();
  openModal('template-modal');
}

async function viewTemplate(id) {
  const data = await apiFetch(`/api/templates/${id}`);
  if (!data._error) openTemplateModal('view', data);
}

async function editTemplate(id) {
  const data = await apiFetch(`/api/templates/${id}`);
  if (!data._error) openTemplateModal('edit', data);
}

function searchTplExercises(query) {
  const dropdown = document.getElementById('tpl-exercise-dropdown');
  const q = query.toLowerCase();
  if (!q) { dropdown.style.display = 'none'; return; }
  
  const matches = _allExercises.filter(e => 
    e.name.toLowerCase().includes(q) || 
    e.category.toLowerCase().includes(q)
  ).slice(0, 20);
  
  if (!matches.length) {
    dropdown.innerHTML = '<div style="padding:10px;color:var(--text-muted)">No exercises found</div>';
  } else {
    dropdown.innerHTML = matches.map(e => `
      <div class="exercise-option" onclick="addTplExercise(${e.id}, '${escHtml(e.name).replace(/'/g, "\\'")}')">
        <div>
          <div class="exercise-option-name">${escHtml(e.name)}</div>
          <div class="exercise-option-meta">${escHtml(e.category)}</div>
        </div>
        <span style="color:var(--violet)">+ Add</span>
      </div>
    `).join('');
  }
  dropdown.style.display = 'block';
}

function addTplExercise(id, name) {
  if (_newTplExercises.find(e => e.id === id)) {
    showToast('Exercise already added', 'warning');
    return;
  }
  _newTplExercises.push({ id, name, default_sets: 3 });
  document.getElementById('tpl-exercise-search').value = '';
  document.getElementById('tpl-exercise-dropdown').style.display = 'none';
  renderNewTplExercises();
}

function removeTplExercise(idx) {
  _newTplExercises.splice(idx, 1);
  renderNewTplExercises();
}

function updateTplSets(idx, val) {
  _newTplExercises[idx].default_sets = parseInt(val) || 3;
}

function renderNewTplExercises() {
  const container = document.getElementById('tpl-exercises-container');
  if (!_newTplExercises.length) {
    container.innerHTML = '<div style="font-size:.8rem;color:var(--text-xmuted);text-align:center;padding:10px;border:1px dashed var(--bg-border);border-radius:var(--radius-sm)">No exercises added yet.</div>';
    return;
  }
  
  container.innerHTML = _newTplExercises.map((e, idx) => `
    <div class="template-exercise-item">
      <div class="ex-item-info">
        <div class="ex-item-name">${escHtml(e.name)}</div>
      </div>
      <div style="display:flex;align-items:center;gap:6px">
        <label style="font-size:.7rem;color:var(--text-muted)">Sets</label>
        <input type="number" value="${e.default_sets}" min="1" max="10" 
          onchange="updateTplSets(${idx}, this.value)" 
          ${_isViewMode ? 'disabled' : ''}
          style="width:50px;background:var(--bg-input);border:1px solid var(--bg-border);border-radius:4px;padding:4px;color:var(--text-primary);text-align:center">
      </div>
      ${_isViewMode ? '' : `<button class="btn btn-ghost btn-sm" onclick="removeTplExercise(${idx})" style="padding:4px">✕</button>`}
    </div>
  `).join('');
}

async function saveTemplate() {
  const name = document.getElementById('tpl-name').value.trim();
  const type = document.getElementById('tpl-type').value;
  
  if (!name) { showToast('Please enter a template name', 'error'); return; }
  if (!_newTplExercises.length) { showToast('Please add at least one exercise', 'error'); return; }
  
  const btn = document.getElementById('save-tpl-btn');
  btn.disabled = true; btn.textContent = 'Saving...';
  
  if (_editTplId) {
    // 1. Update basic info
    await apiFetch(`/api/templates/${_editTplId}`, {
      method: 'PATCH',
      body: { name, training_type: type }
    });
    
    // 2. Fetch existing template to sync exercises
    const existing = await apiFetch(`/api/templates/${_editTplId}`);
    if (!existing._error) {
      // Delete old exercises not in new list
      const newExIds = _newTplExercises.map(e => e.id);
      for (const ex of existing.exercises) {
        if (!newExIds.includes(ex.exercise_id)) {
          await apiFetch(`/api/templates/exercises/${ex.id}`, { method: 'DELETE' });
        }
      }
      // Add new exercises not in old list
      const oldExIds = existing.exercises.map(e => e.exercise_id);
      for (const [idx, ex] of _newTplExercises.entries()) {
        if (!oldExIds.includes(ex.id)) {
          await apiFetch(`/api/templates/${_editTplId}/exercises`, {
            method: 'POST',
            body: { exercise_id: ex.id, position: idx, default_sets: ex.default_sets }
          });
        }
      }
    }
    showToast('Template updated successfully!', 'success');
  } else {
    // Create new
    const payload = {
      name,
      training_type: type,
      exercises: _newTplExercises.map(e => ({ name: e.name, default_sets: e.default_sets }))
    };
    const res = await apiFetch('/api/templates', { method: 'POST', body: payload });
    if (!res._error) showToast('Template created successfully!', 'success');
  }
  
  btn.disabled = false; btn.textContent = 'Save Template';
  closeModal('template-modal');
  loadTemplates();
}

async function deleteTemplate(id) {
  if (!confirm('Are you sure you want to delete this template?')) return;
  const res = await apiFetch(`/api/templates/${id}`, { method: 'DELETE' });
  if (!res._error) {
    showToast('Template deleted', 'success');
    loadTemplates();
  }
}

async function shareTemplate(id) {
  console.log(`[DEBUG] Sharing template ID: ${id}...`);
  // Fetch full template with exercises
  const tpl = await apiFetch(`/api/templates/${id}`);
  if (tpl._error) {
    showToast('Could not load template', 'error');
    console.error('[DEBUG] Failed to load template', tpl);
    return;
  }

  const exList = (tpl.exercises || []).map(e =>
    `  • ${e.exercise_name} — ${e.default_sets || 3} sets`
  ).join('\n');

  const content = `📋 Sharing my workout template: ${tpl.name}\n\n${exList}\n\n[Save this template to your library!]`;

  const metaData = {
    template_id: id,
    template_name: tpl.name,
    training_type: tpl.training_type,
    exercises: (tpl.exercises || []).map(e => ({
      name: e.exercise_name,
      default_sets: e.default_sets || 3,
    }))
  };

  console.log('[DEBUG] Sending template to /api/community/posts', { content, post_type: 'template', meta_data: metaData });
  const res = await apiFetch('/api/community/posts', {
    method: 'POST',
    body: { content, post_type: 'template', meta_data: metaData }
  });

  if (!res._error) {
    showToast('Template shared to Community Feed!', 'success');
    alert('Success! Template was shared to the Community Feed.');
    console.log('[DEBUG] Successfully shared template. Response:', res);
    window.location.href = '/community.html';
  } else {
    showToast('Failed to share template', 'error');
    alert('Error: Failed to share template.');
    console.error('[DEBUG] Failed to share template:', res);
  }
}
