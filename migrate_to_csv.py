"""
JSON 데이터를 CSV 파일로 변환하는 스크립트
기존 data.json을 expenses_data.csv로 변환합니다.
"""
import json
import csv
from pathlib import Path

JSON_PATH = Path("data.json")
CSV_PATH = Path("expenses_data.csv")

def migrate():
    """JSON 데이터를 CSV로 마이그레이션"""
    if not JSON_PATH.exists():
        print(f"경고: {JSON_PATH} 파일이 없습니다.")
        # 빈 CSV 파일 생성
        with open(CSV_PATH, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['학원', '금액', '승인 날짜', '거래처', '결제 주기'])
            writer.writeheader()
        print(f"빈 CSV 파일 {CSV_PATH}를 생성했습니다.")
        return
    
    print(f"{JSON_PATH}에서 데이터를 읽는 중...")
    
    # JSON 파일 읽기
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ JSON 파일 읽기 실패: {e}")
        return
    
    expenses = data.get("expenses", [])
    
    if not expenses:
        print("지출 데이터가 없습니다.")
        # 빈 CSV 파일 생성
        with open(CSV_PATH, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['학원', '금액', '승인 날짜', '거래처', '결제 주기'])
            writer.writeheader()
        print(f"빈 CSV 파일 {CSV_PATH}를 생성했습니다.")
        return
    
    # 날짜순으로 정렬
    expenses = sorted(expenses, key=lambda x: x.get("approval_date", ""))
    
    # CSV 파일로 저장
    with open(CSV_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['학원', '금액', '승인 날짜', '거래처', '결제 주기']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
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
    
    print(f"✅ 마이그레이션 완료!")
    print(f"  - 지출 내역: {len(expenses)}건")
    print(f"  - 데이터가 {CSV_PATH}에 저장되었습니다.")
    print(f"\n참고: 원본 {JSON_PATH} 파일은 백업으로 유지됩니다.")
    print(f"      필요하시면 나중에 삭제하셔도 됩니다.")

if __name__ == "__main__":
    migrate()

