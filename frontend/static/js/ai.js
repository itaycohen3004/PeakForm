/**
 * ai.js — PeakForm AI Coach & Training Analysis
 * Replaces legacy coaching with Athlete AI analysis.
 */

let selectedCards = null;

onReady(async () => {
  requireAuth(); // Generic auth is fine for athletes
  renderSidebar();
  initMobileSidebar();

  // Auto-select first card
  const firstCard = document.querySelector('.analysis-type-card .card');
  if (firstCard) selectType(firstCard);

  await loadHistory();
});

function selectType(card) {
  document.querySelectorAll('.analysis-type-card .card').forEach(c => {
    c.style.borderColor = 'transparent';
    c.style.background = '';
  });
  card.style.borderColor = 'var(--violet-primary)';
  card.style.background = 'rgba(139, 92, 246, 0.05)';
}

function getSelectedType() {
  const radio = document.querySelector('input[name="analysis_type"]:checked');
  const highlighted = document.querySelector('.analysis-type-card .card[style*="border-color: var(--violet"]');
  if (highlighted) {
    const label = highlighted.closest('label');
    const input = label?.querySelector('input[type="radio"]');
    return input?.value || 'strength_progression';
  }
  return radio?.value || 'strength_progression';
}

async function runAnalysis() {
  const analysisType = getSelectedType();
  const btn = document.getElementById('analyze-btn');
  btn.classList.add('loading');
  btn.disabled = true;
  btn.textContent = '';

  const result = await apiFetch('/api/ai/analyze', {
    method: 'POST',
    body: { analysis_type: analysisType },
  }, false);

  btn.classList.remove('loading');
  btn.disabled = false;
  btn.textContent = '🤖 Run AI Analysis';

  if (!result || result._error) {
    showToast(result?.error || 'Analysis failed.', 'error');
    return;
  }

  showToast('✅ AI Coach analysis complete!', 'success');
  displayResult(result, analysisType);
  await loadHistory();
}

function displayResult(result, type) {
  const section = document.getElementById('result-section');
  if (!section) return;
  section.style.display = 'block';

  const badge = document.getElementById('result-type-badge');
  if (badge) badge.textContent = type.replace(/_/g, ' ').toUpperCase();

  const cards = document.getElementById('result-cards');
  if (!cards) return;

  cards.innerHTML = `
    <!-- Trends -->
    <div class="card" style="border-color:rgba(139,92,246,0.2)">
      <div style="display:flex;align-items:center;gap:var(--space-sm);margin-bottom:var(--space-md)">
        <div class="stat-icon violet" style="width:36px;height:36px;font-size:1rem">📈</div>
        <div style="font-weight:700">Progression Trends</div>
      </div>
      ${(result.trends || []).map(t => `
        <div style="display:flex;gap:8px;margin-bottom:var(--space-sm)">
          <span style="color:var(--violet-light);flex-shrink:0">→</span>
          <p style="font-size:0.88rem;margin:0">${t}</p>
        </div>
      `).join('') || '<p style="color:var(--text-muted);font-size:0.85rem">No significant trends found yet.</p>'}
    </div>

    <!-- Warnings / Plateaus -->
    <div class="card" style="border-color:rgba(245,158,11,0.2)">
      <div style="display:flex;align-items:center;gap:var(--space-sm);margin-bottom:var(--space-md)">
        <div class="stat-icon warning" style="width:36px;height:36px;font-size:1rem">⚠️</div>
        <div style="font-weight:700">Observations</div>
      </div>
      ${(result.warnings || []).length ? (result.warnings || []).map(w => `
        <div style="display:flex;gap:8px;margin-bottom:var(--space-sm)">
          <span style="color:var(--warning);flex-shrink:0">⚠</span>
          <p style="font-size:0.88rem;margin:0;color:var(--text-secondary)">${w}</p>
        </div>
      `).join('') : '<p style="color:var(--success);font-size:0.85rem">No plateaus or recovery issues detected.</p>'}
    </div>

    <!-- AI Coaching Tips -->
    <div class="card" style="border-color:rgba(20,184,166,0.2)">
      <div style="display:flex;align-items:center;gap:var(--space-sm);margin-bottom:var(--space-md)">
        <div class="stat-icon teal" style="width:36px;height:36px;font-size:1rem">💡</div>
        <div style="font-weight:700">Coach Recommendations</div>
      </div>
      ${(result.recommendations || []).map((r, i) => `
        <div style="display:flex;gap:8px;margin-bottom:var(--space-sm)">
          <span style="color:var(--accent-teal);flex-shrink:0;font-weight:700">${i+1}.</span>
          <p style="font-size:0.88rem;margin:0;color:var(--text-secondary)">${r}</p>
        </div>
      `).join('') || '<p style="color:var(--text-muted);font-size:0.85rem">No specific tips at this time.</p>'}
    </div>
  `;

  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function loadHistory() {
  const data = await apiFetch('/api/ai/results', {}, false);
  const container = document.getElementById('history-list');

  if (!data || data._error || !data.length) {
    container.innerHTML = `
      <div class="empty-state" style="padding:var(--space-lg)">
        <div class="empty-icon">🤖</div>
        <h3>No Coach Insights</h3>
        <p>Run your first AI analysis above to see trends.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = data.map(a => `
    <div style="padding:var(--space-md);border-bottom:1px solid var(--border);cursor:pointer"
      onclick="expandHistory(this, ${JSON.stringify(a).replace(/"/g, '&quot;')})">
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div>
          <span class="badge badge-violet">${a.analysis_type.replace(/_/g, ' ').toUpperCase()}</span>
          <span style="margin-left:8px;font-size:0.75rem;color:var(--text-muted)">${formatDateTime(a.generated_at)}</span>
        </div>
        <span style="color:var(--text-muted);font-size:0.8rem">DETAILS ▼</span>
      </div>
      <div class="history-detail" style="display:none;margin-top:var(--space-md)"></div>
    </div>
  `).join('');
}

function expandHistory(el, analysis) {
  const detail = el.querySelector('.history-detail');
  if (detail.style.display === 'none') {
    detail.style.display = 'block';
    displayResult(analysis, analysis.analysis_type);
  } else {
    detail.style.display = 'none';
  }
}
