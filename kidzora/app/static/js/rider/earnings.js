/**
 * KidZora – Rider / Earnings Page
 */

document.addEventListener('DOMContentLoaded', function () {
  initFilterControls();

  const dataEl = document.getElementById('kz-rider-earnings-data');
  const canvas = document.getElementById('riderEarningsChart');
  if (!dataEl || !canvas || typeof Chart === 'undefined') return;

  let chartData = null;
  try {
    chartData = JSON.parse(dataEl.textContent || '{}');
  } catch (_) {
    chartData = null;
  }

  if (!chartData || !Array.isArray(chartData.labels) || !chartData.has_data) return;

  const peso = function (value) {
    return '\u20b1' + Number(value || 0).toLocaleString('en-PH', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: chartData.labels,
      datasets: [
        {
          label: 'Daily Earnings',
          data: chartData.earnings || [],
          borderColor: '#198754',
          backgroundColor: 'rgba(25, 135, 84, .14)',
          fill: true,
          pointRadius: 3,
          pointHoverRadius: 5,
          pointBackgroundColor: '#198754',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          tension: 0.35,
          yAxisID: 'y',
        },
        {
          label: 'Completed Deliveries',
          data: chartData.counts || [],
          borderColor: '#0f766e',
          backgroundColor: 'rgba(15, 118, 110, .08)',
          fill: false,
          pointRadius: 2,
          pointHoverRadius: 4,
          tension: 0.25,
          borderDash: [6, 4],
          yAxisID: 'yCount',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            usePointStyle: true,
            boxWidth: 10,
            color: '#334155',
          },
        },
        tooltip: {
          callbacks: {
            label: function (ctx) {
              if (ctx.dataset.yAxisID === 'y') return ' ' + ctx.dataset.label + ': ' + peso(ctx.parsed.y);
              return ' ' + ctx.dataset.label + ': ' + ctx.parsed.y;
            },
          },
        },
      },
      scales: {
        x: {
          grid: {
            display: false,
          },
          ticks: {
            maxRotation: 0,
            color: '#64748b',
          },
        },
        y: {
          beginAtZero: true,
          grid: {
            color: 'rgba(148, 163, 184, .18)',
          },
          ticks: {
            color: '#64748b',
            callback: function (value) {
              return value === 0 ? peso(0) : '\u20b1' + Number(value).toLocaleString('en-PH');
            },
          },
        },
        yCount: {
          beginAtZero: true,
          position: 'right',
          grid: {
            drawOnChartArea: false,
          },
          ticks: {
            precision: 0,
            color: '#64748b',
            stepSize: 1,
          },
        },
      },
    },
  });
});

function initFilterControls() {
  const form = document.getElementById('riderEarningsFilterForm');
  const periodInput = document.getElementById('rePeriodInput');
  const customRow = document.getElementById('reCustomRow');
  const startInput = document.getElementById('reStartDateInput');
  const endInput = document.getElementById('reEndDateInput');
  const tabsRoot = document.getElementById('rePeriodTabs');
  if (!form || !periodInput || !customRow || !tabsRoot) return;

  const setActivePeriod = function (period) {
    tabsRoot.querySelectorAll('button[data-period]').forEach(function (button) {
      const isActive = button.dataset.period === period;
      button.classList.toggle('btn-success', isActive);
      button.classList.toggle('btn-outline-success', !isActive);
    });
    customRow.classList.toggle('d-none', period !== 'custom');
  };

  tabsRoot.querySelectorAll('button[data-period]').forEach(function (button) {
    button.addEventListener('click', function () {
      const period = button.dataset.period || 'monthly';
      periodInput.value = period;
      setActivePeriod(period);
      if (period !== 'custom') form.submit();
    });
  });

  form.addEventListener('submit', function (event) {
    if (periodInput.value !== 'custom') return;
    if (!startInput || !endInput || !startInput.value || !endInput.value) {
      event.preventDefault();
      return;
    }
  });

  setActivePeriod(periodInput.value || 'monthly');
}