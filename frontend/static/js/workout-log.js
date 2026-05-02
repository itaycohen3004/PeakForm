/**
 * PeakForm — Workout Logger
 * Handles all workout logging logic including auto-save.
 */

let workoutId    = null;
let workoutStart = null;
let exercises    = [];   // {exercise_id, name, set_type, weId, sets:[...]}
let allExercises = [];
let timerInterval    = null;
let autoSaveInterval = null;
let isDraft  = false;
let isSaving = false;  // Guard: prevents double-submit

// ── Init ──────────────────────────────────────────────────────

onReady(async () => {
  requireAuth();
  await renderSidebar();
  initMobileSidebar();

  document.getElementById('workout-date').value = todayISO();

  const searchInput = document.getElementById('exercise-search');
  if (searchInput) {
    searchInput.addEventListener('focus', () => searchExercises(''));
  }

  const params        = new URLSearchParams(window.location.search);
  const fromTemplate  = params.get('from_template');
  const workoutIdParam = params.get('workout_id');
  const restoreParam  = params.get('restore');

  if (fromTemplate) {
    await startFromTemplate(parseInt(fromTemplate));
  } else if (workoutIdParam) {
    await resumeWorkout(parseInt(workoutIdParam));
  } else if (restoreParam && hasDraft('active_workout')) {
    restoreFromDraft();
  } else {
    showStartOptions();
  }
});

// ── Start Options ─────────────────────────────────────────────

async function showStartOptions() {
  document.getElementById('start-options').style.display = 'block';
  document.getElementById('workout-logger').style.display = 'none';
  document.getElementById('summary-bar').style.display   = 'none';

  if (hasDraft('active_workout')) {
    document.getElementById('resume-card').style.display = 'block';
  }

  const data = await apiFetch('/api/templates', {}, false);
  if (!data._error) {
    const list = document.getElementById('template-list');
    if (!data.length) {
      list.innerHTML = `<div class="empty-state" style="padding:var(--space-lg)">
        <p>No templates yet. <a href="/templates.html">Create one →</a></p>
      </div>`;
    } else {
      list.innerHTML = data.map(t => `
        <div class="template-select-row" onclick="startFromTemplate(${t.id})">
          <div style="font-weight:700">${escHtml(t.name)}</div>
          <div style="font-size:.8rem;color:var(--text-muted)">${t.exercise_count || 0} exercises · ${t.training_type || ''}</div>
          <div class="btn btn-primary btn-sm" style="margin-left:auto">Select →</div>
        </div>
      `).join('');
    }
  }
}

function startCustom() {
  document.getElementById('start-options').style.display = 'none';
  startWorkoutLogger('Custom Workout');
}

function showTemplateSelector() {
  document.getElementById('template-selector').style.display = 'block';
}

function hideTemplateSelector() {
  document.getElementById('template-selector').style.display = 'none';
}

function checkResumeDraft() {
  restoreFromDraft();
}

// ── Workout Logger ────────────────────────────────────────────

function startWorkoutLogger(name = '') {
  document.getElementById('start-options').style.display = 'none';
  document.getElementById('workout-logger').style.display = 'block';
  document.getElementById('summary-bar').style.display   = 'flex';
  document.getElementById('workout-name').value = name;
  workoutStart = Date.now();
  startTimer();
  startAutoSave();
  loadExerciseList();
}

async function startFromTemplate(templateId) {
  showLoading('Loading template...');
  const tpl = await apiFetch(`/api/templates/${templateId}`, {}, false);
  hideLoading();
  if (tpl._error) { showToast('Failed to load template', 'error'); return; }

  document.getElementById('start-options').style.display = 'none';
  document.getElementById('workout-logger').style.display = 'block';
  document.getElementById('summary-bar').style.display   = 'flex';
  document.getElementById('workout-name').value = tpl.name;

  workoutStart = Date.now();
  startTimer();

  exercises = [];
  for (const ex of (tpl.exercises || [])) {
    const exObj = {
      exercise_id:   ex.exercise_id,
      name:          ex.exercise_name,
      set_type:      ex.set_type || 'reps_weight',
      weId:          null,
      sets:          [],
      lastSession:   null,  // Will be populated below
    };
    const setCount = ex.default_sets || 3;
    for (let i = 0; i < setCount; i++) {
      exObj.sets.push({
        set_number:       i + 1,
        weight_kg:        ex.sets?.[i]?.target_weight || null,
        reps:             ex.default_reps || ex.sets?.[i]?.target_reps || null,
        duration_seconds: null,
        is_warmup:        false,
      });
    }
    exercises.push(exObj);
  }

  renderExercises();
  startAutoSave();
  loadExerciseList();
  showToast(`Template "${tpl.name}" loaded!`, 'success');

  // Fetch last-session intel for each exercise in parallel (background, non-blocking)
  _loadIntelPanels(exercises);
}

async function resumeWorkout(workoutId_) {
  const data = await apiFetch(`/api/workouts/${workoutId_}`);
  if (data._error) { showStartOptions(); return; }

  workoutId = workoutId_;
  document.getElementById('start-options').style.display = 'none';
  document.getElementById('workout-logger').style.display = 'block';
  document.getElementById('summary-bar').style.display   = 'flex';
  document.getElementById('workout-name').value  = data.name || '';
  document.getElementById('workout-date').value  = data.workout_date || todayISO();
  document.getElementById('workout-notes').value = data.notes || '';

  exercises = (data.exercises || []).map(ex => ({
    exercise_id: ex.exercise_id,
    name:        ex.exercise_name,
    set_type:    ex.set_type || 'reps_weight',
    weId:        ex.id,
    sets: (ex.sets || []).map(s => ({
      id:               s.id,
      set_number:       s.set_number,
      weight_kg:        s.weight_kg,
      reps:             s.reps,
      duration_seconds: s.duration_seconds,
      is_warmup:        s.is_warmup,
    })),
  }));

  workoutStart = Date.now();
  startTimer();
  renderExercises();
  startAutoSave();
  loadExerciseList();
}

function restoreFromDraft() {
  const draft = loadDraft('active_workout');
  if (!draft) { showStartOptions(); return; }

  document.getElementById('start-options').style.display = 'none';
  document.getElementById('workout-logger').style.display = 'block';
  document.getElementById('summary-bar').style.display   = 'flex';
  document.getElementById('workout-name').value  = draft.name || '';
  document.getElementById('workout-date').value  = draft.date || todayISO();
  document.getElementById('workout-notes').value = draft.notes || '';

  workoutId    = draft.workoutId || null;
  exercises    = draft.exercises || [];
  workoutStart = draft.startTime
    ? (Date.now() - (draft.savedAt - draft.startTime))
    : Date.now();

  isDraft = true;
  renderExercises();
  startTimer();
  startAutoSave();
  loadExerciseList();
  showToast('Draft restored — keep going! 💪', 'success');
}

// ── In-Workout Intelligence ────────────────────────────────────

async function _loadIntelPanels(exList) {
  // Fetch all last-sessions in parallel
  const results = await Promise.all(
    exList.map(ex =>
      ex.exercise_id
        ? apiFetch(`/api/exercises/${ex.exercise_id}/last-session`, {}, false)
            .catch(() => ({ found: false }))
        : Promise.resolve({ found: false })
    )
  );

  results.forEach((data, idx) => {
    const ex = exList[idx];
    ex.lastSession = (data && data.found) ? data : null;

    // Update just the intel banner div without re-rendering the whole block
    const bannerEl = document.getElementById(`intel-${idx}`);
    if (!bannerEl) return;

    if (ex.lastSession) {
      const intel = ex.lastSession;
      const parts = [];
      if (intel.best_weight != null && intel.best_weight > 0) parts.push(`${intel.best_weight}kg`);
      if (intel.best_reps != null && intel.best_reps > 0) parts.push(`${intel.best_reps} reps`);
      const summary = parts.length ? parts.join(' × ') : 'Bodyweight';
      const dateStr = intel.workout_date ? ` · ${intel.workout_date}` : '';
      const setDetails = intel.sets && intel.sets.length > 1
        ? `<div class="intel-sets">${intel.sets.map(s => {
            const p = [];
            if (s.weight_kg != null) p.push(s.weight_kg + 'kg');
            if (s.reps != null) p.push(s.reps + ' reps');
            if (s.duration_seconds != null) p.push(s.duration_seconds + 's');
            return `<span class="intel-set-pill">Set ${s.set_number}: ${p.join(' × ')}</span>`;
          }).join('')}</div>` : '';
          
      bannerEl.className = 'intel-banner';
      bannerEl.innerHTML = `
        <span class="intel-icon">📊</span>
        <div class="intel-content" style="width:100%">
          <div class="intel-label">Last session${dateStr}</div>
          <div class="intel-value">${summary}</div>
          ${setDetails}
          <div id="ai-rec-${idx}" style="margin-top:8px;padding-top:8px;border-top:1px dashed rgba(255,255,255,0.1);font-size:0.8rem;color:var(--violet-l);display:flex;align-items:center;gap:6px">
            <span class="spinner" style="width:12px;height:12px;border-width:2px;border-top-color:var(--violet-l)"></span> AI analyzing...
          </div>
        </div>`;
        
      // Fetch AI recommendation asynchronously
      apiFetch(`/api/ai/analyze/${ex.exercise_id}`, { method: 'POST' }, false)
        .then(aiRes => {
          const aiEl = document.getElementById(`ai-rec-${idx}`);
          if (!aiEl) return;
          if (aiRes && !aiRes._error && aiRes.next_reps) {
            const w = aiRes.next_weight ? `${aiRes.next_weight}kg × ` : '';
            aiEl.innerHTML = `🤖 <strong>AI Suggests:</strong> ${w}${aiRes.next_reps} reps`;
            aiEl.title = aiRes.progression_note || '';
          } else {
            aiEl.innerHTML = `🤖 <strong>AI Suggests:</strong> Match last session`;
          }
        })
        .catch(() => {
          const aiEl = document.getElementById(`ai-rec-${idx}`);
          if (aiEl) aiEl.style.display = 'none';
        });
        
    } else {
      bannerEl.className = 'intel-banner intel-empty';
      bannerEl.innerHTML = `<span class="intel-icon">💡</span> First time doing this exercise — give it your best!`;
    }
  });
}



// ── Timer ─────────────────────────────────────────────────────

function startTimer() {
  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - workoutStart) / 1000);
    const h = Math.floor(elapsed / 3600);
    const m = Math.floor((elapsed % 3600) / 60);
    const s = elapsed % 60;
    const fmt = h > 0
      ? `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
      : `${m}:${String(s).padStart(2,'0')}`;
    const timerEl = document.getElementById('workout-timer');
    if (timerEl) timerEl.textContent = fmt;
    const sumEl = document.getElementById('sum-duration');
    if (sumEl) sumEl.textContent = fmt;
  }, 1000);
}

// ── Auto Save ─────────────────────────────────────────────────

let _visibilityHandler = null;
let _unloadHandler     = null;

function startAutoSave() {
  clearInterval(autoSaveInterval);
  autoSaveInterval = setInterval(performAutoSave, 15000);

  // Remove stale listeners before attaching new ones (prevents stacking)
  if (_visibilityHandler) document.removeEventListener('visibilitychange', _visibilityHandler);
  if (_unloadHandler)     window.removeEventListener('beforeunload', _unloadHandler);

  _visibilityHandler = () => { if (document.hidden) performAutoSave(); };
  _unloadHandler     = performAutoSave;

  document.addEventListener('visibilitychange', _visibilityHandler);
  window.addEventListener('beforeunload', _unloadHandler);
}

function performAutoSave() {
  const draft = buildDraftData();
  saveDraft('active_workout', draft);
  const indicator = document.getElementById('autosave-indicator');
  if (indicator) {
    indicator.textContent = '💾 Saved';
    setTimeout(() => { if (indicator) indicator.textContent = ''; }, 2000);
  }
}

function buildDraftData() {
  return {
    workoutId,
    name:      document.getElementById('workout-name')?.value  || '',
    date:      document.getElementById('workout-date')?.value  || todayISO(),
    notes:     document.getElementById('workout-notes')?.value || '',
    exercises: exercises.map(ex => ({
      exercise_id: ex.exercise_id,
      name:        ex.name,
      set_type:    ex.set_type,
      weId:        ex.weId,
      sets:        ex.sets,
    })),
    startTime: workoutStart,
    savedAt:   Date.now(),
  };
}

// ── Exercise Management ────────────────────────────────────────

async function loadExerciseList() {
  const data = await apiFetch('/api/exercises', {}, false);
  if (!data._error) allExercises = data;
}

let currentSearchCategory = '';

async function searchExercises(query) {
  const dropdown = document.getElementById('exercise-dropdown');
  const q = query ? query.toLowerCase().trim() : '';

  // 1. Local filter first for speed
  let matches = allExercises.filter(e =>
    e.name.toLowerCase().includes(q) ||
    e.category.toLowerCase().includes(q)
  );

  // 2. If we have a query and local matches are few, fetch from server to find custom/newly approved exercises
  if (q.length >= 2 && matches.length < 10) {
    try {
      const serverMatches = await apiFetch(`/api/exercises?q=${encodeURIComponent(q)}${currentSearchCategory ? '&category='+currentSearchCategory : ''}`, {}, false);
      if (serverMatches && !serverMatches._error) {
        // Merge and unique by ID
        const existingIds = new Set(matches.map(m => m.id));
        serverMatches.forEach(sm => {
          if (!existingIds.has(sm.id)) matches.push(sm);
        });
      }
    } catch(e) { console.warn("Server search failed", e); }
  }

  if (currentSearchCategory) {
    matches = matches.filter(e => e.category.toLowerCase() === currentSearchCategory);
  }

  if (!matches.length) {
    dropdown.innerHTML = '<div style="padding:1rem;color:var(--text-muted);text-align:center">No exercises found</div>';
  } else {
    dropdown.innerHTML = matches.slice(0, 50).map(e => `
      <div class="exercise-option" onclick="addExercise(${e.id}, ${JSON.stringify(e.name).replace(/"/g,'&quot;')}, '${e.set_type}')">
        <span class="ex-icon">${categoryIcon(e.category)}</span>
        <div class="ex-info">
          <div class="ex-name">
            ${escHtml(e.name)}
            ${e.status === 'pending' ? '<span class="badge badge-amber" style="font-size:0.6rem;margin-left:4px">Pending</span>' : ''}
          </div>
          <div class="ex-meta">${escHtml(e.category)} ${e.muscles ? '· ' + escHtml(e.muscles) : ''}</div>
        </div>
        <span class="btn btn-ghost btn-sm" style="margin-left:auto">+</span>
      </div>
    `).join('');
  }
  dropdown.style.display = 'block';
}

function filterCategory(cat) {
  currentSearchCategory = cat;
  searchExercises(document.getElementById('exercise-search').value);
  document.querySelectorAll('.cat-btn').forEach(b => {
    b.classList.remove('btn-primary');
    if (b.dataset.cat === cat) b.classList.add('btn-primary');
  });
}

function addExercise(exId, exName, setType) {
  if (exercises.find(e => e.exercise_id === exId)) {
    showToast(`${exName} already in this workout`, 'warning');
    document.getElementById('exercise-dropdown').style.display = 'none';
    document.getElementById('exercise-search').value = '';
    return;
  }
  exercises.push({
    exercise_id: exId,
    name:        exName,
    set_type:    setType || 'reps_weight',
    weId:        null,
    sets: [{ set_number: 1, weight_kg: null, reps: null, duration_seconds: null, is_warmup: false }],
  });
  document.getElementById('exercise-dropdown').style.display = 'none';
  document.getElementById('exercise-search').value = '';
  renderExercises();
  updateSummary();
  performAutoSave();
}

function removeExercise(idx) {
  exercises.splice(idx, 1);
  renderExercises();
  updateSummary();
  performAutoSave();
}

function addSet(exIdx) {
  const ex = exercises[exIdx];
  if (!ex) return;
  const lastSet = ex.sets[ex.sets.length - 1] || {};
  ex.sets.push({
    set_number:       ex.sets.length + 1,
    weight_kg:        lastSet.weight_kg,
    reps:             lastSet.reps,
    duration_seconds: lastSet.duration_seconds,
    is_warmup:        false,
  });
  renderExercises();
  updateSummary();
  performAutoSave();
}

function removeSet(exIdx, setIdx) {
  exercises[exIdx].sets.splice(setIdx, 1);
  exercises[exIdx].sets.forEach((s, i) => s.set_number = i + 1);
  renderExercises();
  updateSummary();
  performAutoSave();
}

function updateSetField(exIdx, setIdx, field, value) {
  const set = exercises[exIdx]?.sets[setIdx];
  if (!set) return;
  set[field] = value === '' ? null : (field === 'is_warmup' ? value : parseFloat(value) || null);
  updateSummary();
  performAutoSave();

  // Trigger AI set-by-set recommendation when a working set is fully logged
  const ex = exercises[exIdx];
  if (!set.is_warmup && field !== 'is_warmup' && set.weight_kg && set.reps && ex.exercise_id) {
    _fetchAiNextSetSuggestion(exIdx, setIdx);
  }
}

// Debounce per-exercise to avoid rapid firing
const _aiDebounce = {};
function _fetchAiNextSetSuggestion(exIdx, setIdx) {
  clearTimeout(_aiDebounce[exIdx]);
  _aiDebounce[exIdx] = setTimeout(async () => {
    const ex = exercises[exIdx];
    const workingSets = ex.sets.filter(s => !s.is_warmup && s.weight_kg && s.reps);
    const nextSetNum = workingSets.length + 1;
    // Show loading hint on the intel banner
    const bannerEl = document.getElementById(`intel-${exIdx}`);
    const aiEl = document.getElementById(`ai-rec-${exIdx}`);
    if (aiEl) {
      aiEl.innerHTML = `<span class="spinner" style="width:10px;height:10px;border-width:2px"></span> Analyzing Set ${workingSets.length}…`;
    }
    try {
      const res = await apiFetch(`/api/ai/analyze/${ex.exercise_id}`, { method: 'POST' }, false);
      if (aiEl && res && !res._error && res.next_reps) {
        const w = res.next_weight ? `${res.next_weight}kg × ` : '';
        aiEl.innerHTML = `🤖 <strong>Set ${nextSetNum} Target:</strong> ${w}${res.next_reps} reps`;
        if (res.progression_note) aiEl.title = res.progression_note;
      } else if (aiEl) {
        aiEl.style.display = 'none';
      }
    } catch(_) {
      if (aiEl) aiEl.style.display = 'none';
    }
  }, 800);
}

// ── Render ────────────────────────────────────────────────────

function renderExercises() {
  const container = document.getElementById('exercises-container');
  if (!exercises.length) {
    container.innerHTML = `<div class="empty-state mb-xl"><div class="empty-icon">💪</div><p>Search and add exercises above to start your workout.</p></div>`;
    return;
  }
  container.innerHTML = exercises.map((ex, exIdx) => renderExerciseBlock(ex, exIdx)).join('');
}

function renderExerciseBlock(ex, exIdx) {
  const isRW   = ex.set_type === 'reps_weight';
  const isRO   = ex.set_type === 'reps_only';
  const isTime = ex.set_type === 'time_only';
  const isTW   = ex.set_type === 'time_weight';

  const setRows = ex.sets.map((s, sIdx) => `
    <div class="set-row ${s.is_warmup ? 'set-warmup' : ''}">
      <div class="set-num">${s.is_warmup ? 'W' : s.set_number}</div>
      ${(isRW || isTW) ? `
        <input type="number" class="set-input weight-input" placeholder="kg" step="0.5" min="0"
               value="${s.weight_kg != null ? s.weight_kg : ''}"
               onchange="updateSetField(${exIdx},${sIdx},'weight_kg',this.value)"
               oninput="updateSetField(${exIdx},${sIdx},'weight_kg',this.value)">
      ` : ''}
      ${(isRW || isRO) ? `
        <input type="number" class="set-input reps-input" placeholder="reps" min="1" max="999"
               value="${s.reps != null ? s.reps : ''}"
               onchange="updateSetField(${exIdx},${sIdx},'reps',this.value)"
               oninput="updateSetField(${exIdx},${sIdx},'reps',this.value)">
      ` : ''}
      ${(isTime || isTW) ? `
        <input type="number" class="set-input time-input" placeholder="sec" min="1"
               value="${s.duration_seconds != null ? s.duration_seconds : ''}"
               onchange="updateSetField(${exIdx},${sIdx},'duration_seconds',this.value)"
               oninput="updateSetField(${exIdx},${sIdx},'duration_seconds',this.value)">
      ` : ''}
      <label class="warmup-toggle" title="Warmup set">
        <input type="checkbox" ${s.is_warmup ? 'checked' : ''} onchange="updateSetField(${exIdx},${sIdx},'is_warmup',this.checked)">
        <span>W</span>
      </label>
      <button class="set-remove" onclick="removeSet(${exIdx},${sIdx})" title="Remove set">✕</button>
    </div>
  `).join('');

  // Intel banner — shows previous session data if available
  const intel = ex.lastSession;
  let intelHtml = '';
  if (intel === undefined) {
    // Still loading
    intelHtml = `<div class="intel-banner loading" id="intel-${exIdx}"><span class="intel-spinner"></span> Loading previous stats…</div>`;
  } else if (intel) {
    const parts = [];
    if (intel.best_weight != null && intel.best_weight > 0) parts.push(`${intel.best_weight}kg`);
    if (intel.best_reps != null && intel.best_reps > 0) parts.push(`${intel.best_reps} reps`);
    const summary = parts.length ? parts.join(' × ') : 'Bodyweight';
    const dateStr = intel.workout_date ? ` · ${intel.workout_date}` : '';
    intelHtml = `
      <div class="intel-banner" id="intel-${exIdx}">
        <span class="intel-icon">📊</span>
        <div class="intel-content">
          <div class="intel-label">Last session${dateStr}</div>
          <div class="intel-value">${summary}</div>
          ${intel.sets.length > 1 ? `<div class="intel-sets">${intel.sets.map(s => {
            const p = [];
            if (s.weight_kg != null) p.push(s.weight_kg+'kg');
            if (s.reps != null) p.push(s.reps+' reps');
            if (s.duration_seconds != null) p.push(s.duration_seconds+'s');
            return `<span class="intel-set-pill">Set ${s.set_number}: ${p.join(' × ')}</span>`;
          }).join('')}</div>` : ''}
        </div>
      </div>`;
  } else {
    // null = loaded, no data
    intelHtml = `<div class="intel-banner intel-empty" id="intel-${exIdx}"><span class="intel-icon">💡</span> No previous data for this exercise yet.</div>`;
  }

  return `
    <div class="exercise-block" id="ex-block-${exIdx}">
      <div class="exercise-block-header">
        <div class="exercise-block-icon">${categoryIcon(allExercises.find(e=>e.id===ex.exercise_id)?.category||'')}</div>
        <div class="exercise-block-name">${escHtml(ex.name)}</div>
        <button class="btn btn-ghost btn-sm" onclick="requestAiSetSuggestion(${exIdx})"
                id="ai-suggest-btn-${exIdx}"
                style="margin-left:auto;color:var(--violet-l);border:1px solid rgba(139,92,246,0.3);
                       padding:3px 8px;font-size:.75rem;border-radius:var(--radius-sm);
                       white-space:nowrap;flex-shrink:0"
                title="Get an AI recommendation for your next set">
          🤖 AI Suggest
        </button>
        <button class="btn btn-ghost btn-sm" onclick="removeExercise(${exIdx})" style="color:var(--text-xmuted)">✕</button>
      </div>
      <!-- AI set suggestion result — shown directly under the title, before history -->
      <div id="ai-set-suggestion-${exIdx}"
           style="display:none;margin-top:6px;padding:10px 12px;
                  background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.25);
                  border-radius:var(--radius-sm);font-size:0.82rem;color:var(--text-secondary)">
      </div>
      ${intelHtml}
      <div class="sets-table">
        <div class="sets-table-header">
          <div class="set-num-header">Set</div>
          ${(isRW || isTW) ? '<div class="set-header">Weight (kg)</div>' : ''}
          ${(isRW || isRO) ? '<div class="set-header">Reps</div>' : ''}
          ${(isTime || isTW) ? '<div class="set-header">Seconds</div>' : ''}
          <div class="set-header">W</div>
          <div></div>
        </div>
        <div id="sets-${exIdx}">${setRows}</div>
      </div>
      <div class="exercise-block-footer">
        <button class="btn btn-ghost btn-sm" onclick="addSet(${exIdx})">+ Add Set</button>
        <div style="font-size:.75rem;color:var(--text-muted)" id="ex-vol-${exIdx}"></div>
      </div>
    </div>
  `;
}


function updateSummary() {
  let totalSets = 0, totalVol = 0;
  for (const ex of exercises) {
    for (const s of ex.sets) {
      if (!s.is_warmup) totalSets++;
      if (s.weight_kg && s.reps) totalVol += s.weight_kg * s.reps;
    }
  }
  const exEl  = document.getElementById('sum-exercises');
  const setEl = document.getElementById('sum-sets');
  const volEl = document.getElementById('sum-volume');
  if (exEl)  exEl.textContent  = exercises.length;
  if (setEl) setEl.textContent = totalSets;
  if (volEl) volEl.textContent = Math.round(totalVol);
}

// ── Finish button state ───────────────────────────────────────

function setFinishButtonsState(saving) {
  // Target both the header button and the summary bar button
  const btns = [
    document.getElementById('finish-btn'),
    document.getElementById('summary-finish-btn'),
  ].filter(Boolean);

  btns.forEach(btn => {
    if (saving) {
      btn.disabled = true;
      if (!btn.dataset.originalText) btn.dataset.originalText = btn.textContent;
      btn.innerHTML = `<span style="display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:spin 0.7s linear infinite;vertical-align:middle;margin-right:6px"></span> Saving…`;
    } else {
      btn.disabled = false;
      btn.textContent = btn.dataset.originalText || '✓ Finish';
    }
  });
}

// Inject spinner animation once
if (!document.getElementById('spin-style')) {
  const s = document.createElement('style');
  s.id = 'spin-style';
  s.textContent = '@keyframes spin{to{transform:rotate(360deg)}}';
  document.head.appendChild(s);
}

// ── Finish Workout ────────────────────────────────────────────

async function finishWorkout() {
  // Prevent double-submit
  if (isSaving) return;
  if (!exercises.length) {
    showToast('Add at least one exercise before finishing', 'warning');
    return;
  }

  isSaving = true;
  setFinishButtonsState(true);

  const name     = document.getElementById('workout-name')?.value?.trim() || 'Workout';
  const date     = document.getElementById('workout-date')?.value || todayISO();
  const notes    = document.getElementById('workout-notes')?.value?.trim() || '';
  const duration = workoutStart ? Math.floor((Date.now() - workoutStart) / 60000) : 0;

  try {
    // ── Phase 1: Create or update the workout record ──────────
    if (!workoutId) {
      const created = await apiFetch('/api/workouts', {
        method: 'POST',
        body: { name, workout_date: date, notes, duration_minutes: duration, is_draft: 0 },
      }, false);
      if (created._error) throw new Error(created.message || 'Could not create workout');
      workoutId = created.id;
    } else {
      // Best-effort update — ignore failure, workout already exists
      await apiFetch(`/api/workouts/${workoutId}`, {
        method: 'PATCH',
        body: { name, workout_date: date, notes, duration_minutes: duration,
                finished_at: new Date().toISOString(), is_draft: 0 },
      }, false);
    }

    // ── Phase 2: Persist exercises & sets (idempotent) ────────
    for (let i = 0; i < exercises.length; i++) {
      const ex = exercises[i];

      if (!ex.weId) {
        const weRes = await apiFetch(`/api/workouts/${workoutId}/exercises`, {
          method: 'POST',
          body: { exercise_id: ex.exercise_id, position: i },
        }, false);
        if (weRes._error) throw new Error(`Could not save exercise "${ex.name}"`);
        ex.weId = weRes.id;
      }

      for (const s of ex.sets) {
        if (s.id) continue;  // already persisted — skip
        const setRes = await apiFetch(`/api/workouts/exercises/${ex.weId}/sets`, {
          method: 'POST',
          body: {
            set_number:       s.set_number,
            weight_kg:        s.weight_kg,
            reps:             s.reps,
            duration_seconds: s.duration_seconds,
            is_warmup:        s.is_warmup ? 1 : 0,
            rpe:              s.rpe || null,
          },
        }, false);
        if (!setRes._error) s.id = setRes.id; // mark persisted for idempotency
      }
    }

    // ── Phase 3: Finalize metrics (best-effort — never blocks) ─
    // Even if /finish fails (e.g. a model bug), the workout IS saved.
    // We do NOT retry or show an error for this step.
    try {
      await apiFetch(`/api/workouts/${workoutId}/finish`, {
        method: 'POST',
        body: { duration_minutes: duration, notes },
      }, false);
    } catch (_) {
      // Metrics computation failed — workout data is still safe
      console.warn('[finishWorkout] /finish endpoint failed — data still saved');
    }

    // ── Phase 4: Background PR computation ────────────────────
    apiFetch('/api/athletes/prs/compute', { method: 'POST' }, false).catch(() => {});

    // ── Phase 5: Success ──────────────────────────────────────
    clearDraft('active_workout');
    clearInterval(timerInterval);
    clearInterval(autoSaveInterval);

    showToast('✅ Workout saved! Great session! 💪', 'success');
    setTimeout(() => { window.location.href = `/workout-detail.html?id=${workoutId}`; }, 900);

  } catch (err) {
    // Only reaches here if Phase 1 or 2 genuinely failed
    console.error('[finishWorkout] Error:', err.message);
    isSaving = false;
    setFinishButtonsState(false);
    showToast(`❌ ${err.message || 'Failed to save workout'}. Please try again.`, 'error');
  }
}

// ── Discard ───────────────────────────────────────────────────

function showDiscardConfirm() {
  openModal('discard-modal');
}

function discardWorkout() {
  clearDraft('active_workout');
  clearInterval(timerInterval);
  clearInterval(autoSaveInterval);
  window.location.href = '/dashboard.html';
}

// ── Close dropdown on outside click ──────────────────────────

document.addEventListener('click', e => {
  const dd     = document.getElementById('exercise-dropdown');
  const search = document.getElementById('exercise-search');
  if (dd && search && !search.contains(e.target) && !dd.contains(e.target)) {
    dd.style.display = 'none';
  }
});

// ── AI Suggest All Sets ───────────────────────────────────────

/**
 * Called when the user clicks the AI button on an exercise block.
 * Fetches recommendations for ALL planned sets in one request and
 * renders them as a compact table above the intel/history banner.
 * Re-clicking replaces the previous prediction (no duplicates).
 */
async function requestAiSetSuggestion(exIdx) {
  const ex = exercises[exIdx];
  if (!ex || !ex.exercise_id) return;

  const btn    = document.getElementById(`ai-suggest-btn-${exIdx}`);
  const dispEl = document.getElementById(`ai-set-suggestion-${exIdx}`);
  if (!dispEl) return;

  // ── Loading state ────────────────────────────────────────────
  const origLabel = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled  = true;
    btn.innerHTML = '⏳ Generating…';
  }
  dispEl.style.display = 'block';
  dispEl.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;color:var(--text-muted);font-size:.82rem">
      <span class="spinner" style="width:12px;height:12px;border-width:2px;border-top-color:var(--violet-l)"></span>
      AI is analyzing your history for all ${ex.sets.filter(s => !s.is_warmup).length || ex.sets.length} sets…
    </div>`;

  const currentSets = ex.sets.map(s => ({
    weight_kg:        s.weight_kg        ?? null,
    reps:             s.reps             ?? null,
    duration_seconds: s.duration_seconds ?? null,
    is_warmup:        !!s.is_warmup,
  }));

  // Determine how many working sets the user has planned
  const numSets = Math.max(
    ex.sets.filter(s => !s.is_warmup).length,
    1
  );

  try {
    const res = await apiFetch('/api/ai/suggest-all-sets', {
      method: 'POST',
      body: {
        exercise_id:  ex.exercise_id,
        num_sets:     numSets,
        current_sets: currentSets,
        workout_id:   workoutId || null,
      },
    }, false);

    if (res._error) {
      dispEl.innerHTML = `<span style="color:var(--text-muted)">⚠️ Could not generate prediction right now. Keep going! 💪</span>`;
      return;
    }

    // ── No history case ──────────────────────────────────────────
    if (res.source === 'no_history') {
      dispEl.innerHTML = `
        <div style="display:flex;align-items:flex-start;gap:8px">
          <span style="font-size:1rem">💡</span>
          <span style="color:var(--text-muted);font-size:.82rem">${escHtml(res.overall_note)}</span>
        </div>`;
      return;
    }

    // ── Save prediction on the exercise object (survives re-renders) ─
    ex.aiSuggestions = res.sets || [];
    const srcIcon = res.source === 'ai' ? '🤖' : '📊';
    const srcLabel = res.source === 'ai' ? 'AI Prediction' : 'Based on your history';

    const isRW = ex.set_type === 'reps_weight';
    const isRO = ex.set_type === 'reps_only';
    const isTime = ex.set_type === 'time_only';
    const isTW = ex.set_type === 'time_weight';

    // Build table rows
    const rows = (res.sets || []).map(s => {
      let targets = [];
      if (s.weight_kg != null) targets.push(`<strong>${s.weight_kg}kg</strong>`);
      if (s.reps      != null) targets.push(`<strong>${s.reps} reps</strong>`);
      if (s.seconds   != null) targets.push(`<strong>${s.seconds}s</strong>`);
      if (s.rpe)               targets.push(`<span style="opacity:.7">RPE ${escHtml(s.rpe)}</span>`);
      const targetStr = targets.join(' × ') || '—';
      const note = s.note ? `<div style="font-size:.73rem;color:var(--text-muted);margin-top:2px">${escHtml(s.note)}</div>` : '';
      return `
        <div style="display:grid;grid-template-columns:48px 1fr;gap:6px;align-items:start;
                    padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
          <div style="font-size:.78rem;color:var(--text-muted);font-weight:600;padding-top:2px">
            Set ${s.set_number}
          </div>
          <div>
            <div style="font-size:.82rem;color:var(--text-primary)">${targetStr}</div>
            ${note}
          </div>
        </div>`;
    }).join('');

    dispEl.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <div style="font-size:.78rem;font-weight:700;color:var(--violet-l);
                    text-transform:uppercase;letter-spacing:.05em">
          ${srcIcon} ${srcLabel}
        </div>
        <button onclick="document.getElementById('ai-set-suggestion-${exIdx}').style.display='none'"
                style="background:none;border:none;cursor:pointer;color:var(--text-xmuted);
                       font-size:.75rem;padding:0">✕ hide</button>
      </div>
      ${res.overall_note ? `<div style="font-size:.8rem;color:var(--text-muted);margin-bottom:8px;
                                        padding-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.08)">
        ${escHtml(res.overall_note)}</div>` : ''}
      ${rows}`;

  } catch (err) {
    dispEl.innerHTML = `<span style="color:var(--text-muted)">⚠️ AI prediction unavailable. Keep training! 💪</span>`;
    console.warn('[AI suggest-all-sets] error:', err);
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = origLabel; }
  }
}

