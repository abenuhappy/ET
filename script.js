/**
 * Expense Tracker Frontend Logic
 */

// State
let currentDate = new Date();
let expenses = []; // Will hold the data fetched from API

document.addEventListener('DOMContentLoaded', () => {
    init();
});

function init() {
    console.log("Expense Tracker Initializing...");

    // Check if API_URL is set
    if (typeof API_URL !== 'undefined' && API_URL.includes("https://script.google.com")) {
        loadData();
    } else {
        console.warn("API_URL not set yet. Waiting for configuration.");
        // alert("프로젝트 설정이 필요합니다. API.js 파일에 Web App URL을 입력해주세요.");
    }

    setupEventListeners();
    renderCalendar();
}

function setupEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            switchTab(e.target.dataset.tab);
        });
    });

    // Month Selector
    document.getElementById('prevMonth').addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar();
    });

    document.getElementById('nextMonth').addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar();
    });

    // Modals
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').classList.add('hidden');
        });
    });

    // FAB Removed
}

function switchTab(tabId) {
    // Update Nav
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });

    // Update View
    document.querySelectorAll('.view').forEach(view => {
        view.classList.toggle('active', view.id === tabId);
        view.classList.toggle('hidden', view.id !== tabId);
    });
}

async function loadData() {
    // Show loading?
    console.log("Fetching data...");

    try {
        expenses = await api.getExpenses();
        console.log("Loaded expenses:", expenses);

        if (expenses.length > 0) {
            // Sort by date desc
            expenses.sort((a, b) => new Date(b.date) - new Date(a.date));
            // Jump to the month of the most recent expense
            currentDate = new Date(expenses[0].date);
        } else {
            alert("불러온 데이터가 없습니다.");
        }

        renderCalendar();
        renderVendors();
        renderStats();
    } catch (e) {
        console.error(e);
        alert("데이터를 불러오는데 실패했습니다: " + e.message);
    }
}

function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    // Update Header Label
    document.getElementById('currentMonthLabel').textContent = `${year}. ${(month + 1).toString().padStart(2, '0')}`;

    const grid = document.getElementById('calendarGrid');
    grid.innerHTML = '';

    // Calendar Building Logic
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    // Empty cells for previous month
    for (let i = 0; i < firstDay.getDay(); i++) {
        const cell = document.createElement('div');
        cell.className = 'day-cell other-month';
        grid.appendChild(cell);
    }

    // Days
    for (let d = 1; d <= lastDay.getDate(); d++) {
        const cell = document.createElement('div');
        cell.className = 'day-cell';
        cell.innerHTML = `<span class="day-num">${d}</span>`;

        // Calculate daily total
        const dailyExpenses = expenses.filter(e => {
            const eDate = new Date(e.date);
            return eDate.getFullYear() === year && eDate.getMonth() === month && eDate.getDate() === d;
        });

        const dailyTotal = dailyExpenses.reduce((sum, e) => sum + Number(e.amount), 0);

        if (dailyTotal > 0) {
            const totalEl = document.createElement('div');
            totalEl.className = 'day-expense';
            totalEl.textContent = formatCurrency(dailyTotal);
            cell.appendChild(totalEl);
        }

        // Check if today
        const now = new Date();
        if (year === now.getFullYear() && month === now.getMonth() && d === now.getDate()) {
            cell.classList.add('today');
        }

        cell.addEventListener('click', () => {
            openDayModal(new Date(year, month, d));
        });

        grid.appendChild(cell);
    }

    // Monthly Total
    const monthlyTotal = expenses.filter(e => {
        const eDate = new Date(e.date);
        return eDate.getFullYear() === year && eDate.getMonth() === month;
    }).reduce((sum, e) => sum + Number(e.amount), 0);

    document.getElementById('monthlyTotal').textContent = formatCurrency(monthlyTotal);
}

function openDayModal(date) {
    const modal = document.getElementById('dayModal');
    const dateStr = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
    document.getElementById('dayModalDate').textContent = dateStr;

    // Filter expenses for this day (Using consistent Date comparison)
    const dailyExpenses = expenses.filter(e => {
        const eDate = new Date(e.date);
        return eDate.getFullYear() === date.getFullYear() &&
            eDate.getMonth() === date.getMonth() &&
            eDate.getDate() === date.getDate();
    });

    const list = document.getElementById('dayExpenseList');
    list.innerHTML = '';

    if (dailyExpenses.length === 0) {
        list.innerHTML = `<li style="text-align: center; color: #888; padding: 1rem;">데이터 없음</li>`;
    } else {
        dailyExpenses.forEach(exp => {
            const li = document.createElement('li');
            li.className = 'expense-item';
            li.innerHTML = `
                <div class="item-info">
                    <span class="item-vendor">${exp.vendor}</span>
                    <span class="item-desc">${exp.category} | ${exp.content}</span>
                </div>
                <div class="item-right">
                    <span class="item-amount">${formatCurrency(exp.amount)}</span>
                </div>
            `;
            list.appendChild(li);
        });
    }

    modal.classList.remove('hidden');
}

function openFormModal(defaultDate = null, expenseId = null) {
    const modal = document.getElementById('formModal');
    const form = document.getElementById('expenseForm');

    // Reset form
    form.reset();
    document.getElementById('expenseId').value = '';
    document.getElementById('formModalTitle').textContent = '지출 추가';

    if (expenseId) {
        // Edit Mode
        // Use loose equality (==) because ID might be number from JSON but string from HTML attribute
        const exp = expenses.find(e => e.id == expenseId);
        if (exp) {
            document.getElementById('expenseId').value = exp.id;
            document.getElementById('inputDate').value = exp.date.substring(0, 10);
            document.getElementById('inputVendor').value = exp.vendor;
            document.getElementById('inputAmount').value = exp.amount;
            document.getElementById('inputMethod').value = exp.method;
            document.getElementById('inputContent').value = exp.content;

            // Handle Category: Add option if it doesn't exist
            const catSelect = document.getElementById('inputCategory');
            const catVal = exp.category;
            if (catVal && ![...catSelect.options].some(o => o.value === catVal)) {
                const opt = document.createElement('option');
                opt.value = catVal;
                opt.textContent = catVal;
                catSelect.appendChild(opt);
            }
            catSelect.value = catVal;

            // Handle Cycle: Add option if it doesn't exist (e.g. "1M", "2M")
            const cycleSelect = document.getElementById('inputCycle');
            const cycleVal = exp.cycle;
            if (cycleVal && ![...cycleSelect.options].some(o => o.value === cycleVal)) {
                const opt = document.createElement('option');
                opt.value = cycleVal;
                opt.textContent = cycleVal;
                cycleSelect.appendChild(opt);
            }
            cycleSelect.value = cycleVal;
            document.getElementById('formModalTitle').textContent = '지출 수정';
        }
    } else if (defaultDate) {
        document.getElementById('inputDate').value = defaultDate;
    } else {
        document.getElementById('inputDate').valueAsDate = new Date();
    }
    modal.classList.remove('hidden');
}

// Global functions for inline onclick handlers
window.editExpense = (id) => {
    document.getElementById('dayModal').classList.add('hidden');
    openFormModal(null, id);
};

// Custom Confirm Modal Logic
let pendingDeleteId = null;

window.closeConfirmModal = () => {
    document.getElementById('confirmModal').classList.add('hidden');
    pendingDeleteId = null;
};

window.deleteExpense = (event, id) => {
    event.stopPropagation();
    event.preventDefault();

    pendingDeleteId = id;
    document.getElementById('confirmModal').classList.remove('hidden');
};

document.getElementById('confirmDeleteBtn').onclick = async () => {
    if (!pendingDeleteId) return;

    const btn = document.getElementById('confirmDeleteBtn');
    const originalText = btn.textContent;
    btn.textContent = '삭제 중...';
    btn.disabled = true;

    try {
        await api.deleteExpense(pendingDeleteId);
        alert('삭제되었습니다.');
        closeConfirmModal();
        document.getElementById('dayModal').classList.add('hidden');
        loadData();
    } catch (e) {
        alert('삭제 실패: ' + e.message);
        btn.textContent = originalText;
        btn.disabled = false;
    }
};

// Form Submission
document.getElementById('expenseForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const id = document.getElementById('expenseId').value;
    const expenseData = {
        date: document.getElementById('inputDate').value,
        vendor: document.getElementById('inputVendor').value,
        category: document.getElementById('inputCategory').value,
        amount: document.getElementById('inputAmount').value,
        method: document.getElementById('inputMethod').value,
        cycle: document.getElementById('inputCycle').value,
        content: document.getElementById('inputContent').value
    };

    const submitBtn = document.querySelector('.btn-submit');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = '저장 중...';
    submitBtn.disabled = true;

    try {
        if (id) {
            await api.updateExpense({ id, ...expenseData });
            alert('수정되었습니다.');
        } else {
            await api.createExpense(expenseData);
            alert('저장되었습니다.');
        }
        document.getElementById('formModal').classList.add('hidden');
        loadData();
    } catch (e) {
        alert('저장 실패: ' + e.message);
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
});

// Format numbers as currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('ko-KR').format(amount) + '원';
}

function renderVendors() {
    const list = document.getElementById('vendorList');
    list.innerHTML = '';

    // Group by Vendor
    const vendors = {};
    expenses.forEach(e => {
        if (!vendors[e.vendor]) vendors[e.vendor] = [];
        vendors[e.vendor].push(e);
    });

    Object.keys(vendors).sort().forEach(vendorName => {
        const vendorExpenses = vendors[vendorName];

        // Group by Year
        const byYear = {};
        vendorExpenses.forEach(e => {
            const y = new Date(e.date).getFullYear();
            if (!byYear[y]) byYear[y] = { total: 0, list: [] };
            byYear[y].total += Number(e.amount);
            byYear[y].list.push(e);
        });

        // Create Card
        const card = document.createElement('div');
        card.className = 'vendor-card';

        // Create Swiper for Years
        let swiperHTML = '';
        Object.keys(byYear).sort((a, b) => b - a).forEach(year => { // Descending years
            swiperHTML += `
                <div class="year-chip" onclick="toggleVendorDetails(event, '${vendorName}', '${year}')">
                    ${year}년: ${formatCurrency(byYear[year].total)}
                </div>
            `;
        });

        card.innerHTML = `
            <div class="vendor-header">
                <span class="vendor-name">${vendorName}</span>
            </div>
            <div class="year-swiper">
                ${swiperHTML}
            </div>
            <div id="details-${vendorName}" class="vendor-details hidden">
                <!-- Details will be populated here -->
            </div>
        `;

        list.appendChild(card);
    });
}

window.toggleVendorDetails = (event, vendorName, year) => {
    event.stopPropagation(); // Prevent card click if needed
    // Simple implementation: Show list for that year in a modal or expand
    // Let's use the dayModal simply reusing it or a new specific logic? 
    // Requirement says "Click vendor card -> list". 
    // Let's implement expanding logic or reuse the DayModal style list but inline.

    // Changing approach based on "Click vendor card -> list"
    // Let's create a dynamic list inside the card or open a modal.
    // Let's use a Modal for cleaner UI as lists can be long.

    const relevantExpenses = expenses.filter(e =>
        e.vendor === vendorName && new Date(e.date).getFullYear().toString() === year
    ).sort((a, b) => new Date(b.date) - new Date(a.date)); // Descending date

    const modal = document.getElementById('dayModal'); // Reusing DayModal structure
    document.getElementById('dayModalDate').textContent = `${vendorName} (${year}년)`;

    const list = document.getElementById('dayExpenseList');
    list.innerHTML = '';

    relevantExpenses.forEach(exp => {
        const li = document.createElement('li');
        li.className = 'expense-item';
        li.innerHTML = `
            <div class="item-info">
                <span class="item-vendor">${exp.date.substring(0, 10)}</span>
                <span class="item-desc">${exp.method} | ${exp.content}</span>
            </div>
            <div class="item-right">
                <span class="item-amount">${formatCurrency(exp.amount)}</span>
            </div>
        `;
        list.appendChild(li);
    });

    modal.classList.remove('hidden');
    const closeBtn = modal.querySelector('.close-modal');
    const originalClose = closeBtn.onclick; // This might be tricky with addEventListener
    // Actually dayModal logic sets onclick for dayAddBtn every time it opens.
    // The close button just hides hidden class.
    // We need to ensure when opened as "Day View", the add button is visible.
    // Let's update openDayModal to ensure it shows the button.
}

let monthlyChart = null;
let vendorChart = null;

function renderStats() {
    const ctxM = document.getElementById('monthlyChart').getContext('2d');
    const ctxV = document.getElementById('vendorChart').getContext('2d');

    // 1. Monthly Trend
    const monthlyData = {};
    expenses.forEach(e => {
        const key = e.date.substring(0, 7); // YYYY-MM
        if (!monthlyData[key]) monthlyData[key] = 0;
        monthlyData[key] += Number(e.amount);
    });

    // Generate last 12 months based on latest data or today
    let latestDate = new Date();
    if (expenses.length > 0) {
        // expenses sorted desc
        latestDate = new Date(expenses[0].date);
    }

    const last12Months = [];
    for (let i = 11; i >= 0; i--) {
        const d = new Date(latestDate.getFullYear(), latestDate.getMonth() - i, 1);
        const year = d.getFullYear();
        const month = (d.getMonth() + 1).toString().padStart(2, '0');
        last12Months.push(`${year}-${month}`);
    }

    const formattedMonths = last12Months.map(m => m.substring(2).replace('-', '.'));
    const chartData = last12Months.map(m => monthlyData[m] || 0);

    if (monthlyChart) monthlyChart.destroy();
    monthlyChart = new Chart(ctxM, {
        type: 'bar',
        data: {
            labels: formattedMonths,
            datasets: [{
                label: '월별 지출',
                data: chartData,
                backgroundColor: '#4A90E2',
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y', // X-axis: Amount, Y-axis: Month
            plugins: {
                legend: { display: false } // Hide label
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (value) {
                            if (value === 0) return '0';
                            return (value / 10000) + '만';
                        }
                    }
                },
                y: {
                    ticks: { autoSkip: false } // Force show all months
                }
            },
            maintainAspectRatio: false // Allow resizing
        }
    });

    // 2. Vendor Average (Simple average per transaction or monthly average?) 
    // Req: "Monthly average per vendor"
    // Valid Months count per vendor? Or just Total / Total Months?
    // Let's do Total Amount / Number of unique months involved for that vendor.

    const vendorStats = {}; // { vendor: { total: 0, months: Set() } }
    expenses.forEach(e => {
        if (!vendorStats[e.vendor]) vendorStats[e.vendor] = { total: 0, months: new Set() };
        vendorStats[e.vendor].total += Number(e.amount);
        vendorStats[e.vendor].months.add(e.date.substring(0, 7));
    });

    const vendorLabels = Object.keys(vendorStats);
    const vendorAvgs = vendorLabels.map(v => {
        const count = vendorStats[v].months.size || 1;
        return vendorStats[v].total / count;
    });

    if (vendorChart) vendorChart.destroy();
    vendorChart = new Chart(ctxV, {
        type: 'bar', // or 'pie'
        data: {
            labels: vendorLabels,
            datasets: [{
                label: '월평균 지출',
                data: vendorAvgs,
                backgroundColor: '#FF5252',
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            plugins: {
                legend: { display: false } // Hide label
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (value) {
                            if (value === 0) return '0';
                            return (value / 10000) + '만';
                        }
                    }
                },
                y: {
                    ticks: { autoSkip: false } // Force show all vendors
                }
            },
            maintainAspectRatio: false
        }
    });


    // 3. Category Average
    const categoryStats = {};
    expenses.forEach(e => {
        const cat = e.category || '기타';
        if (!categoryStats[cat]) categoryStats[cat] = { total: 0, months: new Set() };
        categoryStats[cat].total += Number(e.amount);
        categoryStats[cat].months.add(e.date.substring(0, 7));
    });

    const categoryLabels = Object.keys(categoryStats);
    const categoryAvgs = categoryLabels.map(c => {
        const count = categoryStats[c].months.size || 1;
        return categoryStats[c].total / count;
    });

    // Assuming categoryChart is global or on window like others
    if (window.categoryChart instanceof Chart) window.categoryChart.destroy();

    // Get context safely
    const ctxC = document.getElementById('categoryChart').getContext('2d');

    window.categoryChart = new Chart(ctxC, {
        type: 'bar',
        data: {
            labels: categoryLabels,
            datasets: [{
                label: '월평균 지출',
                data: categoryAvgs,
                backgroundColor: '#4CAF50', // Green
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (value) {
                            if (value === 0) return '0';
                            return (value / 10000) + '만';
                        }
                    }
                },
                y: {
                    ticks: { autoSkip: false }
                }
            },
            maintainAspectRatio: false
        }
    });
}
