# 가계부 (Expense Tracker)

지출을 관리하고 통계를 확인할 수 있는 간단한 웹 애플리케이션입니다.

## 실행

```bash
cd "/Users/abenu/Downloads/Forecast/LearningData/Expense_Tracker"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

브라우저에서 `http://127.0.0.1:5056` 로 접속하세요.

## 기능

- 지출 추가/수정/삭제
- CSV 파일 업로드 및 데이터 임포트
- 거래처별, 지불처별, 결제주기별 통계
- 총 지출액 조회

## 데이터 항목

- **거래처**: 지출이 발생한 곳 (예: 학원명)
- **금액**: 지출 금액
- **승인날짜**: 지출이 승인된 날짜
- **지불처**: 결제 수단 (예: 신한카드, 신한은행 등)
- **결제주기**: 결제 주기 (1M, 3M, 6M, 1Y 등)

## CSV 파일 형식

CSV 파일은 다음 형식을 따라야 합니다:

```csv
학원,금액,승인 날짜,거래처,결제 주기
기파랑,"220,000",25/05/28,신한카드,3M
김영아,"340,000",25/05/26,신한카드,3M
```

- 날짜 형식: `YY/MM/DD` (예: `25/05/28` → `2025-05-28`)
- 금액 형식: 콤마 포함 문자열 (예: `"220,000"`)

## 프로젝트 구조

- `app.py`: Flask 애플리케이션 메인 파일
- `templates/index.html`: 메인 페이지 템플릿
- `static/app.js`: 프론트엔드 JavaScript
- `static/style.css`: 스타일시트
- `expense_tracker.db`: SQLite 데이터베이스 (자동 생성)
