/**
 * charts.js — PeakForm Analytics & Progress Charts
 * Focused on Workout Frequency, Volume, and Body Weight.
 * No medical leftovers.
 */

const chartInstances = {};
let currentPeriodDays = 30;

const CHART_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(10,14,26,0.95)',
      borderColor: 'rgba(139,92,246,0.3)',
      borderWidth: 1,
      titleColor: '#F0F4FF',
      bodyColor: '#94A3B8',
      padding: 10,
    },
  },
  scales: {
    x: { ticks: { color: '#475569', font: { size: 10 }, maxRotation: 45 }, grid: { color: 'rgba(255,255,255,0.04)' } },
    y: { ticks: { color: '#475569', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.06)' } },
  },
};

function makeChart(id, type, data, options = {}) {
  if (chartInstances[id]) chartInstances[id].destroy();
  const ctx = document.getElementById(id)?.getContext('2d');
  if (!ctx) return;
  chartInstances[id] = new Chart(ctx, { type, data, options: { ...CHART_OPTS, ...options } });
}

function shortLabel(dateStr) {
  const d = new Date(dateStr);
  if (isNaN(d)) return dateStr;
  return d.toLocaleDateString('en-GB', { month: 'short', day: 'numeric' });
}

async function loadAllCharts() {
  showLoading('Loading analytics...');
  
  // Fetch data from standardized PeakForm endpoints
  const [volumeData, weightData, statsData] = await Promise.all([
    apiFetch(`/api/workouts/weekly-volume?weeks=12`, {}, false),
    apiFetch(`/api/body-weight/history?days=${currentPeriodDays}`, {}, false),
    apiFetch(`/api/dashboard/stats`, {}, false),
  ]);

  hideLoading();

  renderSummaryStats(statsData);

  if (volumeData && !volumeData._error) {
    const labels = volumeData.map(w => w.week).reverse();
    const volume = volumeData.map(w => w.total_volume_kg || 0).reverse();
    const sets   = volumeData.map(w => w.total_sets || 0).reverse();

    // Volume Chart
    makeChart('chart-volume', 'line', {
      labels,
      datasets: [{
        label: 'Volume (kg)',
        data: volume,
        borderColor: '#8B5CF6',
        backgroundColor: 'rgba(139,92,246,0.1)',
        borderWidth: 3, 
        pointRadius: 4, 
        fill: true, 
        tension: 0.4,
      }],
    });

    // Sets Chart
    makeChart('chart-sets', 'bar', {
      labels,
      datasets: [{
        label: 'Total Sets',
        data: sets,
        backgroundColor: 'rgba(59,130,246,0.6)',
        borderColor: '#3B82F6',
        borderWidth: 1,
        borderRadius: 4,
      }],
    });
  }

  if (weightData && !weightData._error) {
    const labels = weightData.map(d => shortLabel(d.logged_at));
    const weights = weightData.map(d => d.weight_kg);

    makeChart('chart-weight', 'line', {
      labels,
      datasets: [{
        label: 'Body Weight (kg)',
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
        y: { ...CHART_OPTS.scales.y, beginAtZero: false }
      }
    });
  }
}

function renderSummaryStats(stats) {
  const container = document.getElementById('chart-stats-row');
  if (!container || !stats || stats._error) return;

  container.innerHTML = `
    <div class="stat-card violet">
      <div class="stat-icon violet">🔥</div>
      <div class="stat-value">${stats.streak || 0}</div>
      <div class="stat-label">Day Streak</div>
    </div>
    <div class="stat-card blue">
      <div class="stat-icon blue">🏋️</div>
      <div class="stat-value">${stats.total_workouts || 0}</div>
      <div class="stat-label">Total Workouts</div>
    </div>
    <div class="stat-card success">
      <div class="stat-icon success">📦</div>
      <div class="stat-value">${parseInt(stats.total_volume || 0).toLocaleString()} <small>kg</small></div>
      <div class="stat-label">Total Volume</div>
    </div>
    <div class="stat-card teal">
      <div class="stat-icon teal">🎯</div>
      <div class="stat-value">${stats.prs_count || 0}</div>
      <div class="stat-label">Personal Records</div>
    </div>
  `;
}

function setPeriod(days, btn) {
  currentPeriodDays = days;
  document.querySelectorAll('.chart-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadAllCharts();
}

onReady(() => {
  requireAuth();
  renderSidebar();
  initMobileSidebar();
  loadAllCharts();
});
