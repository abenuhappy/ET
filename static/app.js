const qs = (id) => document.getElementById(id);

async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || res.statusText);
  }
  return res.json();
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatCurrency(amount) {
  return new Intl.NumberFormat("ko-KR").format(Math.round(amount)) + "원";
}

function formatAmountOnly(amount) {
  return new Intl.NumberFormat("ko-KR").format(Math.round(amount));
}

function formatDate(dateStr) {
  if (!dateStr) return "-";
  return dateStr;
}

function formatDateKorean(dateStr) {
  if (!dateStr) return "-";
  // dateStr format: YYYY-MM-DD
  const [year, month, day] = dateStr.split("-");
  const yy = year.slice(2); // Get last 2 digits of year
  return `${yy}년 ${parseInt(month)}월 ${parseInt(day)}일`;
}


// 하단 탭 전환 로직
const navItems = document.querySelectorAll(".nav-item");
const tabContents = document.querySelectorAll(".tab-content");

navItems.forEach((item) => {
  item.addEventListener("click", () => {
    const tabId = item.getAttribute("data-tab");

    // 활성 탭 버튼 변경
    navItems.forEach((btn) => btn.classList.remove("active"));
    item.classList.add("active");

    // 활성 탭 컨텐츠 변경
    tabContents.forEach((content) => content.classList.remove("active"));
    qs(`tab-${tabId}`).classList.add("active");

    // 탭 전환 시 필요한 데이터 로드
    if (tabId === "statistics") {
      loadStatistics();
    } else if (tabId === "payees") {
      loadPayees();
    }
  });
});

async function loadStatistics() {
  const res = await api("/api/statistics");

  // 총 지출액
  qs("totalAmount").textContent = formatCurrency(res.total_amount || 0);

  // 거래처별 합계
  const merchantTbody = qs("merchantStatsTable").querySelector("tbody");
  merchantTbody.innerHTML = (res.merchant_totals || [])
    .map((item) => {
      return `
        <tr>
          <td data-label="거래처">${escapeHtml(item.merchant)}</td>
          <td data-label="합계">${formatCurrency(item.total)}</td>
        </tr>
      `;
    })
    .join("");

  // 지불처별 합계
  const paymentTbody = qs("paymentStatsTable").querySelector("tbody");
  paymentTbody.innerHTML = (res.payment_totals || [])
    .map((item) => {
      return `
        <tr>
          <td data-label="지불처">${escapeHtml(item.payment_method)}</td>
          <td data-label="합계">${formatCurrency(item.total)}</td>
        </tr>
      `;
    })
    .join("");

  // 결제주기별 합계
  const cycleTbody = qs("cycleStatsTable").querySelector("tbody");
  cycleTbody.innerHTML = (res.cycle_totals || [])
    .map((item) => {
      return `
        <tr>
          <td data-label="결제주기">${escapeHtml(item.payment_cycle)}</td>
          <td data-label="합계">${formatCurrency(item.total)}</td>
        </tr>
      `;
    })
    .join("");
}

async function saveExpenseRow(tr) {
  const id = parseInt(tr.getAttribute("data-id"));
  const inputs = tr.querySelectorAll("input[data-k]");
  const data = {};

  inputs.forEach((inp) => {
    const k = inp.getAttribute("data-k");
    const v = inp.value.trim();
    if (k === "amount") {
      data[k] = parseFloat(v) || 0;
    } else {
      data[k] = v;
    }
  });

  await api(`/api/expenses/${id}`, {
    method: "PUT",
    body: JSON.stringify({
      merchant: data.merchant,
      amount: data.amount,
      approval_date: data.approval_date,
      payment_method: data.payment_method,
      payment_cycle: data.payment_cycle,
    }),
  });
}

async function deleteExpense(id) {
  if (!confirm("정말 삭제하시겠습니까?")) return;

  try {
    await api(`/api/expenses/${id}`, { method: "DELETE" });
    await loadAll();
  } catch (err) {
    alert("삭제 실패: " + err.message);
  }
}

async function loadAll() {
  await loadStatistics();
  renderCalendar();
  if (selectedDate) {
    loadDateExpenses(selectedDate);
  }
}

// 지출 추가 모달
const expenseModal = qs("expenseModal");
const expenseForm = qs("expenseForm");
const btnAddExpense = qs("btnAddExpense");
const btnCloseModal = qs("btnCloseModal");
const btnCancel = qs("btnCancel");

function openModal(data = null) {
  expenseModal.style.display = "flex";

  if (data && data.id) {
    // 수정 모드
    qs("modalTitle").textContent = "지출 수정";
    qs("expenseId").value = data.id;
    qs("merchant").value = data.merchant;
    qs("amount").value = data.amount;
    qs("approvalDate").value = data.approval_date;
    qs("paymentMethod").value = data.payment_method;
    qs("paymentCycle").value = data.payment_cycle;
  } else {
    // 추가 모드
    qs("modalTitle").textContent = "지출 추가";
    qs("expenseId").value = "";
    expenseForm.reset();
    if (data && data.date) {
      qs("approvalDate").value = data.date;
    }
  }
}

function closeModal() {
  expenseModal.style.display = "none";
}

const btnAddExpenseDate = qs("btnAddExpenseDate");
if (btnAddExpenseDate) {
  btnAddExpenseDate.addEventListener("click", () => {
    openModal({ date: selectedDate });
  });
}

if (btnCloseModal) {
  btnCloseModal.addEventListener("click", closeModal);
}

if (btnCancel) {
  btnCancel.addEventListener("click", closeModal);
}

if (expenseForm) {
  expenseForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const id = qs("expenseId").value;
    const data = {
      merchant: qs("merchant").value.trim(),
      amount: parseFloat(qs("amount").value) || 0,
      approval_date: qs("approvalDate").value,
      payment_method: qs("paymentMethod").value.trim(),
      payment_cycle: qs("paymentCycle").value,
    };

    if (!data.merchant || !data.approval_date || !data.payment_method || !data.payment_cycle) {
      alert("모든 필수 항목을 입력하세요.");
      return;
    }

    try {
      if (id) {
        // 수정
        await api(`/api/expenses/${id}`, {
          method: "PUT",
          body: JSON.stringify(data),
        });
      } else {
        // 추가
        await api("/api/expenses", {
          method: "POST",
          body: JSON.stringify(data),
        });
      }
      closeModal();
      await loadAll();
    } catch (err) {
      alert("저장 실패: " + err.message);
    }
  });
}

// 전역 함수로 등록 (onclick 등에서 사용)
window.editExpense = (id, merchant, amount, date, method, cycle) => {
  openModal({
    id, merchant, amount, approval_date: date,
    payment_method: method, payment_cycle: cycle
  });
};

window.deleteExpense = async (id) => {
  if (!confirm("정말 삭제하시겠습니까?")) return;
  try {
    await api(`/api/expenses/${id}`, { method: "DELETE" });
    await loadAll();
  } catch (err) {
    alert("삭제 실패: " + err.message);
  }
};

// 검색 기능
const btnSearch = qs("btnSearch");
const searchInput = qs("searchInput");
const searchResultsSection = qs("searchResultsSection");
const searchResultsTbody = qs("searchResultsTable").querySelector("tbody");

if (btnSearch) {
  btnSearch.addEventListener("click", async () => {
    const q = searchInput.value.trim();
    if (!q) {
      alert("검색어를 입력하세요.");
      return;
    }

    try {
      btnSearch.disabled = true;
      btnSearch.textContent = "검색 중...";

      const res = await api(`/api/expenses/search?q=${encodeURIComponent(q)}`);
      const expenses = res.expenses || [];

      if (expenses.length === 0) {
        searchResultsTbody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 20px;">검색 결과가 없습니다.</td></tr>';
      } else {
        searchResultsTbody.innerHTML = expenses
          .map((exp) => {
            return `
              <tr>
                <td>${escapeHtml(exp.merchant)}</td>
                <td>${formatDateKorean(exp.approval_date)}</td>
                <td>${formatCurrency(exp.amount)}</td>
              </tr>
            `;
          })
          .join("");
      }

      searchResultsSection.style.display = "block";
    } catch (err) {
      alert("검색 실패: " + err.message);
    } finally {
      btnSearch.disabled = false;
      btnSearch.textContent = "검색";
    }
  });
}

// 캘린더 관련 변수
let currentDate = new Date();
let selectedDate = null;

// 캘린더 렌더링
function renderCalendar() {
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  // 월/년도 표시
  qs("currentMonthYear").textContent = `${year}년 ${month + 1}월`;

  // 해당 월의 첫 날과 마지막 날
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const daysInMonth = lastDay.getDate();
  const startDayOfWeek = firstDay.getDay();

  // 캘린더 데이터 로드
  loadCalendarData(year, month + 1).then((dailyData) => {
    const calendar = qs("calendar");
    calendar.innerHTML = "";

    // 요일 헤더
    const weekdays = ["일", "월", "화", "수", "목", "금", "토"];
    weekdays.forEach((day) => {
      const header = document.createElement("div");
      header.className = "calendar-header";
      header.textContent = day;
      calendar.appendChild(header);
    });

    // 이전 달의 마지막 날들
    const prevMonthLastDay = new Date(year, month, 0).getDate();
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      const day = prevMonthLastDay - i;
      const dayEl = createCalendarDay(day, year, month - 1, true, null);
      calendar.appendChild(dayEl);
    }

    // 현재 달의 날들
    const today = new Date();
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
      const dayData = dailyData[dateStr];
      const isToday =
        today.getFullYear() === year &&
        today.getMonth() === month &&
        today.getDate() === day;

      const dayEl = createCalendarDay(day, year, month, false, dayData, isToday, dateStr);
      calendar.appendChild(dayEl);
    }

    // 다음 달의 첫 날들
    const totalCells = calendar.children.length - 7; // 헤더 제외
    const remainingCells = 35 - totalCells; // 5주 * 7일 = 35
    for (let day = 1; day <= remainingCells; day++) {
      const dayEl = createCalendarDay(day, year, month + 1, true, null);
      calendar.appendChild(dayEl);
    }
  });
}

function createCalendarDay(day, year, month, isOtherMonth, dayData, isToday = false, dateStr = null) {
  const dayEl = document.createElement("div");
  dayEl.className = "calendar-day";

  if (isOtherMonth) {
    dayEl.classList.add("other-month");
  }

  if (isToday) {
    dayEl.classList.add("today");
  }

  if (dayData && dayData.total > 0) {
    dayEl.classList.add("has-expense");
  }

  if (dateStr && selectedDate === dateStr) {
    dayEl.classList.add("selected");
  }

  const dayNumber = document.createElement("div");
  dayNumber.className = "day-number";
  dayNumber.textContent = day;
  dayEl.appendChild(dayNumber);

  if (dayData && dayData.total > 0) {
    const dayAmount = document.createElement("div");
    dayAmount.className = "day-amount";
    dayAmount.textContent = formatAmountOnly(dayData.total);
    dayEl.appendChild(dayAmount);
  }

  if (dateStr) {
    dayEl.addEventListener("click", () => {
      selectedDate = dateStr;
      renderCalendar();
      loadDateExpenses(dateStr);
    });
  }

  return dayEl;
}

async function loadCalendarData(year, month) {
  try {
    const res = await api(`/api/expenses/calendar?year=${year}&month=${month}`);
    return res.daily_data || {};
  } catch (err) {
    console.error("캘린더 데이터 로드 실패:", err);
    return {};
  }
}

async function loadDateExpenses(dateStr) {
  try {
    const res = await api(`/api/expenses/by-date?date=${dateStr}`);
    const expenses = res.expenses || [];

    const dateExpenses = qs("dateExpenses");
    const title = qs("selectedDateTitle");
    const tbody = qs("dateExpensesTable").querySelector("tbody");

    title.textContent = `${formatDateKorean(dateStr)} 지출 내역 (${expenses.length
      }건)`;

    if (expenses.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="5" style="text-align: center; padding: 20px;">해당 날짜에 지출이 없습니다.</td></tr>';
    } else {
      tbody.innerHTML = expenses
        .map((exp) => {
          return `
            <tr>
              <td data-label="거래처">${escapeHtml(exp.merchant)}</td>
              <td data-label="금액">${formatCurrency(exp.amount)}</td>
              <td data-label="지불처">${escapeHtml(exp.payment_method)}</td>
              <td data-label="결제주기">${escapeHtml(exp.payment_cycle)}</td>
              <td data-label="관리">
                <div class="action-btns">
                  <button class="btn btn-sm" onclick="editExpense(${exp.id
            }, '${escapeHtml(exp.merchant).replace(
              /'/g,
              "\\'"
            )}', ${exp.amount}, '${exp.approval_date}', '${escapeHtml(
              exp.payment_method
            ).replace(/'/g, "\\'")}', '${escapeHtml(exp.payment_cycle).replace(
              /'/g,
              "\\'"
            )}')">수정</button>
                  <button class="btn btn-danger btn-sm" onclick="deleteExpense(${exp.id
            })">삭제</button>
                </div>
              </td>
            </tr>
          `;
        })
        .join("");
    }

    dateExpenses.style.display = "block";
  } catch (err) {
    console.error("날짜별 지출 로드 실패:", err);
  }
}

// 월 이동 버튼
const btnPrevMonth = qs("btnPrevMonth");
const btnNextMonth = qs("btnNextMonth");

if (btnPrevMonth) {
  btnPrevMonth.addEventListener("click", () => {
    currentDate.setMonth(currentDate.getMonth() - 1);
    selectedDate = null;
    renderCalendar();
    qs("dateExpenses").style.display = "none";
  });
}

if (btnNextMonth) {
  btnNextMonth.addEventListener("click", () => {
    currentDate.setMonth(currentDate.getMonth() + 1);
    selectedDate = null;
    renderCalendar();
    qs("dateExpenses").style.display = "none";
  });
}

// 거래처 관리 기능
async function loadPayees() {
  try {
    const res = await api("/api/payees");
    const payees = res.payees || [];
    const container = qs("payeeListSection");

    if (payees.length === 0) {
      container.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-light);">등록된 거래처가 없습니다.</div>';
    } else {
      container.innerHTML = payees.map(p => `
        <div class="payee-card">
          <div class="payee-info">
            <div class="payee-name">${escapeHtml(p.name)}</div>
            <div class="payee-details">
              <span>${escapeHtml(p.bank_name)}</span> | 
              <span>${escapeHtml(p.account_number)}</span> | 
              <span>${escapeHtml(p.owner_name)}</span>
            </div>
          </div>
          <div class="payee-actions">
            <button class="btn btn-sm" onclick="editPayee(${p.id}, '${escapeHtml(p.name).replace(/'/g, "\\'")}',' ${escapeHtml(p.bank_name).replace(/'/g, "\\'")}',' ${escapeHtml(p.account_number).replace(/'/g, "\\'")}',' ${escapeHtml(p.owner_name).replace(/'/g, "\\'")}')" >수정</button>
            <button class="btn btn-danger btn-sm" onclick="deletePayee(${p.id})">삭제</button>
          </div>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("거래처 로드 실패:", err);
  }
}

const payeeModal = qs("payeeModal");
const btnAddPayee = qs("btnAddPayee");
const btnClosePayeeModal = qs("btnClosePayeeModal");
const btnCancelPayee = qs("btnCancelPayee");
const payeeForm = qs("payeeForm");
let editingPayeeId = null;

if (btnAddPayee) {
  btnAddPayee.addEventListener("click", () => {
    editingPayeeId = null;
    qs("payeeModalTitle").textContent = "거래처 추가";
    payeeModal.style.display = "flex";
  });
}

function closePayeeModal() {
  payeeModal.style.display = "none";
  payeeForm.reset();
  editingPayeeId = null;
}

if (btnClosePayeeModal) btnClosePayeeModal.addEventListener("click", closePayeeModal);
if (btnCancelPayee) btnCancelPayee.addEventListener("click", closePayeeModal);

if (payeeForm) {
  payeeForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = {
      name: qs("payeeName").value.trim(),
      bank_name: qs("payeeBank").value.trim(),
      account_number: qs("payeeAccount").value.trim(),
      owner_name: qs("payeeOwner").value.trim(),
    };

    try {
      if (editingPayeeId) {
        await api(`/api/payees/${editingPayeeId}`, {
          method: "PUT",
          body: JSON.stringify(data),
        });
      } else {
        await api("/api/payees", {
          method: "POST",
          body: JSON.stringify(data),
        });
      }
      closePayeeModal();
      loadPayees();
    } catch (err) {
      alert("거래처 저장 실패: " + err.message);
    }
  });
}

window.editPayee = (id, name, bankName, accountNumber, ownerName) => {
  editingPayeeId = id;
  qs("payeeModalTitle").textContent = "거래처 수정";
  qs("payeeName").value = name;
  qs("payeeBank").value = bankName;
  qs("payeeAccount").value = accountNumber;
  qs("payeeOwner").value = ownerName;
  payeeModal.style.display = "flex";
};

window.deletePayee = async (id) => {
  if (!confirm("이 거래처를 삭제하시겠습니까?")) return;
  try {
    await api(`/api/payees/${id}`, { method: "DELETE" });
    loadPayees();
  } catch (err) {
    alert("거래처 삭제 실패: " + err.message);
  }
};

// 초기 로드
loadAll();
renderCalendar();
