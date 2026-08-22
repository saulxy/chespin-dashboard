/**
 * Chespin Local Web Dashboard - Kiosk Frontend Controller
 */

// Global Chart Instances
let trendsChart = null;
let categoryChart = null;
let pollTimer = null;
const REFRESH_INTERVAL_MS = (window.CHspin_CONFIG?.refreshInterval || 30) * 1000;

// Format Currency
function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

// Update Live Clock & Date
function updateClock() {
  const now = new Date();
  
  // Format Time (12-hour with AM/PM)
  const timeElem = document.getElementById('live-clock');
  const dateElem = document.getElementById('live-date');
  
  if (timeElem) {
    timeElem.textContent = now.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
  }
  
  if (dateElem) {
    dateElem.textContent = now.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }
}

// Fetch and Render Summary Metrics
async function fetchSummary() {
  try {
    const res = await fetch('/api/v1/summary');
    if (!res.ok) throw new Error('Failed to fetch summary');
    const data = await res.json();

    // Total Spent
    const totalSpentElem = document.getElementById('metric-total-spent');
    if (totalSpentElem) totalSpentElem.textContent = formatCurrency(data.total_spent);

    // Remaining Budget
    const remainingElem = document.getElementById('metric-remaining-budget');
    if (remainingElem) remainingElem.textContent = formatCurrency(data.remaining_budget);

    // Monthly Budget Total
    const budgetElem = document.getElementById('metric-monthly-budget');
    if (budgetElem) budgetElem.textContent = `of ${formatCurrency(data.monthly_budget)} limit`;

    // Savings Current & Target
    const savingsElem = document.getElementById('metric-savings-rate');
    if (savingsElem) savingsElem.textContent = `${data.savings_rate}%`;

    const savingsDetail = document.getElementById('metric-savings-detail');
    if (savingsDetail) {
      savingsDetail.textContent = `${formatCurrency(data.savings_current)} / ${formatCurrency(data.savings_target)}`;
    }

    // Daily Average
    const dailyAvgElem = document.getElementById('metric-daily-average');
    if (dailyAvgElem) dailyAvgElem.textContent = formatCurrency(data.daily_average);

    const daysLeftElem = document.getElementById('metric-days-left');
    if (daysLeftElem) daysLeftElem.textContent = `${data.days_left_in_month} days left`;

    // Overall Progress Bar
    const spentPercent = Math.min(100, Math.round((data.total_spent / data.monthly_budget) * 100));
    const budgetProgressBar = document.getElementById('overall-budget-bar');
    const budgetPercentText = document.getElementById('overall-budget-percent');
    
    if (budgetProgressBar) {
      budgetProgressBar.style.width = `${spentPercent}%`;
      if (spentPercent > 90) {
        budgetProgressBar.className = "progress-bar-fill h-full bg-rose-500 rounded-full";
      } else if (spentPercent > 75) {
        budgetProgressBar.className = "progress-bar-fill h-full bg-amber-500 rounded-full";
      } else {
        budgetProgressBar.className = "progress-bar-fill h-full bg-emerald-500 rounded-full";
      }
    }
    
    if (budgetPercentText) {
      budgetPercentText.textContent = `${spentPercent}% allocated`;
    }

    // Status Badge
    const statusPill = document.getElementById('spending-status-badge');
    if (statusPill) {
      if (data.spending_status === 'on_track') {
        statusPill.textContent = '● On Track';
        statusPill.className = 'px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-500/30';
      } else if (data.spending_status === 'warning') {
        statusPill.textContent = '● Warning';
        statusPill.className = 'px-3 py-1 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-400 border border-amber-500/30';
      } else {
        statusPill.textContent = '● Over Budget';
        statusPill.className = 'px-3 py-1 rounded-full text-xs font-semibold bg-rose-950/80 text-rose-400 border border-rose-500/30';
      }
    }
  } catch (err) {
    console.error('Error loading summary:', err);
  }
}

// Fetch and Render Category Expense Breakdown
async function fetchCategories() {
  try {
    const res = await fetch('/api/v1/expenses/categories');
    if (!res.ok) throw new Error('Failed to fetch categories');
    const categories = await res.json();

    // Render Category Progress List
    const categoryList = document.getElementById('category-progress-list');
    if (categoryList) {
      categoryList.innerHTML = categories.map(cat => {
        const percent = Math.min(100, Math.round((cat.amount / cat.budget) * 100));
        const isOver = cat.amount > cat.budget;
        const barColor = isOver ? '#F43F5E' : cat.color;

        return `
          <div class="space-y-1.5 p-2 rounded-lg bg-slate-900/40 border border-slate-800/60 hover:border-slate-700 transition">
            <div class="flex items-center justify-between text-xs sm:text-sm">
              <div class="flex items-center space-x-2">
                <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${cat.color}"></span>
                <span class="font-medium text-slate-200">${cat.name}</span>
              </div>
              <div class="flex items-center space-x-1.5 font-mono">
                <span class="text-white font-semibold">${formatCurrency(cat.amount)}</span>
                <span class="text-slate-500">/ ${formatCurrency(cat.budget)}</span>
              </div>
            </div>
            <div class="w-full bg-slate-800/80 h-2 rounded-full overflow-hidden">
              <div class="progress-bar-fill h-full rounded-full" style="width: ${percent}%; background-color: ${barColor};"></div>
            </div>
          </div>
        `;
      }).join('');
    }

    // Render Chart.js Doughnut
    const ctx = document.getElementById('categoriesChart')?.getContext('2d');
    if (ctx) {
      const labels = categories.map(c => c.name);
      const dataValues = categories.map(c => c.amount);
      const bgColors = categories.map(c => c.color);

      if (categoryChart) {
        categoryChart.data.labels = labels;
        categoryChart.data.datasets[0].data = dataValues;
        categoryChart.data.datasets[0].backgroundColor = bgColors;
        categoryChart.update();
      } else {
        categoryChart = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: labels,
            datasets: [{
              data: dataValues,
              backgroundColor: bgColors,
              borderColor: '#0f172a',
              borderWidth: 3,
              hoverOffset: 6
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '72%',
            plugins: {
              legend: {
                display: false
              },
              tooltip: {
                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                titleColor: '#f3f4f6',
                bodyColor: '#e2e8f0',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1,
                padding: 10,
                callbacks: {
                  label: function(context) {
                    return ` ${context.label}: ${formatCurrency(context.raw)}`;
                  }
                }
              }
            }
          }
        });
      }
    }
  } catch (err) {
    console.error('Error loading categories:', err);
  }
}

// Fetch and Render Trends Line Chart
async function fetchTrends() {
  try {
    const res = await fetch('/api/v1/expenses/trends');
    if (!res.ok) throw new Error('Failed to fetch trends');
    const points = await res.json();

    const ctx = document.getElementById('trendsChart')?.getContext('2d');
    if (!ctx) return;

    const labels = points.map(p => p.date);
    const spentData = points.map(p => p.spent);
    const paceData = points.map(p => p.budget_pace);

    // Gradient fill for spent curve
    const gradient = ctx.createLinearGradient(0, 0, 0, 240);
    gradient.addColorStop(0, 'rgba(106, 141, 115, 0.40)');
    gradient.addColorStop(1, 'rgba(228, 255, 225, 0.00)');

    if (trendsChart) {
      trendsChart.data.labels = labels;
      trendsChart.data.datasets[0].data = spentData;
      trendsChart.data.datasets[1].data = paceData;
      trendsChart.update();
    } else {
      trendsChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Actual Spend',
              data: spentData,
              borderColor: '#6A8D73',
              backgroundColor: gradient,
              fill: true,
              tension: 0.38,
              pointBackgroundColor: '#6A8D73',
              pointBorderColor: '#0d1511',
              pointBorderWidth: 2,
              pointRadius: 4,
              pointHoverRadius: 6,
            },
            {
              label: 'Budget Pace',
              data: paceData,
              borderColor: 'rgba(148, 163, 184, 0.45)',
              borderDash: [5, 5],
              borderWidth: 2,
              pointRadius: 0,
              fill: false,
              tension: 0.2,
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: 'index',
            intersect: false,
          },
          scales: {
            x: {
              grid: {
                color: 'rgba(255, 255, 255, 0.05)',
                drawBorder: false,
              },
              ticks: {
                color: '#94a3b8',
                font: { size: 11 },
                maxRotation: 0,
              }
            },
            y: {
              grid: {
                color: 'rgba(255, 255, 255, 0.05)',
                drawBorder: false,
              },
              ticks: {
                color: '#94a3b8',
                font: { size: 11 },
                callback: function(val) {
                  return '$' + val;
                }
              }
            }
          },
          plugins: {
            legend: {
              position: 'top',
              align: 'end',
              labels: {
                boxWidth: 12,
                boxHeight: 12,
                color: '#cbd5e1',
                font: { size: 12, family: 'system-ui' }
              }
            },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              titleColor: '#f3f4f6',
              bodyColor: '#e2e8f0',
              borderColor: 'rgba(255, 255, 255, 0.1)',
              borderWidth: 1,
              padding: 12,
              callbacks: {
                label: function(context) {
                  return ` ${context.dataset.label}: ${formatCurrency(context.raw)}`;
                }
              }
            }
          }
        }
      });
    }
  } catch (err) {
    console.error('Error loading trends:', err);
  }
}

// Fetch and Render Recent Transactions
async function fetchTransactions() {
  try {
    const res = await fetch('/api/v1/transactions/recent');
    if (!res.ok) throw new Error('Failed to fetch transactions');
    const transactions = await res.json();

    const container = document.getElementById('recent-transactions-list');
    if (!container) return;

    container.innerHTML = transactions.map(tx => `
      <div class="flex items-center justify-between p-3 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition duration-200">
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <i data-lucide="${tx.icon || 'credit-card'}" class="w-4 h-4"></i>
          </div>
          <div>
            <div class="font-medium text-slate-100 text-sm">${tx.title}</div>
            <div class="text-xs text-slate-400 flex items-center space-x-2">
              <span>${tx.category}</span>
              <span>•</span>
              <span>${tx.date}</span>
            </div>
          </div>
        </div>
        <div class="text-right">
          <div class="font-mono font-semibold text-sm text-slate-100">-${formatCurrency(tx.amount)}</div>
          <div class="text-xs text-slate-500">${tx.payment_method}</div>
        </div>
      </div>
    `).join('');

    // Re-initialize Lucide icons for dynamically added items
    if (window.lucide) {
      lucide.createIcons();
    }
  } catch (err) {
    console.error('Error loading transactions:', err);
  }
}

// Fetch System Health Status
async function fetchSystemStatus() {
  try {
    const res = await fetch('/api/v1/system/status');
    if (!res.ok) throw new Error('Failed to fetch system status');
    const status = await res.json();

    const deviceElem = document.getElementById('sys-device-name');
    const uptimeElem = document.getElementById('sys-uptime');
    const syncElem = document.getElementById('sys-last-sync');

    if (deviceElem) deviceElem.textContent = status.device_name;
    if (uptimeElem) uptimeElem.textContent = `Uptime: ${status.uptime}`;
    if (syncElem) syncElem.textContent = `Synced: ${status.last_sync}`;
  } catch (err) {
    console.error('Error loading system status:', err);
  }
}

// Fullscreen Kiosk Mode Toggle
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(err => {
      console.warn(`Fullscreen request error: ${err.message}`);
    });
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    }
  }
}

// Refresh all dashboard sections
async function refreshDashboard() {
  const refreshBtn = document.getElementById('manual-refresh-btn');
  if (refreshBtn) refreshBtn.classList.add('animate-spin');

  await Promise.all([
    fetchSummary(),
    fetchCategories(),
    fetchTrends(),
    fetchTransactions(),
    fetchSystemStatus()
  ]);

  if (refreshBtn) {
    setTimeout(() => refreshBtn.classList.remove('animate-spin'), 600);
  }
}

// Initialize on DOM Loaded
document.addEventListener('DOMContentLoaded', () => {
  // Start clock
  updateClock();
  setInterval(updateClock, 1000);

  // Initial load
  refreshDashboard();

  // Polling loop for kiosk live data
  pollTimer = setInterval(refreshDashboard, REFRESH_INTERVAL_MS);

  // Setup Fullscreen Button
  const fsBtn = document.getElementById('fullscreen-toggle-btn');
  if (fsBtn) {
    fsBtn.addEventListener('click', toggleFullscreen);
  }

  // Setup Manual Refresh Button
  const refreshBtn = document.getElementById('manual-refresh-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', refreshDashboard);
  }

  // Initialize Lucide Icons
  if (window.lucide) {
    lucide.createIcons();
  }
});
