/**
 * KidZora Admin — Analytics charts
 *
 * Usage: include this script on any page that has
 *   <div id="analytics-root" data-api-url="/admin/analytics/data"></div>
 *
 * Period tabs:    #periodTabs  (buttons with data-period="daily|weekly|monthly|yearly")
 * Sub-period bar: #subPeriodBar  (injected dynamically)
 * KPI ids:        #kpiRevenue, #kpiCommission, #kpiOrders,
 *                 #kpiCompleted, #kpiCancelled, #kpiNewUsers
 * Chart canvases: #chartRevenue, #chartOrders, #chartStatus,
 *                 #chartTopSellers, #chartNewUsers
 */

/* ── Constants ──────────────────────────────────────────────────── */
const ADM_COLORS = {
  indigo : '#6366f1',
  green  : '#22c55e',
  blue   : '#3b82f6',
  amber  : '#f59e0b',
  red    : '#ef4444',
  cyan   : '#06b6d4',
  purple : '#a855f7',
  pink   : '#ec4899',
};

const STATUS_COLORS = {
  pending          : '#f59e0b',
  confirmed        : '#06b6d4',
  preparing        : '#a855f7',
  ready_for_pickup : '#3b82f6',
  out_for_delivery : '#6366f1',
  delivered        : '#22c55e',
  completed        : '#16a34a',
  cancelled        : '#ef4444',
};

/* Sub-options shown under each period tab */
const SUB_OPTIONS = {
  daily   : [], // hourly — no sub needed
  weekly  : ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'],
  monthly : [], // will be generated from API labels
  yearly  : ['January','February','March','April','May','June',
             'July','August','September','October','November','December'],
};

const PERIOD_DESC = {
  daily   : 'Today — hour by hour (00:00–23:00)',
  weekly  : 'This week — Monday to Sunday',
  monthly : 'This month — day by day',
  yearly  : 'This year — January to December',
};

/* ── Helpers ─────────────────────────────────────────────────────── */
const peso = v =>
  '\u20b1' + Number(v).toLocaleString('en-PH', { minimumFractionDigits:2, maximumFractionDigits:2 });

let _charts   = {};
let _apiData  = null;   // cache last fetch
let _apiUrl   = '';
let _activeSub = null;

function destroyAll () {
  Object.values(_charts).forEach(c => { try { c.destroy(); } catch (_) {} });
  _charts = {};
}

/* ── Init ────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('analytics-root');
  if (!root) return;
  _apiUrl = root.dataset.apiUrl || '/admin/analytics/data';

  // Period tab clicks
  document.querySelectorAll('#periodTabs button[data-period]').forEach(btn => {
    btn.addEventListener('click', () => switchPeriod(btn.dataset.period));
  });

  // Initial load — daily
  switchPeriod('daily');
});

/* ── Period switch ───────────────────────────────────────────────── */
function switchPeriod (period) {
  _activeSub = null;

  // Highlight active tab
  document.querySelectorAll('#periodTabs button[data-period]').forEach(btn => {
    const on = btn.dataset.period === period;
    btn.classList.toggle('btn-primary', on);
    btn.classList.toggle('btn-outline-secondary', !on);
    btn.setAttribute('aria-pressed', on);
  });

  // Period description
  const desc = document.getElementById('periodLabel');
  if (desc) desc.innerHTML = PERIOD_DESC[period] || period;

  // Show skeleton loaders for charts
  ['Revenue','Orders','Status','TopSellers','NewUsers'].forEach(k => {
    const el = document.getElementById('chart' + k);
    if (el) {
      el.style.display = 'none';
      el.classList.add('skeleton-hidden');
    }
  });

  // Render sub-period bar
  renderSubBar(period, null);

  // Spinner in KPI cells
  setKpiSpinners();

  // Fetch data
  fetch(_apiUrl + '?period=' + period)
    .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(d => {
      _apiData = d;
      renderAll(d);
      fillKpis(d.kpis);
    })
    .catch(err => {
      console.error('Analytics fetch error:', err);
      fillKpisError();
    });
}

/* ── Sub-period bar ──────────────────────────────────────────────── */
function renderSubBar (period, activeSub) {
  const bar = document.getElementById('subPeriodBar');
  if (!bar) return;

  // Monthly → show date-range picker instead of pills
  if (period === 'monthly') {
    const now   = new Date();
    const y     = now.getFullYear();
    const m     = String(now.getMonth() + 1).padStart(2, '0');
    const today = now.toISOString().slice(0, 10);
    const monthStart = `${y}-${m}-01`;

    bar.innerHTML = `
      <div class="adm-date-picker">
        <label class="adm-date-label" for="drpStart">From</label>
        <input type="date" id="drpStart" class="adm-date-input"
               value="${monthStart}">
        <label class="adm-date-label" for="drpEnd">To</label>
        <input type="date" id="drpEnd" class="adm-date-input"
               value="${today}">
        <button class="btn btn-primary btn-sm" onclick="applyDateRange()">
          <i class="fas fa-search me-1"></i>Apply
        </button>
        <button class="btn btn-outline-secondary btn-sm" onclick="resetDateRange()">
          <i class="fas fa-undo me-1"></i>Reset
        </button>
      </div>`;
    return;
  }

  const opts = SUB_OPTIONS[period] || [];
  if (!opts.length) { bar.innerHTML = ''; return; }

  bar.innerHTML = opts.map(opt => {
    const on = opt === activeSub;
    return `<button class="btn btn-sm ${on ? 'btn-primary' : 'btn-outline-secondary'} adm-sub-tabs-btn"
                    data-sub="${opt}" onclick="applySub('${opt}')"
                    style="border-radius:14px;font-size:.72rem;padding:.18rem .65rem">
              ${opt}
            </button>`;
  }).join('');
}

/* ── Custom date range (monthly picker) ─────────────────────────── */
function applyDateRange () {
  const startEl = document.getElementById('drpStart');
  const endEl   = document.getElementById('drpEnd');
  if (!startEl || !endEl) return;

  const start = startEl.value;
  const end   = endEl.value;
  if (!start || !end) return;
  if (start > end) {
    alert('Start date must be before end date.');
    return;
  }

  setKpiSpinners();

  fetch(`${_apiUrl}?period=custom&start=${start}&end=${end}`)
    .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(d => {
      _apiData = d;
      renderAll(d);
      fillKpis(d.kpis);
      const desc = document.getElementById('periodLabel');
      if (desc) desc.innerHTML = `Custom range: ${start} → ${end}`;
    })
    .catch(err => {
      console.error('Custom range fetch error:', err);
      fillKpisError();
    });
}

function resetDateRange () {
  setKpiSpinners();
  fetch(_apiUrl + '?period=monthly')
    .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(d => {
      _apiData = d;
      renderAll(d);
      fillKpis(d.kpis);
      const desc = document.getElementById('periodLabel');
      if (desc) desc.innerHTML = PERIOD_DESC['monthly'];
      // Reset date inputs to current month
      const now = new Date();
      const y = now.getFullYear();
      const m = String(now.getMonth() + 1).padStart(2, '0');
      const startEl = document.getElementById('drpStart');
      const endEl   = document.getElementById('drpEnd');
      if (startEl) startEl.value = `${y}-${m}-01`;
      if (endEl)   endEl.value   = now.toISOString().slice(0, 10);
    })
    .catch(err => {
      console.error('Reset error:', err);
      fillKpisError();
    });
}

/* ── Sub-filter click ────────────────────────────────────────────── */
function applySub (sub) {
  if (!_apiData) return;

  // Toggle off if already active
  if (_activeSub === sub) {
    _activeSub = null;
    highlightSub(null);
    renderAll(_apiData);
    return;
  }

  _activeSub = sub;
  highlightSub(sub);

  // Filter data to the single selected sub-label
  const idx = _apiData.labels.indexOf(sub);
  if (idx === -1) { renderAll(_apiData); return; }

  const filtered = {
    labels      : [sub],
    revenue     : [_apiData.revenue[idx]],
    commission  : [_apiData.commission[idx]],
    order_counts: [_apiData.order_counts[idx]],
    new_users   : [_apiData.new_users[idx]],
    status_dist : _apiData.status_dist,   // keep global for doughnut
    top_sellers : _apiData.top_sellers,   // keep global
    kpis        : {
      revenue    : _apiData.revenue[idx],
      commission : _apiData.commission[idx],
      orders     : _apiData.order_counts[idx],
      completed  : _apiData.kpis.completed,
      cancelled  : _apiData.kpis.cancelled,
      new_users  : _apiData.new_users[idx],
    },
  };

  renderAll(filtered);
  fillKpis(filtered.kpis);
}

function highlightSub (sub) {
  document.querySelectorAll('.adm-sub-tabs-btn').forEach(btn => {
    const on = btn.dataset.sub === sub;
    btn.classList.toggle('btn-primary', on);
    btn.classList.toggle('btn-outline-secondary', !on);
  });
}

/* ── Render all charts ───────────────────────────────────────────── */
function renderAll (d) {
  destroyAll();
  buildRevenue(d);
  buildOrders(d);
  buildStatus(d);
  buildTopSellers(d);
  buildNewUsers(d);
  
  // Show charts after rendering (hide skeleton)
  ['Revenue','Orders','Status','TopSellers','NewUsers'].forEach(k => {
    const el = document.getElementById('chart' + k);
    if (el) {
      el.style.display = '';
      el.classList.remove('skeleton-hidden');
    }
  });
}

/* ── KPI helpers ─────────────────────────────────────────────────── */
function setKpiSpinners () {
  ['Revenue','Commission','Orders','Completed','Cancelled','NewUsers'].forEach(k => {
    const el = document.getElementById('kpi' + k);
    if (el) {
      // Use skeleton shimmer instead of spinner
      el.classList.add('skeleton');
      el.style.height = '28px';
      el.style.width = '70%';
      el.innerHTML = '';
    }
  });
}
function fillKpis (k) {
  const set = (id, val) => { 
    const el = document.getElementById(id); 
    if (el) {
      el.classList.remove('skeleton');
      el.style.height = 'auto';
      el.style.width = 'auto';
      el.textContent = val;
    }
  };
  set('kpiRevenue',    peso(k.revenue));
  set('kpiCommission', peso(k.commission));
  set('kpiOrders',     k.orders);
  set('kpiCompleted',  k.completed);
  set('kpiCancelled',  k.cancelled);
  set('kpiNewUsers',   k.new_users);
}
function fillKpisError () {
  ['Revenue','Commission','Orders','Completed','Cancelled','NewUsers'].forEach(k => {
    const el = document.getElementById('kpi' + k);
    if (el) el.textContent = '—';
  });
}

/* ── Chart 1: Revenue vs Commission (area line) ──────────────────── */
function buildRevenue (d) {
  const el = document.getElementById('chartRevenue');
  if (!el) return;
  
  // Empty state: no revenue data
  const prev = el.previousElementSibling;
  if (prev && prev.classList.contains('chart-no-data')) prev.remove();
  if (!d.revenue || !d.revenue.length || d.revenue.every(v => !v)) {
    el.insertAdjacentHTML('beforebegin',
      '<div class="chart-no-data text-muted small text-center mt-3 mb-3"><i class="fas fa-chart-line fa-2x opacity-25 mb-2 d-block"></i>No revenue data in this period.</div>');
    return;
  }
  
  _charts.rev = new Chart(el, {
    type: 'line',
    data: {
      labels: d.labels,
      datasets: [
        {
          label: 'Revenue (\u20b1)',
          data: d.revenue,
          borderColor: ADM_COLORS.green,
          backgroundColor: 'rgba(34,197,94,.12)',
          fill: true, tension: .4, pointRadius: 3, pointHoverRadius: 6,
        },
        {
          label: 'Commission (\u20b1)',
          data: d.commission,
          borderColor: ADM_COLORS.indigo,
          backgroundColor: 'rgba(99,102,241,.10)',
          fill: true, tension: .4, pointRadius: 3, pointHoverRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top', labels: { usePointStyle: true, boxWidth: 8 } },
        tooltip: { callbacks: { label: c => '  ' + c.dataset.label + ': ' + peso(c.parsed.y) } },
      },
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => '\u20b1' + v.toLocaleString() } },
        x: { grid: { display: false } },
      },
    },
  });
}

/* ── Chart 2: Orders volume (bar) ────────────────────────────────── */
function buildOrders (d) {
  const el = document.getElementById('chartOrders');
  if (!el) return;
  
  // Empty state: no orders data
  const prev = el.previousElementSibling;
  if (prev && prev.classList.contains('chart-no-data')) prev.remove();
  if (!d.order_counts || !d.order_counts.length || d.order_counts.every(v => !v)) {
    el.insertAdjacentHTML('beforebegin',
      '<div class="chart-no-data text-muted small text-center mt-3 mb-3"><i class="fas fa-shopping-bag fa-2x opacity-25 mb-2 d-block"></i>No orders in this period.</div>');
    return;
  }
  
  _charts.ord = new Chart(el, {
    type: 'bar',
    data: {
      labels: d.labels,
      datasets: [{
        label: 'Orders',
        data: d.order_counts,
        backgroundColor: 'rgba(59,130,246,.75)',
        borderColor: ADM_COLORS.blue,
        borderWidth: 1,
        borderRadius: 5,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
        x: { grid: { display: false } },
      },
    },
  });
}

/* ── Chart 3: Status doughnut ────────────────────────────────────── */
function buildStatus (d) {
  const el = document.getElementById('chartStatus');
  if (!el) return;
  // Remove any previous "no data" note
  const prev = el.nextElementSibling;
  if (prev && prev.classList.contains('chart-no-data')) prev.remove();

  const keys = Object.keys(d.status_dist || {});
  if (!keys.length) {
    el.insertAdjacentHTML('afterend',
      '<p class="chart-no-data text-muted small text-center mt-3">No orders in this period.</p>');
    return;
  }
  _charts.stat = new Chart(el, {
    type: 'doughnut',
    data: {
      labels: keys.map(s => s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())),
      datasets: [{
        data: keys.map(s => d.status_dist[s]),
        backgroundColor: keys.map(s => STATUS_COLORS[s] || '#94a3b8'),
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      cutout: '60%',
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8, font: { size: 11 } } },
      },
    },
  });
}

/* ── Chart 4: Top sellers (horizontal bar) ───────────────────────── */
function truncLabel (s, max = 16) {
  return s.length > max ? s.slice(0, max) + '\u2026' : s;
}

function buildTopSellers (d) {
  const el = document.getElementById('chartTopSellers');
  if (!el) return;
  const prev = el.nextElementSibling;
  if (prev && prev.classList.contains('chart-no-data')) prev.remove();

  if (!d.top_sellers || !d.top_sellers.labels.length) {
    el.insertAdjacentHTML('afterend',
      '<p class="chart-no-data text-muted small text-center mt-3">No seller data this period.</p>');
    return;
  }
  _charts.sell = new Chart(el, {
    type: 'bar',
    data: {
      labels: d.top_sellers.labels.map(l => truncLabel(l)),
      datasets: [{
        label: 'Revenue (\u20b1)',
        data: d.top_sellers.data,
        borderRadius: 6,
        backgroundColor: [
          'rgba(99,102,241,.85)',
          'rgba(34,197,94,.85)',
          'rgba(245,158,11,.85)',
          'rgba(239,68,68,.85)',
          'rgba(6,182,212,.85)',
        ],
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: c => d.top_sellers.labels[c[0].dataIndex],
            label: c => '  ' + peso(c.parsed.x),
          },
        },
      },
      scales: {
        x: { beginAtZero: true, ticks: { callback: v => '\u20b1' + v.toLocaleString() } },
        y: { grid: { display: false } },
      },
    },
  });
}

/* ── Chart 5: New users (area line) ──────────────────────────────── */
function buildNewUsers (d) {
  const el = document.getElementById('chartNewUsers');
  if (!el) return;
  
  // Empty state: no user signup data
  const prev = el.previousElementSibling;
  if (prev && prev.classList.contains('chart-no-data')) prev.remove();
  if (!d.new_users || !d.new_users.length || d.new_users.every(v => !v)) {
    el.insertAdjacentHTML('beforebegin',
      '<div class="chart-no-data text-muted small text-center mt-3 mb-3"><i class="fas fa-user-plus fa-2x opacity-25 mb-2 d-block"></i>No new user signups in this period.</div>');
    return;
  }
  
  _charts.usr = new Chart(el, {
    type: 'line',
    data: {
      labels: d.labels,
      datasets: [{
        label: 'New Users',
        data: d.new_users,
        borderColor: ADM_COLORS.cyan,
        backgroundColor: 'rgba(6,182,212,.12)',
        fill: true, tension: .4, pointRadius: 3, pointHoverRadius: 6,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
        x: { grid: { display: false } },
      },
    },
  });
}
