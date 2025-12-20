#!/usr/bin/env python3
"""JSON 파일의 지출 데이터를 CSV로 내보내기"""

import json
import csv
from pathlib import Path

# 데이터 파일 경로
JSON_PATH = Path(__file__).parent / "data.json"
CSV_PATH = Path(__file__).parent / "expenses_export.csv"

def export_expenses_to_csv():
    """지출 데이터를 CSV 파일로 내보내기"""
    if not JSON_PATH.exists():
        print(f"❌ 데이터 파일을 찾을 수 없습니다: {JSON_PATH}")
        return
    
    # JSON 파일 읽기
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"❌ 데이터 파일을 읽을 수 없습니다: {e}")
        return
    
    expenses = data.get("expenses", [])
    
    if not expenses:
        print("❌ 내보낼 데이터가 없습니다.")
        return
    
    # 날짜순으로 정렬
    expenses = sorted(expenses, key=lambda x: x.get("approval_date", ""))
    
    # CSV 파일로 저장
    with open(CSV_PATH, 'w', newline='', encoding='utf-8-sig') as csvfile:
        # 헤더: 앱의 CSV 업로드 형식에 맞춤
        fieldnames = ['학원', '금액', '승인 날짜', '거래처', '결제 주기']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for expense in expenses:
            # 날짜 형식 변환: YYYY-MM-DD -> YY/MM/DD
            approval_date = expense.get('approval_date', '')
            if approval_date:
                date_parts = approval_date.split('-')
                if len(date_parts) == 3:
                    year = date_parts[0][2:]  # 2025 -> 25
                    month = date_parts[1]
                    day = date_parts[2]
                    formatted_date = f"{year}/{month}/{day}"
                else:
                    formatted_date = approval_date
            else:
                formatted_date = ""
            
            # 금액 포맷팅 (콤마 포함)
            amount = expense.get('amount', 0)
            amount_str = f"{int(amount):,}"
            
            writer.writerow({
                '학원': expense.get('merchant', ''),
                '금액': amount_str,
                '승인 날짜': formatted_date,
                '거래처': expense.get('payment_method', ''),
                '결제 주기': expense.get('payment_cycle', '')
            })
    
    print(f"✅ {len(expenses)}개의 지출 데이터를 CSV로 내보냈습니다.")
    print(f"📁 파일 위치: {CSV_PATH}")
    print(f"\n다음 단계:")
    print(f"1. Render 웹사이트에 로그인")
    print(f"2. 'CSV 가져오기' 버튼 클릭")
    print(f"3. {CSV_PATH.name} 파일을 선택하여 업로드")
    print(f"4. 데이터가 자동으로 임포트됩니다!")

if __name__ == "__main__":
    export_expenses_to_csv()
