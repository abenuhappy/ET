/**
 * API Service for Expense Tracker
 * Handles communication with Google Apps Script Backend
 */

// CONFIGURATION
// You will get this URL after deploying the Google Apps Script
const API_URL = "https://script.google.com/macros/s/AKfycbz0rJblkGBUQ-shbO8wIfTQmc7gkQcdDq7dTXZGIOoSsOpQ06rlidb1JofdSvpuehxx/exec";
const API_KEY = "jinipini0608"; // Must match the key in gas/code.js

const api = {
    /**
     * Fetch all expenses
     */
    getExpenses: async () => {
        try {
            const response = await fetch(`${API_URL}?action=read&apiKey=${API_KEY}`);
            const result = await response.json();
            if (result.status === "success") {
                // Map Korean headers or mismatching keys to standard keys
                return result.data.map(item => {
                    // Helper to check if a value looks like a date (YYYY-MM-DD or ISO)
                    const isDate = (val) => val && (
                        typeof val === 'string' && (val.match(/^\d{4}-\d{2}-\d{2}/) || val.includes('T')) ||
                        val instanceof Date
                    );

                    // Normalize keys
                    let id = item['id'] || item['ID'];
                    let date = item['date'] || item['승인 날짜'] || item['날짜'];
                    let vendor = item['vendor'] || item['거래처'];
                    let amount = item['amount'] || item['금액'];
                    let method = item['method'] || item['지불방법'] || item['결제수단'];
                    let cycle = item['cycle'] || item['결제 주기'] || item['주기'];
                    let category = item['category'] || item['카테고리'] || '기타';
                    let content = item['content'] || item['내용'];

                    // Heuristic correction for shifted data (Date vs Vendor vs Amount)
                    // Issue: Vendor field having Date string, Date field having Amount

                    // 1. If 'vendor' looks like a Date, and 'date' looks like number/amount
                    if (isDate(vendor) && !isDate(date) && !isNaN(Number(date))) {
                        // Swap or shift?
                        // If vendor is date, then likely: Date -> Amount, Vendor -> Date? No that's weird.
                        // Let's just find the properties in the object that match types

                        // Find a property that matches Date
                        const dateVal = Object.values(item).find(v => isDate(v));
                        if (dateVal) date = dateVal;

                        // Find a property that matches Amount (number or string number > 1000 usually)
                        const amountVal = Object.values(item).find(v => !isNaN(Number(v)) && Number(v) > 0 && v !== dateVal && v !== id);
                        if (amountVal) amount = amountVal;

                        // Remaining string matching... it's risky but let's trust the fix for Date/Amount first
                    }

                    // Force formatted Date string
                    let dateStr = "";
                    try {
                        if (date) {
                            const d = new Date(date);
                            if (!isNaN(d.getTime())) {
                                // Convert to KST (Asia/Seoul) YYYY-MM-DD
                                dateStr = d.toLocaleDateString('en-CA', { timeZone: 'Asia/Seoul' });
                            }
                        }
                    } catch (e) { console.error("Date parse error", date); }

                    return {
                        id: id,
                        date: dateStr,
                        vendor: typeof vendor === 'string' && !isDate(vendor) ? vendor : (isDate(vendor) ? "Vendor_Error" : vendor),
                        amount: amount,
                        method: method,
                        cycle: cycle,
                        category: category,
                        content: content
                    };
                });
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error("API Error (read):", error);
            alert("Failed to load expenses: " + error.message);
            return [];
        }
    },

    /**
     * Create a new expense
     * @param {Object} expense 
     */
    createExpense: async (expense) => {
        // expense object should contain: date, vendor, amount, method, cycle, category, content
        const params = new URLSearchParams({
            action: "create",
            apiKey: API_KEY,
            ...expense
        });

        try {
            const response = await fetch(`${API_URL}`, {
                method: "POST",
                body: params
            });
            const result = await response.json();
            if (result.status !== "success") {
                throw new Error(result.message);
            }
            return result;
        } catch (error) {
            console.error("API Error (create):", error);
            throw error;
        }
    },

    /**
     * Update an existing expense
     * @param {Object} expense 
     */
    updateExpense: async (expense) => {
        // expense object must contain 'id'
        const params = new URLSearchParams({
            action: "update",
            apiKey: API_KEY,
            ...expense
        });

        try {
            const response = await fetch(`${API_URL}`, {
                method: "POST",
                body: params
            });
            const result = await response.json();
            if (result.status !== "success") {
                throw new Error(result.message);
            }
            return result;
        } catch (error) {
            console.error("API Error (update):", error);
            throw error;
        }
    },

    /**
     * Delete an expense
     * @param {string} id 
     */
    deleteExpense: async (id) => {
        const params = new URLSearchParams({
            action: "delete",
            apiKey: API_KEY,
            id: id
        });

        try {
            const response = await fetch(`${API_URL}`, {
                method: "POST",
                body: params
            });
            const result = await response.json();
            if (result.status !== "success") {
                throw new Error(result.message);
            }
            return result;
        } catch (error) {
            console.error("API Error (delete):", error);
            throw error;
        }
    }
};
