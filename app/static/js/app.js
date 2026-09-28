/**
 * Chespin Local Web Dashboard - Kiosk Frontend Controller
 */

// Global Chart Instances
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

    // Active Month Label (always current month based on system date)
    const activeMonthElem = document.getElementById('metric-active-month');
    if (activeMonthElem) {
      const now = new Date();
      activeMonthElem.textContent = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    }

    // Remaining Budget & Color Indicator
    const remainingElem = document.getElementById('metric-remaining-budget');
    if (remainingElem) remainingElem.textContent = formatCurrency(data.remaining_budget);

    const daysLeftElem = document.getElementById('metric-days-left');
    if (daysLeftElem) daysLeftElem.textContent = `${data.days_left_in_month} days left`;

    // Calculate remaining percentage
    const monthlyBudget = Number(data.monthly_budget) || 1;
    const remainingBudget = Number(data.remaining_budget) || 0;
    const remainingPercent = Math.max(0, Math.min(100, Math.round((remainingBudget / monthlyBudget) * 100)));

    const remainingPercentElem = document.getElementById('metric-remaining-percent');
    if (remainingPercentElem) remainingPercentElem.textContent = `${remainingPercent}%`;

    const remainingBadge = document.getElementById('remaining-status-badge');
    const remainingDot = document.getElementById('remaining-status-dot');
    const remainingBar = document.getElementById('remaining-color-bar');

    if (remainingBar) {
      remainingBar.style.width = `${remainingPercent}%`;
    }

    // Color Indicator States:
    // 100% - 80%  -> Green
    // > 80% - 50% -> Yellow
    // > 50% - 20% -> Orange
    // < 20%       -> Red
    if (remainingPercent >= 80) {
      // Green
      if (remainingBadge) {
        remainingBadge.className = "inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30";
      }
      if (remainingDot) {
        remainingDot.className = "w-2 h-2 rounded-full bg-emerald-400";
      }
      if (remainingBar) {
        remainingBar.className = "progress-bar-fill h-full bg-emerald-500 rounded-full";
      }
      if (remainingElem) {
        remainingElem.className = "text-3xl sm:text-4xl font-bold font-mono tracking-tight text-emerald-400";
      }
    } else if (remainingPercent >= 50) {
      // Yellow
      if (remainingBadge) {
        remainingBadge.className = "inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-yellow-500/10 text-yellow-400 border border-yellow-500/30";
      }
      if (remainingDot) {
        remainingDot.className = "w-2 h-2 rounded-full bg-yellow-400";
      }
      if (remainingBar) {
        remainingBar.className = "progress-bar-fill h-full bg-yellow-400 rounded-full";
      }
      if (remainingElem) {
        remainingElem.className = "text-3xl sm:text-4xl font-bold font-mono tracking-tight text-yellow-400";
      }
    } else if (remainingPercent >= 20) {
      // Orange
      if (remainingBadge) {
        remainingBadge.className = "inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-500/10 text-orange-400 border border-orange-500/30";
      }
      if (remainingDot) {
        remainingDot.className = "w-2 h-2 rounded-full bg-orange-400";
      }
      if (remainingBar) {
        remainingBar.className = "progress-bar-fill h-full bg-orange-400 rounded-full";
      }
      if (remainingElem) {
        remainingElem.className = "text-3xl sm:text-4xl font-bold font-mono tracking-tight text-orange-400";
      }
    } else {
      // Red (< 20%)
      if (remainingBadge) {
        remainingBadge.className = "inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30";
      }
      if (remainingDot) {
        remainingDot.className = "w-2 h-2 rounded-full bg-rose-400 animate-pulse";
      }
      if (remainingBar) {
        remainingBar.className = "progress-bar-fill h-full bg-rose-500 rounded-full";
      }
      if (remainingElem) {
        remainingElem.className = "text-3xl sm:text-4xl font-bold font-mono tracking-tight text-rose-400";
      }
    }

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

// Fetch and Render Monthly Expense Breakdown
async function fetchCategories() {
  const categoryList = document.getElementById('category-progress-list');
  const ctx = document.getElementById('categoriesChart')?.getContext('2d');
  if (!categoryList && !ctx) return;

  try {
    let res = await fetch('/api/v1/expenses/monthly');
    if (!res.ok) {
      res = await fetch('/api/v1/expenses/categories');
    }
    if (!res.ok) throw new Error('Failed to fetch monthly expenses');
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


// Fetch and Render Recent Transactions
async function fetchTransactions() {
  const container = document.getElementById('recent-transactions-list');
  if (!container) return;

  try {
    const res = await fetch('/api/v1/transactions/recent');
    if (!res.ok) throw new Error('Failed to fetch transactions');
    const transactions = await res.json();


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

  // Use allSettled so one failing endpoint never blocks other dashboard sections
  await Promise.allSettled([
    fetchSummary(),
    fetchCategories(),
    fetchTransactions(),
    fetchSystemStatus()
  ]);

  if (refreshBtn) {
    setTimeout(() => refreshBtn.classList.remove('animate-spin'), 600);
  }
}

// App Initialization
function initDashboard() {
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

  // Setup CRUD Management Modal
  setupCrudModal();

  // Initialize Lucide Icons
  if (window.lucide) {
    lucide.createIcons();
  }
}

// ===================================================
// CRUD Management Modal Controller
// ===================================================

let allLoadedExpenses = [];

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const isErr = type === 'error';
  toast.className = `px-4 py-3 rounded-xl border text-xs font-semibold shadow-xl flex items-center space-x-2 transition-all transform duration-300 pointer-events-auto ${
    isErr
      ? 'bg-rose-950/90 text-rose-300 border-rose-500/50'
      : 'bg-emerald-950/90 text-emerald-300 border-emerald-500/50'
  }`;
  toast.innerHTML = `
    <i data-lucide="${isErr ? 'alert-circle' : 'check-circle'}" class="w-4 h-4 flex-shrink-0"></i>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  if (window.lucide) lucide.createIcons();

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function setupCrudModal() {
  const modal = document.getElementById('crud-modal');
  const openBtn = document.getElementById('open-crud-modal-btn');
  const closeBtn = document.getElementById('close-crud-modal-btn');
  const closeFooterBtn = document.getElementById('close-crud-modal-footer-btn');

  const tabBtnSummaries = document.getElementById('tab-btn-summaries');
  const tabBtnExpenses = document.getElementById('tab-btn-expenses');
  const tabContentSummaries = document.getElementById('tab-content-summaries');
  const tabContentExpenses = document.getElementById('tab-content-expenses');

  if (!modal || !openBtn) return;

  // Open Modal
  openBtn.addEventListener('click', () => {
    modal.classList.remove('hidden');
    loadMetricSummaries();
    loadMonthlyExpenses();
  });

  // Close Modal
  const closeModal = () => modal.classList.add('hidden');
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (closeFooterBtn) closeFooterBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  // Tab Switching
  if (tabBtnSummaries && tabBtnExpenses) {
    tabBtnSummaries.addEventListener('click', () => {
      tabBtnSummaries.className = 'px-4 py-2 text-xs sm:text-sm font-semibold border-b-2 border-emerald-400 text-emerald-400 transition flex items-center space-x-2';
      tabBtnExpenses.className = 'px-4 py-2 text-xs sm:text-sm font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition flex items-center space-x-2';
      tabContentSummaries?.classList.remove('hidden');
      tabContentExpenses?.classList.add('hidden');
    });

    tabBtnExpenses.addEventListener('click', () => {
      tabBtnExpenses.className = 'px-4 py-2 text-xs sm:text-sm font-semibold border-b-2 border-emerald-400 text-emerald-400 transition flex items-center space-x-2';
      tabBtnSummaries.className = 'px-4 py-2 text-xs sm:text-sm font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition flex items-center space-x-2';
      tabContentExpenses?.classList.remove('hidden');
      tabContentSummaries?.classList.add('hidden');
    });
  }

  // Preload Checkbox Toggle
  const preloadCheckbox = document.getElementById('checkbox-preload-expenses');
  const preloadPicker = document.getElementById('preload-month-picker');
  if (preloadCheckbox && preloadPicker) {
    preloadCheckbox.addEventListener('change', () => {
      if (preloadCheckbox.checked) {
        preloadPicker.classList.remove('hidden');
        const now = new Date();
        const curMonthStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
        const inputPreload = document.getElementById('input-preload-month');
        if (inputPreload && !inputPreload.value) {
          inputPreload.value = curMonthStr;
        }
      } else {
        preloadPicker.classList.add('hidden');
      }
    });
  }

  // Summary Form Open/Close/Save
  const btnOpenSummaryForm = document.getElementById('btn-open-summary-form');
  const summaryFormContainer = document.getElementById('summary-form-container');
  const btnCloseSummaryForm = document.getElementById('btn-close-summary-form');
  const btnCancelSummary = document.getElementById('btn-cancel-summary');
  const btnSaveSummary = document.getElementById('btn-save-summary');

  const hideSummaryForm = () => {
    summaryFormContainer?.classList.add('hidden');
    const errBanner = document.getElementById('summary-error-banner');
    if (errBanner) errBanner.classList.add('hidden');
  };

  if (btnOpenSummaryForm && summaryFormContainer) {
    btnOpenSummaryForm.addEventListener('click', () => {
      document.getElementById('input-summary-id').value = '';
      document.getElementById('summary-form-title').innerHTML = '<i data-lucide="calendar-plus" class="w-4 h-4 text-emerald-400"></i><span>New Monthly Budget</span>';
      
      const now = new Date();
      // Default to next month for new budget
      const nextM = new Date(now.getFullYear(), now.getMonth() + 1, 1);
      const nextMStr = `${nextM.getFullYear()}-${String(nextM.getMonth() + 1).padStart(2, '0')}`;
      
      const monthInput = document.getElementById('input-summary-month');
      if (monthInput) monthInput.value = nextMStr;
      
      const budgetInput = document.getElementById('input-summary-budget');
      if (budgetInput) budgetInput.value = '3500.00';
      
      const savingsInput = document.getElementById('input-summary-savings');
      if (savingsInput) savingsInput.value = '800.00';

      const preloadCb = document.getElementById('checkbox-preload-expenses');
      if (preloadCb) {
        preloadCb.checked = false;
        document.getElementById('preload-month-picker')?.classList.add('hidden');
      }

      const errBanner = document.getElementById('summary-error-banner');
      if (errBanner) errBanner.classList.add('hidden');

      summaryFormContainer.classList.remove('hidden');
      if (window.lucide) lucide.createIcons();
    });
  }

  if (btnCloseSummaryForm) btnCloseSummaryForm.addEventListener('click', hideSummaryForm);
  if (btnCancelSummary) btnCancelSummary.addEventListener('click', hideSummaryForm);
  if (btnSaveSummary) btnSaveSummary.addEventListener('click', saveMetricSummary);

  // Expense Form Open/Close/Save
  const btnOpenExpenseForm = document.getElementById('btn-open-expense-form');
  const expenseFormContainer = document.getElementById('expense-form-container');
  const btnCloseExpenseForm = document.getElementById('btn-close-expense-form');
  const btnCancelExpense = document.getElementById('btn-cancel-expense');
  const btnSaveExpense = document.getElementById('btn-save-expense');

  const hideExpenseForm = () => expenseFormContainer?.classList.add('hidden');

  if (btnOpenExpenseForm && expenseFormContainer) {
    btnOpenExpenseForm.addEventListener('click', () => {
      document.getElementById('input-expense-id').value = '';
      document.getElementById('expense-form-title').innerHTML = '<i data-lucide="receipt" class="w-4 h-4 text-emerald-400"></i><span>Add Monthly Expense</span>';
      
      document.getElementById('input-expense-name').value = '';
      document.getElementById('input-expense-budget').value = '200.00';
      document.getElementById('input-expense-amount').value = '0.00';
      
      const now = new Date();
      const todayStr = now.toISOString().slice(0, 10);
      document.getElementById('input-expense-date').value = todayStr;
      
      document.getElementById('input-expense-color').value = '#6A8D73';
      document.getElementById('input-expense-color-hex').textContent = '#6A8D73';
      document.getElementById('input-expense-icon').value = 'credit-card';

      expenseFormContainer.classList.remove('hidden');
      if (window.lucide) lucide.createIcons();
    });
  }

  if (btnCloseExpenseForm) btnCloseExpenseForm.addEventListener('click', hideExpenseForm);
  if (btnCancelExpense) btnCancelExpense.addEventListener('click', hideExpenseForm);
  if (btnSaveExpense) btnSaveExpense.addEventListener('click', saveMonthlyExpense);

  // Color picker sync
  const colorInput = document.getElementById('input-expense-color');
  const colorHex = document.getElementById('input-expense-color-hex');
  if (colorInput && colorHex) {
    colorInput.addEventListener('input', () => {
      colorHex.textContent = colorInput.value;
    });
  }

  // Month filter for expenses
  const filterSelect = document.getElementById('filter-expenses-month-select');
  if (filterSelect) {
    filterSelect.addEventListener('change', () => {
      loadMonthlyExpenses(filterSelect.value);
    });
  }
}

// Fetch and Render Summaries List
async function loadMetricSummaries() {
  const container = document.getElementById('summaries-list-container');
  if (!container) return;

  try {
    const res = await fetch('/api/v1/metric-summary');
    if (!res.ok) throw new Error('Failed to fetch metric summaries');
    const summaries = await res.json();

    if (!summaries.length) {
      container.innerHTML = '<div class="text-center py-6 text-slate-500 text-xs">No monthly budgets found. Click "New Monthly Budget" to create one.</div>';
      return;
    }

    container.innerHTML = summaries.map(s => {
      const monthStr = s.running_month ? s.running_month.slice(0, 7) : 'Unknown';
      let dateLabel = monthStr;
      try {
        const [yr, mo] = monthStr.split('-');
        const dt = new Date(parseInt(yr), parseInt(mo) - 1, 1);
        dateLabel = dt.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
      } catch (e) {}

      return `
        <div class="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition">
          <div>
            <div class="flex items-center space-x-2">
              <span class="text-sm font-bold text-white tracking-tight">${dateLabel}</span>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">${monthStr}</span>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                s.spending_status === 'on_track' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30' :
                s.spending_status === 'warning' ? 'bg-amber-950 text-amber-400 border border-amber-500/30' :
                'bg-rose-950 text-rose-400 border border-rose-500/30'
              }">${s.spending_status}</span>
            </div>
            <div class="flex items-center space-x-3 text-xs text-slate-400 mt-1 font-mono">
              <span>Budget: <strong class="text-white">${formatCurrency(s.monthly_budget)}</strong></span>
              <span>•</span>
              <span>Spent: <strong class="text-emerald-400">${formatCurrency(s.total_spent)}</strong></span>
              <span>•</span>
              <span>Remaining: <strong class="text-slate-200">${formatCurrency(s.remaining_budget)}</strong></span>
            </div>
          </div>
          <div class="flex items-center space-x-2 self-end sm:self-auto">
            <button onclick="editMetricSummary(${s.id}, '${monthStr}', ${s.monthly_budget}, ${s.savings_target})"
              class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs flex items-center space-x-1 transition">
              <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
              <span>Edit</span>
            </button>
            <button onclick="deleteMetricSummary(${s.id}, '${dateLabel}')"
              class="px-2.5 py-1 rounded bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-xs flex items-center space-x-1 border border-rose-800/40 transition">
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
              <span>Delete</span>
            </button>
          </div>
        </div>
      `;
    }).join('');

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Error loading summaries:', err);
    container.innerHTML = `<div class="text-center py-6 text-rose-400 text-xs">${err.message}</div>`;
  }
}

// Edit Summary Handler
window.editMetricSummary = function(id, monthStr, budget, savings) {
  const container = document.getElementById('summary-form-container');
  if (!container) return;

  document.getElementById('input-summary-id').value = id;
  document.getElementById('summary-form-title').innerHTML = '<i data-lucide="edit" class="w-4 h-4 text-emerald-400"></i><span>Edit Monthly Budget</span>';
  document.getElementById('input-summary-month').value = monthStr;
  document.getElementById('input-summary-budget').value = budget;
  document.getElementById('input-summary-savings').value = savings;

  const preloadCb = document.getElementById('checkbox-preload-expenses');
  if (preloadCb) {
    preloadCb.checked = false;
    document.getElementById('preload-month-picker')?.classList.add('hidden');
  }

  const errBanner = document.getElementById('summary-error-banner');
  if (errBanner) errBanner.classList.add('hidden');

  container.classList.remove('hidden');
  container.scrollIntoView({ behavior: 'smooth' });
  if (window.lucide) lucide.createIcons();
};

// Delete Summary Handler
window.deleteMetricSummary = async function(id, dateLabel) {
  if (!confirm(`Are you sure you want to delete the budget for ${dateLabel}?`)) return;

  try {
    const res = await fetch(`/api/v1/metric-summary/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to delete summary');
    }
    showToast(`Budget for ${dateLabel} deleted successfully.`);
    loadMetricSummaries();
    refreshDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

// Save Summary (Create / Update with Pre-load support)
async function saveMetricSummary() {
  const id = document.getElementById('input-summary-id').value;
  const monthVal = document.getElementById('input-summary-month').value;
  const budgetVal = parseFloat(document.getElementById('input-summary-budget').value);
  const savingsVal = parseFloat(document.getElementById('input-summary-savings').value) || 0;

  const errBanner = document.getElementById('summary-error-banner');
  const errText = document.getElementById('summary-error-text');
  if (errBanner) errBanner.classList.add('hidden');

  if (!monthVal) {
    alert('Please choose a target month.');
    return;
  }
  if (isNaN(budgetVal) || budgetVal <= 0) {
    alert('Please enter a valid monthly budget amount.');
    return;
  }

  const preloadCb = document.getElementById('checkbox-preload-expenses');
  let preloadMonth = null;
  if (preloadCb && preloadCb.checked) {
    preloadMonth = document.getElementById('input-preload-month').value;
    if (!preloadMonth) {
      alert('Please select a month to pre-load expenses from, or uncheck the option.');
      return;
    }
  }

  const formattedRunningMonth = `${monthVal}-01 00:00:00`;
  const isUpdate = Boolean(id);

  try {
    let res;
    if (isUpdate) {
      res = await fetch(`/api/v1/metric-summary/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          monthly_budget: budgetVal,
          savings_target: savingsVal,
          running_month: formattedRunningMonth,
          preload_from_month: preloadMonth,
        }),
      });
    } else {
      res = await fetch('/api/v1/metric-summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          monthly_budget: budgetVal,
          savings_target: savingsVal,
          running_month: formattedRunningMonth,
          preload_from_month: preloadMonth,
        }),
      });
    }

    if (!res.ok) {
      const err = await res.json();
      const message = err.detail || 'Failed to save monthly budget';
      
      // Prominently display error banner in form
      if (errBanner && errText) {
        errText.textContent = message;
        errBanner.classList.remove('hidden');
        if (window.lucide) lucide.createIcons();
      }
      showToast(message, 'error');
      return;
    }

    showToast(`Monthly budget for ${monthVal} saved successfully!`);
    document.getElementById('summary-form-container')?.classList.add('hidden');
    loadMetricSummaries();
    loadMonthlyExpenses();
    refreshDashboard();
  } catch (err) {
    console.error('Error saving summary:', err);
    if (errBanner && errText) {
      errText.textContent = err.message;
      errBanner.classList.remove('hidden');
    }
    showToast(err.message, 'error');
  }
}

// Fetch and Render Expenses List
async function loadMonthlyExpenses(filterMonth = '') {
  const container = document.getElementById('expenses-list-container');
  const filterSelect = document.getElementById('filter-expenses-month-select');
  if (!container) return;

  try {
    let url = '/api/v1/expenses/monthly';
    if (filterMonth) {
      const [y, m] = filterMonth.split('-');
      url += `?month=${m}&year=${y}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch expenses');
    const expenses = await res.json();
    allLoadedExpenses = expenses;

    // Populate filter options if not yet populated
    if (filterSelect && filterSelect.options.length <= 1) {
      const monthsSet = new Set();
      expenses.forEach(e => {
        if (e.expense_date && e.expense_date.length >= 7) {
          monthsSet.add(e.expense_date.slice(0, 7));
        }
      });
      const sortedMonths = Array.from(monthsSet).sort().reverse();
      sortedMonths.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = m;
        filterSelect.appendChild(opt);
      });
    }

    if (!expenses.length) {
      container.innerHTML = '<div class="text-center py-6 text-slate-500 text-xs">No expenses found for this selection.</div>';
      return;
    }

    container.innerHTML = expenses.map(exp => `
      <div class="p-3 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center text-white" style="background-color: ${exp.color || '#6A8D73'}">
            <i data-lucide="${exp.icon || 'credit-card'}" class="w-4 h-4"></i>
          </div>
          <div>
            <div class="text-sm font-semibold text-white tracking-tight">${exp.name}</div>
            <div class="flex items-center space-x-2 text-xs text-slate-400 font-mono mt-0.5">
              <span>Date: ${exp.expense_date ? exp.expense_date.slice(0, 10) : 'N/A'}</span>
              <span>•</span>
              <span class="text-slate-300">${exp.percentage || 0}% of spend</span>
            </div>
          </div>
        </div>

        <div class="flex items-center space-x-4 self-end sm:self-auto font-mono">
          <div class="text-right">
            <div class="text-sm font-bold text-white">${formatCurrency(exp.amount)}</div>
            <div class="text-[11px] text-slate-500">of ${formatCurrency(exp.budget)} cap</div>
          </div>
          <div class="flex items-center space-x-1.5 pl-2 border-l border-slate-800">
            <button onclick="editMonthlyExpense(${exp.id})"
              class="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition" title="Edit">
              <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
            </button>
            <button onclick="deleteMonthlyExpense(${exp.id}, '${exp.name.replace(/'/g, "\\'")}')"
              class="p-1.5 rounded hover:bg-rose-950/50 text-rose-400 transition" title="Delete">
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
          </div>
        </div>
      </div>
    `).join('');

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Error loading expenses:', err);
    container.innerHTML = `<div class="text-center py-6 text-rose-400 text-xs">${err.message}</div>`;
  }
}

// Edit Monthly Expense
window.editMonthlyExpense = function(id) {
  const exp = allLoadedExpenses.find(e => e.id === id);
  if (!exp) return;

  const container = document.getElementById('expense-form-container');
  if (!container) return;

  document.getElementById('input-expense-id').value = exp.id;
  document.getElementById('expense-form-title').innerHTML = '<i data-lucide="edit" class="w-4 h-4 text-emerald-400"></i><span>Edit Expense</span>';
  document.getElementById('input-expense-name').value = exp.name;
  document.getElementById('input-expense-budget').value = exp.budget;
  document.getElementById('input-expense-amount').value = exp.amount;
  document.getElementById('input-expense-date').value = exp.expense_date ? exp.expense_date.slice(0, 10) : '';
  document.getElementById('input-expense-color').value = exp.color || '#6A8D73';
  document.getElementById('input-expense-color-hex').textContent = exp.color || '#6A8D73';
  document.getElementById('input-expense-icon').value = exp.icon || 'credit-card';

  container.classList.remove('hidden');
  container.scrollIntoView({ behavior: 'smooth' });
  if (window.lucide) lucide.createIcons();
};

// Delete Monthly Expense
window.deleteMonthlyExpense = async function(id, name) {
  if (!confirm(`Are you sure you want to delete expense "${name}"?`)) return;

  try {
    const res = await fetch(`/api/v1/expenses/monthly/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to delete expense');
    }
    showToast(`Expense "${name}" deleted.`);
    const filterSelect = document.getElementById('filter-expenses-month-select');
    loadMonthlyExpenses(filterSelect ? filterSelect.value : '');
    refreshDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

// Save Monthly Expense
async function saveMonthlyExpense() {
  const id = document.getElementById('input-expense-id').value;
  const name = document.getElementById('input-expense-name').value.trim();
  const budget = parseFloat(document.getElementById('input-expense-budget').value);
  const amount = parseFloat(document.getElementById('input-expense-amount').value) || 0;
  const date = document.getElementById('input-expense-date').value;
  const color = document.getElementById('input-expense-color').value;
  const icon = document.getElementById('input-expense-icon').value;

  if (!name) {
    alert('Please enter an expense name.');
    return;
  }
  if (isNaN(budget) || budget < 0) {
    alert('Please enter a valid budget amount.');
    return;
  }

  const isUpdate = Boolean(id);
  const payload = {
    name,
    budget,
    amount,
    expense_date: date || null,
    color,
    icon,
  };

  try {
    let res;
    if (isUpdate) {
      res = await fetch(`/api/v1/expenses/monthly/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } else {
      res = await fetch('/api/v1/expenses/monthly', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    }

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to save expense');
    }

    showToast(`Expense "${name}" saved!`);
    document.getElementById('expense-form-container')?.classList.add('hidden');
    const filterSelect = document.getElementById('filter-expenses-month-select');
    loadMonthlyExpenses(filterSelect ? filterSelect.value : '');
    refreshDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
}


// Ensure init executes even if script loads after DOMContentLoaded fired
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDashboard);
} else {
  initDashboard();
}

