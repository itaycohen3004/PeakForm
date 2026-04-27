/**
 * goals.js — Goals & Achievements page
 */

onReady(async () => {
  requireAuth();
  await renderSidebar();
  initMobileSidebar();
  await loadGoals();
});

async function loadGoals() {
  const goals = await apiFetch('/api/goals', {}, false);
  if (!goals || goals._error) return;

  const active    = goals.filter(g => !g.is_completed);
  const completed = goals.filter(g => g.is_completed);

  renderGoals('active-goals-grid', active, false);
  renderGoals('completed-goals-grid', completed, true);
}

const GOAL_CONFIG = {
  exercise_weight:     { label: 'Exercise Weight', unit: 'kg', icon: '🏋️', color: 'violet' },
  exercise_reps:       { label: 'Exercise Reps', unit: 'reps', icon: '🔁', color: 'teal' },
  exercise_1rm:        { label: '1RM Target', unit: 'kg', icon: '💪', color: 'amber' },
  weekly_frequency:    { label: 'Weekly Frequency', unit: 'workouts', icon: '📅', color: 'blue' },
  body_weight_target:  { label: 'Body Weight', unit: 'kg', icon: '⚖️', color: 'emerald' },
  workout_count:       { label: 'Total Workouts', unit: 'sessions', icon: '📊', color: 'indigo' },
  volume_target:       { label: 'Weekly Volume', unit: 'kg', icon: '📈', color: 'rose' },
  streak_days:         { label: 'Day Streak', unit: 'days', icon: '🔥', color: 'orange' },
  custom:              { label: 'Custom Goal', unit: '', icon: '⭐', color: 'slate' },
};

function renderGoals(containerId, goals, completed) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!goals.length) {
    container.innerHTML = `
      <div style="grid-column:1/-1">
        <div class="empty-state" style="padding:var(--space-lg)">
          <div class="empty-icon">${completed ? '🏆' : '🎯'}</div>
          <h3>${completed ? 'No completed goals yet' : 'No active goals'}</h3>
          ${!completed ? '<p><button class="btn btn-primary btn-sm" onclick="openGoalModal()">Set your first goal</button></p>' : ''}
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = goals.map(g => {
    const config = GOAL_CONFIG[g.goal_type] || GOAL_CONFIG.custom;
    const pct    = Math.min(100, Math.round((g.current_value / Math.max(g.target_value, 0.01)) * 100));

    return `
      <div class="card" style="${completed ? 'border-color:rgba(16,185,129,0.3);background:rgba(16,185,129,0.03)' : ''}">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:var(--space-md)">
          <div style="display:flex;align-items:center;gap:var(--space-sm)">
            <div class="stat-icon ${config.color}" style="width:36px;height:36px;font-size:1rem">${config.icon}</div>
            <div>
              <div style="font-weight:700;color:var(--text-primary)">${escHtml(g.title)}</div>
              <div style="font-size:0.72rem;color:var(--text-muted)">${config.label} ${g.deadline ? `· Due ${formatDate(g.deadline)}` : ''}</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:6px">
            ${completed ? '<span class="badge badge-success">🏆 Done</span>' : ''}
            ${!completed ? `<button class="btn btn-ghost btn-xs" onclick="updateProgress(${g.id}, ${g.current_value}, '${config.label}')">✏️</button>` : ''}
            <button class="btn btn-danger btn-xs" onclick="deleteGoal(${g.id})">🗑</button>
          </div>
        </div>

        <div style="display:flex;justify-content:space-between;margin-bottom:6px">
          <span style="font-size:0.82rem;color:var(--text-muted)">Progress</span>
          <span style="font-size:0.88rem;font-weight:700;color:${pct >= 100 ? 'var(--green-l)' : 'var(--violet-l)'}">
            ${g.current_value} / ${g.target_value} ${g.unit || config.unit}
          </span>
        </div>

        <div class="progress-wrap">
          <div class="progress-bar ${pct >= 100 ? 'success' : config.color}" style="width:${pct}%"></div>
        </div>

        <div style="display:flex;justify-content:space-between;margin-top:6px">
          <span style="font-size:0.78rem;color:var(--text-muted)">${pct}% complete</span>
          ${pct >= 100 && !completed ? '<span style="font-size:0.8rem;color:var(--green)">🎉 Goal achieved!</span>' : ''}
        </div>
      </div>
    `;
  }).join('');
}

function openGoalModal() {
  openModal('goal-modal');
}

function closeGoalModal() {
  closeModal('goal-modal');
}

async function saveGoal() {
  const type_el = document.getElementById('goal_type');
  const target_el = document.getElementById('target_value');
  const title_el = document.getElementById('goal_title');
  
  const payload = {
    goal_type:    type_el.value,
    title:        title_el.value.trim() || type_el.options[type_el.selectedIndex].text,
    target_value: parseFloat(target_el.value),
    deadline:     document.getElementById('deadline').value || null,
    unit:         GOAL_CONFIG[type_el.value]?.unit || '',
  };

  if (!payload.target_value || payload.target_value <= 0) {
    showToast('Please enter a valid target value.', 'warning');
    return;
  }

  const result = await apiFetch('/api/goals', { method: 'POST', body: payload });
  if (result && !result._error) {
    showToast('🎯 Goal created!', 'success');
    closeGoalModal();
    target_el.value = '';
    title_el.value = '';
    await loadGoals();
  }
}

async function updateProgress(goalId, currentVal, label) {
  const val = prompt(`Update progress for "${label}":`, currentVal);
  if (val === null) return;
  const num = parseFloat(val);
  if (isNaN(num)) { showToast('Invalid value.', 'error'); return; }

  const result = await apiFetch(`/api/goals/${goalId}/progress`, {
    method: 'PATCH',
    body: { current_value: num },
  });

  if (result && !result._error) {
    if (result.is_completed) {
      showToast('🏆 Goal achieved! Great work!', 'success');
      launchConfetti();
    } else {
      showToast('Progress updated!', 'success');
    }
    await loadGoals();
  }
}

async function deleteGoal(goalId) {
  if (!confirm('Delete this goal selected?')) return;
  const result = await apiFetch(`/api/goals/${goalId}`, { method: 'DELETE' });
  if (result && !result._error) {
    showToast('Goal deleted.', 'success');
    await loadGoals();
  }
}

