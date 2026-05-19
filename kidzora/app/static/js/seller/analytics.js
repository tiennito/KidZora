/**
 * KidZora Seller — Analytics charts
 *
 * Reads data-api-url from #slr-analytics-root and renders 4 charts:
 *   #slrChartRevenue     — Revenue vs Earnings (line)
 *   #slrChartOrders      — Orders Volume (bar)
 *   #slrChartStatus      — Order Status (doughnut)
 *   #slrChartTopProducts — Top 5 Products by Revenue (horizontal bar)
 *
 * KPI ids: #slrKpiRevenue, #slrKpiEarnings, #slrKpiOrders,
 *          #slrKpiCompleted, #slrKpiCancelled, #slrKpiProducts
 */

const SLR_COLORS = {
  blue   : '#3b82f6',
  green  : '#22c55e',
  amber  : '#f59e0b',
  red    : '#ef4444',
  indigo : '#6366f1',
  cyan   : '#06b6d4',
  purple : '#a855f7',
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

const PERIOD_DESC = {
  daily   : 'Today — hour by hour',
  weekly  : 'This week — Monday to Sunday',
  monthly : 'This month — day by day',
  yearly  : 'This year — January to December',
};

const peso = v =>
  '\u20b1' + Number(v).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

let _charts        = {};
let _apiUrl        = '';
let commissionPct  = 5;  // overwritten from data-commission-pct

function destroyAll() {
  Object.values(_charts).forEach(c => { try { c.destroy(); } catch (_) {} });
  _charts = {};
}

/* ── Skeleton helpers ──────────────────────────────────────────────────── */
const _CHART_IDS   = ['slrChartRevenue', 'slrChartOrders', 'slrChartStatus', 'slrChartTopProducts'];
const _SKEL_IDS    = ['slrSkelRevenue',  'slrSkelOrders',  'slrSkelStatus',  'slrSkelTopProducts'];
const _KPI_IDS     = ['slrKpiRevenue', 'slrKpiEarnings', 'slrKpiOrders', 'slrKpiCompleted', 'slrKpiCancelled', 'slrKpiProducts'];
const _KPISKEL_IDS = ['slrSkelKpiRevenue', 'slrSkelKpiEarnings', 'slrSkelKpiOrders', 'slrSkelKpiCompleted', 'slrSkelKpiCancelled', 'slrSkelKpiProducts'];

function setSkeletons(show) {
  _SKEL_IDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('slr-sk-active', show);
  });
  _CHART_IDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = show ? 'none' : '';
  });
  _KPISKEL_IDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('slr-sk-active', show);
  });
  _KPI_IDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('slr-sk-hidden', show);
  });
}

/* ── Init ──────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('slr-analytics-root');
  if (!root) return;
  _apiUrl       = root.dataset.apiUrl || '/seller/analytics/data';
  commissionPct = parseFloat(root.dataset.commissionPct) || 5;

  document.querySelectorAll('#slrPeriodTabs button[data-period]').forEach(btn => {
    btn.addEventListener('click', () => switchPeriod(btn.dataset.period));
  });

  // Custom range apply
  const applyBtn = document.getElementById('slrApplyCustom');
  if (applyBtn) {
    applyBtn.addEventListener('click', () => {
      const s = document.getElementById('slrDateStart').value;
      const e = document.getElementById('slrDateEnd').value;
      if (!s || !e) return;
      loadData(`custom&start=${s}&end=${e}`, `${s} → ${e}`);
    });
  }

  switchPeriod('weekly');
});

/* ── Period switch ─────────────────────────────────────────────────────── */
function switchPeriod(period) {
  document.querySelectorAll('#slrPeriodTabs button[data-period]').forEach(btn => {
    const on = btn.dataset.period === period;
    btn.classList.toggle('btn-primary', on);
    btn.classList.toggle('btn-outline-secondary', !on);
  });

  const lbl = document.getElementById('slrPeriodLabel');
  if (lbl) lbl.textContent = PERIOD_DESC[period] || period;

  const customRow = document.getElementById('slrCustomRow');
  if (customRow) customRow.style.display = period === 'custom' ? 'flex' : 'none';

  if (period !== 'custom') loadData(period, PERIOD_DESC[period] || period);
}

/* ── Fetch + render ────────────────────────────────────────────────────── */
function loadData(period, periodLabel) {
  const spinner = document.getElementById('slrSpinner');
  if (spinner) spinner.style.display = 'block';
  setSkeletons(true);

  fetch(`${_apiUrl}?period=${period}`)
    .then(r => r.json())
    .then(data => {
      if (spinner) spinner.style.display = 'none';
      setSkeletons(false);
      updateKPIs(data.kpis || {});
      renderRevenue(data.labels, data.revenue, data.earnings);
      renderOrders(data.labels, data.order_counts);
      renderStatus(data.status_dist || {});
      renderTopProducts(data.top_products || []);
    })
    .catch(err => {
      if (spinner) spinner.style.display = 'none';
      setSkeletons(false);
      console.error('[seller analytics]', err);
    });
}

/* ── KPIs ──────────────────────────────────────────────────────────────── */
function updateKPIs(kpis) {
  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };
  set('slrKpiRevenue',   peso(kpis.revenue   || 0));
  set('slrKpiEarnings',  peso(kpis.earnings  || 0));
  set('slrKpiOrders',    kpis.orders          || 0);
  set('slrKpiCompleted', kpis.completed        || 0);
  set('slrKpiCancelled', kpis.cancelled        || 0);
  set('slrKpiProducts',  kpis.active_products  || 0);
}

/* ── Chart helpers ─────────────────────────────────────────────────────── */
function mkChart(id, config) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  if (_charts[id]) { try { _charts[id].destroy(); } catch (_) {} }
  _charts[id] = new Chart(canvas.getContext('2d'), config);
}

const gridColor  = 'rgba(0,0,0,.05)';
const fontFamily = "'Segoe UI', system-ui, sans-serif";

/* ── Revenue vs Earnings ───────────────────────────────────────────────── */
function renderRevenue(labels, revenue, earnings) {
  // Empty state: no revenue data
  if (!labels || !labels.length || (revenue && !revenue.some(v => v)) || (earnings && !earnings.some(v => v))) {
    const canvas = document.getElementById('slrChartRevenue');
    if (canvas) {
      const prev = canvas.previousElementSibling;
      if (prev && prev.classList.contains('chart-no-data')) prev.remove();
      canvas.insertAdjacentHTML('beforebegin',
        '<div class="chart-no-data text-muted small text-center mt-3 mb-3"><i class="fas fa-chart-line fa-2x opacity-25 mb-2 d-block"></i>No revenue data for this period yet.</div>');
    }
    return;
  }
  
  mkChart('slrChartRevenue', {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Revenue (Total Sales)',
          data: revenue,
          borderColor: SLR_COLORS.blue,
          backgroundColor: 'rgba(59,130,246,.08)',
          fill: true, tension: 0.4, pointRadius: 3,
        },
        {
          label: 'Your Earnings (after ' + commissionPct + '% commission)',
          data: earnings,
          borderColor: SLR_COLORS.green,
          backgroundColor: 'rgba(34,197,94,.08)',
          fill: true, tension: 0.4, pointRadius: 3,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'top', labels: { font: { family: fontFamily } } },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${peso(ctx.parsed.y)}`,
          },
        },
      },
      scales: {
        x: { grid: { color: gridColor } },
        y: {
          grid: { color: gridColor },
          ticks: { callback: v => '\u20b1' + Number(v).toLocaleString('en-PH') },
        },
      },
    },
  });
}

/* ── Orders Volume ─────────────────────────────────────────────────────── */
function renderOrders(labels, counts) {
  // Empty state: no orders data
  if (!labels || !labels.length || !counts || !counts.some(v => v)) {
    const canvas = document.getElementById('slrChartOrders');
    if (canvas) {
      const prev = canvas.previousElementSibling;
      if (prev && prev.classList.contains('chart-no-data')) prev.remove();
      canvas.insertAdjacentHTML('beforebegin',
        '<div class="chart-no-data text-muted small text-center mt-3 mb-3"><i class="fas fa-shopping-bag fa-2x opacity-25 mb-2 d-block"></i>No orders in this period.</div>');
    }
    return;
  }
  
  mkChart('slrChartOrders', {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Orders',
        data: counts,
        backgroundColor: 'rgba(99,102,241,.75)',
        borderColor: SLR_COLORS.indigo,
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: { grid: { color: gridColor }, ticks: { stepSize: 1 } },
      },
    },
  });
}

/* ── Order Status Doughnut ─────────────────────────────────────────────── */
function renderStatus(dist) {
  // Empty state: no status distribution data
  const labels = Object.keys(dist || {});
  if (!labels.length) {
    const canvas = document.getElementById('slrChartStatus');
    if (canvas) {
      const prev = canvas.previousElementSibling;
      if (prev && prev.classList.contains('chart-no-data')) prev.remove();
      canvas.insertAdjacentHTML('beforebegin',
        '<div class="chart-no-data text-muted small text-center mt-3 mb-3"><i class="fas fa-chart-pie fa-2x opacity-25 mb-2 d-block"></i>No orders to show status distribution.</div>');
    }
    return;
  }
  
  const mappedLabels = labels.map(k => k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
  const data   = labels.map(k => dist[k]);
  const colors = labels.map(k => STATUS_COLORS[k] || '#9ca3af');

  mkChart('slrChartStatus', {
    type: 'doughnut',
    data: {
      labels: mappedLabels,
      datasets: [{ data, backgroundColor: colors, borderWidth: 2 }],
    },
    options: {
      responsive: true,
      cutout: '62%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { font: { size: 11, family: fontFamily }, padding: 10 },
        },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed} order${ctx.parsed !== 1 ? 's' : ''}`,
          },
        },
      },
    },
  });
}

/* ── Top 5 Products ────────────────────────────────────────────────────── */
function renderTopProducts(products) {
  if (!products.length) {
    const canvas = document.getElementById('slrChartTopProducts');
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#9ca3af';
      ctx.font = '14px ' + fontFamily;
      ctx.textAlign = 'center';
      ctx.fillText('No sales data yet', canvas.width / 2, canvas.height / 2);
    }
    return;
  }

  const labels   = products.map(p => p.name);
  const revenues = products.map(p => p.revenue);
  const barColors = [
    SLR_COLORS.blue, SLR_COLORS.indigo, SLR_COLORS.cyan,
    SLR_COLORS.green, SLR_COLORS.purple,
  ];

  mkChart('slrChartTopProducts', {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Revenue',
        data: revenues,
        backgroundColor: barColors.slice(0, products.length),
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` Revenue: ${peso(ctx.parsed.x)} · Qty: ${products[ctx.dataIndex].qty || 0}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: gridColor },
          ticks: { callback: v => '\u20b1' + Number(v).toLocaleString('en-PH') },
        },
        y: {
          grid: { display: false },
          ticks: {
            font: { size: 12, family: fontFamily },
            callback: function(val, idx) {
              const lbl = this.getLabelForValue(val);
              return lbl.length > 22 ? lbl.slice(0, 21) + '…' : lbl;
            },
          },
        },
      },
    },
  });
}
