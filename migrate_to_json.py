"""
SQLite 데이터베이스를 JSON 파일로 마이그레이션하는 스크립트
기존 데이터를 그대로 유지하면서 JSON 형식으로 변환합니다.
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# 경로 설정
DB_PATH = Path("expense_tracker.db")
JSON_DATA_PATH = Path("data.json")

def migrate():
    """SQLite 데이터를 JSON으로 마이그레이션"""
    if not DB_PATH.exists():
        print(f"경고: {DB_PATH} 파일이 없습니다. 마이그레이션할 데이터가 없습니다.")
        # 빈 JSON 파일 생성
        initial_data = {
            "expenses": [],
            "payees": [],
            "next_expense_id": 1,
            "next_payee_id": 1
        }
        with open(JSON_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=2)
        print(f"빈 데이터 파일 {JSON_DATA_PATH}를 생성했습니다.")
        return
    
    print(f"{DB_PATH}에서 데이터를 읽는 중...")
    
    # SQLite에서 데이터 읽기
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    # expenses 데이터 읽기
    expenses_rows = conn.execute("SELECT * FROM expenses ORDER BY id").fetchall()
    expenses = []
    max_expense_id = 0
    
    for row in expenses_rows:
        expense = {
            "id": row["id"],
            "merchant": row["merchant"],
            "amount": row["amount"],
            "approval_date": row["approval_date"],
            "payment_method": row["payment_method"],
            "payment_cycle": row["payment_cycle"],
            "created_at": row["created_at"] if "created_at" in row.keys() else "",
            "updated_at": row["updated_at"] if "updated_at" in row.keys() else ""
        }
        expenses.append(expense)
        if row["id"] > max_expense_id:
            max_expense_id = row["id"]
    
    # payees 데이터 읽기
    payees_rows = conn.execute("SELECT * FROM payees ORDER BY id").fetchall()
    payees = []
    max_payee_id = 0
    
    for row in payees_rows:
        payee = {
            "id": row["id"],
            "name": row["name"],
            "account_number": row["account_number"],
            "bank_name": row["bank_name"],
            "owner_name": row["owner_name"],
            "created_at": row["created_at"] if "created_at" in row.keys() else "",
            "updated_at": row["updated_at"] if "updated_at" in row.keys() else ""
        }
        payees.append(payee)
        if row["id"] > max_payee_id:
            max_payee_id = row["id"]
    
    conn.close()
    
    # JSON 데이터 구조 생성
    data = {
        "expenses": expenses,
        "payees": payees,
        "next_expense_id": max_expense_id + 1,
        "next_payee_id": max_payee_id + 1
    }
    
    # JSON 파일로 저장
    with open(JSON_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"마이그레이션 완료!")
    print(f"  - 지출 내역: {len(expenses)}건")
    print(f"  - 거래처: {len(payees)}건")
    print(f"  - 데이터가 {JSON_DATA_PATH}에 저장되었습니다.")
    print(f"\n참고: 원본 {DB_PATH} 파일은 백업으로 유지됩니다.")
    print(f"      필요하시면 나중에 삭제하셔도 됩니다.")

if __name__ == "__main__":
    migrate()

