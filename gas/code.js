/**
 * Expense Tracker Backend (Google Apps Script)
 * 
 * INSTRUCTIONS:
 * 1. Create a new Google Sheet.
 * 2. Extensions > Apps Script.
 * 3. Paste this code into 'Code.gs'.
 * 4. Run the 'setup' function once to initialize the sheet headers.
 * 5. Deploy > New Deployment > Web App > 
 *    - Execute as: Me
 *    - Who has access: Anyone
 */

const API_KEY = "jinipini0608"; // Change this to something unique!
const SHEET_NAME = "Expenses";

function doGet(e) {
    return handleRequest(e);
}

function doPost(e) {
    return handleRequest(e);
}

function handleRequest(e) {
    const lock = LockService.getScriptLock();
    lock.tryLock(10000);

    try {
        const params = e.parameter;
        const action = params.action;

        // Simple Auth Check
        if (params.apiKey !== API_KEY) {
            return createResponse({ status: "error", message: "Invalid API Key" });
        }

        const ss = SpreadsheetApp.getActiveSpreadsheet();
        let sheet = ss.getSheetByName(SHEET_NAME);
        if (!sheet) {
            sheet = ss.insertSheet(SHEET_NAME);
            setup(); // Auto-setup if missing
        }

        if (action === "read") {
            return readExpenses(sheet);
        } else if (action === "create") {
            return createExpense(sheet, params);
        } else if (action === "update") {
            return updateExpense(sheet, params);
        } else if (action === "delete") {
            return deleteExpense(sheet, params);
        } else {
            return createResponse({ status: "error", message: "Unknown action" });
        }

    } catch (err) {
        return createResponse({ status: "error", message: err.toString() });
    } finally {
        lock.releaseLock();
    }
}

function readExpenses(sheet) {
    const data = sheet.getDataRange().getValues();
    const headers = data[0];
    let rows = data.slice(1);
    let isDirty = false;

    // 1. Filter out deleted rows first
    // Note: We keep the original 'rows' index mapping for writing back IDs if needed? 
    // Actually, writing back requires matching original sheet indices. 
    // Let's iterate ALL rows to fix IDs, then filter for return.

    const ids = [];
    const idsToUpdate = []; // [rowIndex, newId]

    // Scan for ID issues
    for (let i = 0; i < rows.length; i++) {
        let id = rows[i][0];
        const isDeleted = rows[i][8] === true;

        // Verify ID uniqueness and presence
        if (!id || ids.includes(id)) {
            id = Utilities.getUuid();
            rows[i][0] = id; // Update in memory
            sheet.getRange(i + 2, 1).setValue(id); // Write back immediately (slow but safe) or batch later
            // Batching is better but checking uniqueness requires awareness of new IDs.
            // We pushed to 'ids' array so next iteration checks against new ID.
        }
        ids.push(id);
    }

    // Now filter for response
    const expenses = rows.filter(row => row[8] !== true && row[0] !== "").map(row => {
        let obj = {};
        headers.forEach((header, index) => {
            obj[header] = row[index];
        });
        return obj;
    });

    return createResponse({ status: "success", data: expenses });
}

function createExpense(sheet, params) {
    const newRow = [
        params.id || Utilities.getUuid(),
        params.vendor,
        params.amount,
        params.date,
        params.method,
        params.category,
        params.cycle,
        params.content,
        false // isDeleted
    ];

    sheet.appendRow(newRow);
    return createResponse({ status: "success", message: "Expense created", id: newRow[0] });
}

function updateExpense(sheet, params) {
    const id = params.id;
    const data = sheet.getDataRange().getValues();

    for (let i = 1; i < data.length; i++) {
        if (data[i][0] == id) {
            // Columns: ID(0), Vendor(1), Amount(2), Date(3), Method(4), Category(5), Cycle(6), Content(7), isDeleted(8)
            // Note: Sheet columns are 1-indexed. ID=1, Vendor=2, Amount=3, Date=4...
            if (params.vendor) sheet.getRange(i + 1, 2).setValue(params.vendor);
            if (params.amount) sheet.getRange(i + 1, 3).setValue(params.amount);
            if (params.date) sheet.getRange(i + 1, 4).setValue(params.date);
            if (params.method) sheet.getRange(i + 1, 5).setValue(params.method);
            if (params.category) sheet.getRange(i + 1, 6).setValue(params.category);
            if (params.cycle) sheet.getRange(i + 1, 7).setValue(params.cycle);
            if (params.content) sheet.getRange(i + 1, 8).setValue(params.content);

            return createResponse({ status: "success", message: "Expense updated" });
        }
    }
    return createResponse({ status: "error", message: "ID not found" });
}

function deleteExpense(sheet, params) {
    const id = params.id;
    const data = sheet.getDataRange().getValues();

    for (let i = 1; i < data.length; i++) {
        if (data[i][0] == id) {
            // Soft delete: set isDeleted (column 9) to true
            sheet.getRange(i + 1, 9).setValue(true);
            return createResponse({ status: "success", message: "Expense deleted" });
        }
    }
    return createResponse({ status: "error", message: "ID not found" });
}

function setup() {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName(SHEET_NAME);
    if (!sheet) {
        sheet = ss.insertSheet(SHEET_NAME);
    }

    // Headers
    const headers = ["id", "vendor", "amount", "date", "method", "category", "cycle", "content", "isDeleted"];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.setFrozenRows(1);
}

function createResponse(data) {
    return ContentService.createTextOutput(JSON.stringify(data))
        .setMimeType(ContentService.MimeType.JSON);
}
