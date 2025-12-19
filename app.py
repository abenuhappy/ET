from __future__ import annotations

import csv
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from functools import wraps

# 기본 디렉토리
APP_DIR = Path(__file__).parent.absolute()
DB_PATH = APP_DIR / "expense_tracker.db"

app = Flask(__name__)

# 세션 암호화를 위한 SECRET_KEY 설정
import os
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# 비밀번호 설정 (환경 변수 또는 기본값)
APP_PASSWORD = os.environ.get('APP_PASSWORD', 'jinipini0608')


# 인증 데코레이터
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({'error': '인증이 필요합니다.'}), 401
        return f(*args, **kwargs)
    return decorated_function


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              merchant TEXT NOT NULL,
              amount REAL NOT NULL,
              approval_date TEXT NOT NULL,
              payment_method TEXT NOT NULL,
              payment_cycle TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payees (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              account_number TEXT NOT NULL,
              bank_name TEXT NOT NULL,
              owner_name TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        conn.commit()


@app.get("/api/payees")
@login_required
def list_payees():
    """거래처 목록 조회"""
    with _db() as conn:
        rows = conn.execute("SELECT * FROM payees ORDER BY name ASC").fetchall()
        payees = [
            {
                "id": row["id"],
                "name": row["name"],
                "account_number": row["account_number"],
                "bank_name": row["bank_name"],
                "owner_name": row["owner_name"],
            }
            for row in rows
        ]
    return jsonify({"payees": payees})


@app.post("/api/payees")
@login_required
def create_payee():
    """거래처 추가"""
    payload = request.get_json(force=True) or {}
    name = payload.get("name", "").strip()
    account_number = payload.get("account_number", "").strip()
    bank_name = payload.get("bank_name", "").strip()
    owner_name = payload.get("owner_name", "").strip()

    if not name or not account_number or not bank_name or not owner_name:
        return jsonify({"error": "필수 항목이 누락되었습니다."}), 400

    with _db() as conn:
        cur = conn.execute(
            """
            INSERT INTO payees (name, account_number, bank_name, owner_name)
            VALUES (?, ?, ?, ?)
            """,
            (name, account_number, bank_name, owner_name),
        )
        conn.commit()
    return jsonify({"ok": True})


@app.put("/api/payees/<int:payee_id>")
@login_required
def update_payee(payee_id: int):
    """거래처 수정"""
    payload = request.get_json(force=True) or {}
    name = payload.get("name", "").strip()
    account_number = payload.get("account_number", "").strip()
    bank_name = payload.get("bank_name", "").strip()
    owner_name = payload.get("owner_name", "").strip()

    if not name or not account_number or not bank_name or not owner_name:
        return jsonify({"error": "필수 항목이 누락되었습니다."}), 400

    with _db() as conn:
        conn.execute(
            """
            UPDATE payees 
            SET name = ?, account_number = ?, bank_name = ?, owner_name = ?,
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (name, account_number, bank_name, owner_name, payee_id),
        )
        conn.commit()
    return jsonify({"ok": True})


@app.delete("/api/payees/<int:payee_id>")
@login_required
def delete_payee(payee_id: int):
    """거래처 삭제"""
    with _db() as conn:
        conn.execute("DELETE FROM payees WHERE id = ?", (payee_id,))
        conn.commit()
    return jsonify({"ok": True})


def _parse_amount(amount_str: str) -> float:
    """금액 문자열을 float로 변환 (콤마 제거)"""
    if not amount_str:
        return 0.0
    try:
        # 콤마 제거 후 변환
        return float(amount_str.replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0


def _parse_date(date_str: str) -> str:
    """날짜 문자열을 YYYY-MM-DD 형식으로 변환 (25/05/28 -> 2025-05-28)"""
    if not date_str:
        return ""
    try:
        # 25/05/28 형식 파싱
        parts = date_str.split("/")
        if len(parts) == 3:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            # 25 -> 2025, 24 -> 2024 등으로 변환
            if year < 100:
                year += 2000
            return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, AttributeError):
        pass
    return date_str


@app.route("/")
def index():
    if not session.get('authenticated'):
        return redirect(url_for('login_page'))
    return render_template("index.html")


@app.route("/login")
def login_page():
    """로그인 페이지"""
    return render_template("login.html")


@app.post("/api/login")
def login():
    """로그인 API"""
    payload = request.get_json(force=True) or {}
    password = payload.get('password', '')
    
    if password == APP_PASSWORD:
        session['authenticated'] = True
        return jsonify({'ok': True})
    else:
        return jsonify({'error': '비밀번호가 올바르지 않습니다.'}), 401


@app.post("/api/logout")
def logout():
    """로그아웃 API"""
    session.pop('authenticated', None)
    return jsonify({'ok': True})


@app.get("/api/expenses")
@login_required
def list_expenses():
    """지출 목록 조회"""
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM expenses ORDER BY approval_date DESC, id DESC"
        ).fetchall()
        expenses = [
            {
                "id": row["id"],
                "merchant": row["merchant"],
                "amount": row["amount"],
                "approval_date": row["approval_date"],
                "payment_method": row["payment_method"],
                "payment_cycle": row["payment_cycle"],
            }
            for row in rows
        ]
    return jsonify({"expenses": expenses})


@app.post("/api/expenses")
@login_required
def create_expense():
    """지출 추가"""
    payload = request.get_json(force=True) or {}
    
    merchant = payload.get("merchant", "").strip()
    amount = _parse_amount(payload.get("amount", "0"))
    approval_date = _parse_date(payload.get("approval_date", ""))
    payment_method = payload.get("payment_method", "").strip()
    payment_cycle = payload.get("payment_cycle", "").strip()
    
    if not merchant or not approval_date or not payment_method or not payment_cycle:
        return jsonify({"error": "필수 항목이 누락되었습니다."}), 400
    
    with _db() as conn:
        cur = conn.execute(
            """
            INSERT INTO expenses (merchant, amount, approval_date, payment_method, payment_cycle)
            VALUES (?, ?, ?, ?, ?)
            """,
            (merchant, amount, approval_date, payment_method, payment_cycle),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (cur.lastrowid,)).fetchone()
    
    return jsonify({
        "expense": {
            "id": row["id"],
            "merchant": row["merchant"],
            "amount": row["amount"],
            "approval_date": row["approval_date"],
            "payment_method": row["payment_method"],
            "payment_cycle": row["payment_cycle"],
        }
    })


@app.put("/api/expenses/<int:expense_id>")
@login_required
def update_expense(expense_id: int):
    """지출 수정"""
    payload = request.get_json(force=True) or {}
    
    merchant = payload.get("merchant", "").strip()
    amount = _parse_amount(payload.get("amount", "0"))
    approval_date = _parse_date(payload.get("approval_date", ""))
    payment_method = payload.get("payment_method", "").strip()
    payment_cycle = payload.get("payment_cycle", "").strip()
    
    if not merchant or not approval_date or not payment_method or not payment_cycle:
        return jsonify({"error": "필수 항목이 누락되었습니다."}), 400
    
    with _db() as conn:
        conn.execute(
            """
            UPDATE expenses
            SET merchant = ?, amount = ?, approval_date = ?, payment_method = ?, payment_cycle = ?,
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (merchant, amount, approval_date, payment_method, payment_cycle, expense_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    
    if not row:
        return jsonify({"error": "지출을 찾을 수 없습니다."}), 404
    
    return jsonify({
        "expense": {
            "id": row["id"],
            "merchant": row["merchant"],
            "amount": row["amount"],
            "approval_date": row["approval_date"],
            "payment_method": row["payment_method"],
            "payment_cycle": row["payment_cycle"],
        }
    })


@app.delete("/api/expenses/<int:expense_id>")
@login_required
def delete_expense(expense_id: int):
    """지출 삭제"""
    with _db() as conn:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
    return jsonify({"ok": True})


@app.post("/api/import/csv")
@login_required
def import_csv():
    """CSV 파일 업로드 및 데이터 임포트"""
    if "file" not in request.files:
        return jsonify({"error": "file 필드가 필요합니다."}), 400
    
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "파일이 선택되지 않았습니다."}), 400
    
    try:
        # CSV 파일 읽기
        text = f.read().decode("utf-8-sig")  # BOM 제거
        reader = csv.DictReader(text.splitlines())
        
        inserted = 0
        errors = []
        
        with _db() as conn:
            for idx, row in enumerate(reader, start=2):  # 헤더 제외하고 2부터 시작
                try:
                    merchant = row.get("학원", "").strip()
                    amount_str = row.get("금액", "").strip()
                    approval_date_str = row.get("승인 날짜", "").strip()
                    payment_method = row.get("거래처", "").strip()
                    payment_cycle = row.get("결제 주기", "").strip()
                    
                    # 빈 행 건너뛰기
                    if not merchant or not approval_date_str:
                        continue
                    
                    amount = _parse_amount(amount_str)
                    approval_date = _parse_date(approval_date_str)
                    
                    if not approval_date:
                        errors.append(f"{idx}행: 날짜 형식 오류 ({approval_date_str})")
                        continue
                    
                    # 중복 체크 (같은 거래처, 금액, 날짜가 있으면 건너뛰기)
                    existing = conn.execute(
                        "SELECT id FROM expenses WHERE merchant = ? AND amount = ? AND approval_date = ?",
                        (merchant, amount, approval_date)
                    ).fetchone()
                    
                    if existing:
                        continue
                    
                    conn.execute(
                        """
                        INSERT INTO expenses (merchant, amount, approval_date, payment_method, payment_cycle)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (merchant, amount, approval_date, payment_method, payment_cycle),
                    )
                    inserted += 1
                except Exception as e:
                    errors.append(f"{idx}행: {str(e)}")
            
            conn.commit()
        
        return jsonify({
            "inserted": inserted,
            "errors": errors,
        })
    except Exception as e:
        return jsonify({"error": f"CSV 업로드 중 오류가 발생했습니다: {str(e)}"}), 500


@app.get("/api/statistics")
@login_required
def get_statistics():
    """통계 정보 조회"""
    with _db() as conn:
        # 총 지출액
        total_row = conn.execute("SELECT SUM(amount) as total FROM expenses").fetchone()
        total_amount = total_row["total"] or 0.0
        
        # 거래처별 합계
        merchant_rows = conn.execute(
            """
            SELECT merchant, SUM(amount) as total
            FROM expenses
            GROUP BY merchant
            ORDER BY total DESC
            """
        ).fetchall()
        merchant_totals = [
            {"merchant": row["merchant"], "total": row["total"]}
            for row in merchant_rows
        ]
        
        # 지불처별 합계
        payment_rows = conn.execute(
            """
            SELECT payment_method, SUM(amount) as total
            FROM expenses
            GROUP BY payment_method
            ORDER BY total DESC
            """
        ).fetchall()
        payment_totals = [
            {"payment_method": row["payment_method"], "total": row["total"]}
            for row in payment_rows
        ]
        
        # 결제 주기별 합계
        cycle_rows = conn.execute(
            """
            SELECT payment_cycle, SUM(amount) as total
            FROM expenses
            GROUP BY payment_cycle
            ORDER BY total DESC
            """
        ).fetchall()
        cycle_totals = [
            {"payment_cycle": row["payment_cycle"], "total": row["total"]}
            for row in cycle_rows
        ]
    
    return jsonify({
        "total_amount": total_amount,
        "merchant_totals": merchant_totals,
        "payment_totals": payment_totals,
        "cycle_totals": cycle_totals,
    })


@app.get("/api/expenses/by-date")
@login_required
def get_expenses_by_date():
    """날짜별 지출 조회"""
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "date 파라미터가 필요합니다."}), 400
    
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM expenses
            WHERE approval_date = ?
            ORDER BY id DESC
            """,
            (date_str,),
        ).fetchall()
        expenses = [
            {
                "id": row["id"],
                "merchant": row["merchant"],
                "amount": row["amount"],
                "approval_date": row["approval_date"],
                "payment_method": row["payment_method"],
                "payment_cycle": row["payment_cycle"],
            }
            for row in rows
        ]
    return jsonify({"expenses": expenses})


@app.get("/api/expenses/calendar")
@login_required
def get_calendar_data():
    """캘린더용 월별 지출 데이터 조회"""
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    
    if not year or not month:
        return jsonify({"error": "year와 month 파라미터가 필요합니다."}), 400
    
    # 해당 월의 시작일과 종료일 계산
    from datetime import datetime
    start_date = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{month+1:02d}-01"
    
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT approval_date, SUM(amount) as total, COUNT(*) as count
            FROM expenses
            WHERE approval_date >= ? AND approval_date < ?
            GROUP BY approval_date
            ORDER BY approval_date
            """,
            (start_date, end_date),
        ).fetchall()
        
        daily_data = {
            row["approval_date"]: {
                "total": row["total"],
                "count": row["count"],
            }
            for row in rows
        }
    
    return jsonify({"daily_data": daily_data})


@app.get("/api/expenses/search")
@login_required
def search_expenses():
    """거래처 또는 지불처 검색"""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"expenses": []})
    
    search_term = f"%{query}%"
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT merchant, approval_date, amount, payment_method
            FROM expenses
            WHERE merchant LIKE ? OR payment_method LIKE ?
            ORDER BY approval_date DESC, id DESC
            """,
            (search_term, search_term),
        ).fetchall()
        
        expenses = [
            {
                "merchant": row["merchant"],
                "approval_date": row["approval_date"],
                "amount": row["amount"],
                "payment_method": row["payment_method"],
            }
            for row in rows
        ]
        
    return jsonify({"expenses": expenses})


def main() -> None:
    import os
    _init_db()
    
    # Render는 PORT 환경 변수를 제공합니다
    port = int(os.environ.get("PORT", 5056))
    # 프로덕션 환경에서는 debug=False
    debug = os.environ.get("FLASK_ENV") != "production"
    
    print(f"서버 시작: http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
