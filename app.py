from __future__ import annotations

import csv
import json
import threading
import urllib.request
import urllib.error
import base64
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from functools import wraps

# 기본 디렉토리
APP_DIR = Path(__file__).parent.absolute()

# Render Disk 경로 설정 (환경 변수로 제어)
import os
DATA_DIR = os.environ.get('DATA_DIR', str(APP_DIR))
JSON_DATA_PATH = Path(DATA_DIR) / "data.json"  # 캐시용
CSV_DATA_PATH = Path(DATA_DIR) / "expenses_data.csv"  # 기본 저장소
PAYEES_CSV_PATH = Path(DATA_DIR) / "payees_data.csv"  # 거래처 저장소

# 파일 접근 동기화를 위한 락
_data_lock = threading.Lock()

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


def _load_from_github() -> Optional[Dict[str, Any]]:
    """GitHub 저장소에서 data.json 파일을 가져오기 (공개/비공개 저장소 지원)"""
    github_repo = os.environ.get('GITHUB_REPO')
    if not github_repo:
        return None
    
    try:
        # GitHub raw URL 형식: https://raw.githubusercontent.com/{owner}/{repo}/{branch}/data.json
        # 환경 변수에서 전체 URL 또는 owner/repo 형식 지원
        if github_repo.startswith('http'):
            url = f"{github_repo.rstrip('/')}/data.json"
        else:
            # owner/repo 형식인 경우
            branch = os.environ.get('GITHUB_BRANCH', 'main')
            url = f"https://raw.githubusercontent.com/{github_repo}/{branch}/data.json"
        
        print(f"GitHub에서 데이터 로드 시도: {url}")
        
        # 비공개 저장소를 위한 인증 헤더 (선택사항)
        headers = {}
        github_token = os.environ.get('GITHUB_TOKEN')
        if github_token:
            # GitHub API를 통한 접근 (비공개 저장소용)
            # raw.githubusercontent.com은 비공개 저장소에서 인증이 필요할 수 있음
            # 대신 GitHub API 사용
            if not github_repo.startswith('http'):
                # owner/repo 형식인 경우 API 사용
                api_url = f"https://api.github.com/repos/{github_repo}/contents/data.json"
                if branch != 'main':
                    api_url += f"?ref={branch}"
                
                req = urllib.request.Request(api_url, headers={'Authorization': f'token {github_token}'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    api_data = json.loads(response.read().decode('utf-8'))
                    # Base64 디코딩
                    content = base64.b64decode(api_data['content']).decode('utf-8')
                    data = json.loads(content)
                    print(f"GitHub API를 통해 데이터 로드 성공: {len(data.get('expenses', []))}건의 지출, {len(data.get('payees', []))}건의 거래처")
                    return data
        
        # 공개 저장소 또는 토큰이 없는 경우 일반 raw URL 사용
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"GitHub에서 데이터 로드 성공: {len(data.get('expenses', []))}건의 지출, {len(data.get('payees', []))}건의 거래처")
            return data
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, Exception) as e:
        print(f"GitHub에서 데이터 로드 실패: {e}")
        return None


def _load_from_csv() -> Optional[Dict[str, Any]]:
    """CSV 파일에서 데이터 로드"""
    if not CSV_DATA_PATH.exists():
        return None
    
    try:
        expenses = []
        
        # 먼저 JSON에서 ID 매핑 정보 가져오기 (있는 경우)
        id_mapping = {}  # (merchant, amount, approval_date) -> id
        next_expense_id = 1
        if JSON_DATA_PATH.exists():
            try:
                with open(JSON_DATA_PATH, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                    for exp in json_data.get("expenses", []):
                        key = (exp.get("merchant"), exp.get("amount"), exp.get("approval_date"))
                        id_mapping[key] = exp.get("id", 0)
                    next_expense_id = json_data.get("next_expense_id", 1)
            except:
                pass
        
        with open(CSV_DATA_PATH, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                merchant = row.get("학원", "").strip()
                amount_str = row.get("금액", "").strip()
                approval_date_str = row.get("승인 날짜", "").strip()
                payment_method = row.get("거래처", "").strip()
                payment_cycle = row.get("결제 주기", "").strip()
                
                if not merchant or not approval_date_str:
                    continue
                
                amount = _parse_amount(amount_str)
                approval_date = _parse_date(approval_date_str)
                
                if not approval_date:
                    continue
                
                # ID는 JSON에서 가져오거나, 없으면 새로 부여
                key = (merchant, amount, approval_date)
                expense_id = id_mapping.get(key, next_expense_id)
                if expense_id >= next_expense_id:
                    next_expense_id = expense_id + 1
                
                expense = {
                    "id": expense_id,
                    "merchant": merchant,
                    "amount": amount,
                    "approval_date": approval_date,
                    "payment_method": payment_method,
                    "payment_cycle": payment_cycle,
                    "created_at": _get_current_time(),
                    "updated_at": _get_current_time()
                }
                expenses.append(expense)
        
        # CSV에서 payees 로드 (거래처는 CSV에 저장)
        payees = []
        next_payee_id = 1
        
        # 먼저 JSON에서 ID 매핑 정보 가져오기 (있는 경우)
        payee_id_mapping = {}  # (name, bank_name, account_number, owner_name) -> id
        if JSON_DATA_PATH.exists():
            try:
                with open(JSON_DATA_PATH, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                    for payee in json_data.get("payees", []):
                        key = (
                            payee.get("name"),
                            payee.get("bank_name"),
                            payee.get("account_number"),
                            payee.get("owner_name")
                        )
                        payee_id_mapping[key] = payee.get("id", 0)
                    next_payee_id = json_data.get("next_payee_id", 1)
            except:
                pass
        
        # CSV에서 거래처 로드
        if PAYEES_CSV_PATH.exists():
            try:
                with open(PAYEES_CSV_PATH, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        name = row.get("거래처명", "").strip()
                        bank_name = row.get("은행명", "").strip()
                        account_number = row.get("계좌번호", "").strip()
                        owner_name = row.get("예금주", "").strip()
                        payment_cycle = row.get("결제 주기", "").strip()
                        amount_str = row.get("금액", "").strip()
                        payee_id_str = row.get("ID", "").strip()
                        
                        if not name or not owner_name:
                            continue
                        
                        # 금액 파싱
                        amount = _parse_amount(amount_str) if amount_str else 0
                        
                        # ID는 CSV에서 가져오거나, JSON 매핑에서 가져오거나, 없으면 새로 부여
                        try:
                            payee_id = int(payee_id_str) if payee_id_str else 0
                        except ValueError:
                            payee_id = 0
                        
                        if payee_id == 0:
                            key = (name, bank_name, account_number, owner_name)
                            payee_id = payee_id_mapping.get(key, next_payee_id)
                            if payee_id >= next_payee_id:
                                next_payee_id = payee_id + 1
                        
                        payee = {
                            "id": payee_id,
                            "name": name,
                            "bank_name": bank_name,
                            "account_number": account_number,
                            "owner_name": owner_name,
                            "payment_cycle": payment_cycle,
                            "amount": amount,
                            "created_at": _get_current_time(),
                            "updated_at": _get_current_time()
                        }
                        payees.append(payee)
            except Exception as e:
                print(f"거래처 CSV 파일 로드 실패: {e}")
        
        # CSV에 거래처가 없으면 JSON에서 로드 시도
        if not payees and JSON_DATA_PATH.exists():
            try:
                with open(JSON_DATA_PATH, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                    payees = json_data.get("payees", [])
                    next_payee_id = json_data.get("next_payee_id", len(payees) + 1)
            except:
                pass
        
        return {
            "expenses": expenses,
            "payees": payees,
            "next_expense_id": next_expense_id,
            "next_payee_id": next_payee_id
        }
    except Exception as e:
        print(f"CSV 파일 로드 실패: {e}")
        return None


def _load_data() -> Dict[str, Any]:
    """CSV 파일에서 데이터 로드 (우선순위: CSV > JSON > GitHub)"""
    CSV_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. CSV 파일에서 로드 시도
    csv_data = _load_from_csv()
    if csv_data:
        print(f"CSV에서 데이터 로드 성공: {len(csv_data.get('expenses', []))}건의 지출")
        # JSON 캐시도 업데이트
        _save_data_to_json(csv_data)
        return csv_data
    
    # 2. JSON 파일에서 로드 시도
    if JSON_DATA_PATH.exists():
        try:
            with open(JSON_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"JSON에서 데이터 로드 성공: {len(data.get('expenses', []))}건의 지출")
                # CSV로 변환하여 저장
                _save_data_to_csv(data)
                return data
        except (json.JSONDecodeError, IOError):
            print(f"JSON 파일 손상, GitHub에서 로드 시도...")
    
    # 3. GitHub에서 가져오기 시도
    github_data = _load_from_github()
    if github_data:
        _save_data(github_data)
        return github_data
    
    # 4. 모두 실패하면 초기 데이터 생성
    print("데이터 파일이 없어 초기 데이터 생성")
    initial_data = {
        "expenses": [],
        "payees": [
            # 거래처 초기 데이터 (코드에서 직접 수정 가능)
            # 형식: {"id": 1, "name": "거래처명", "bank_name": "은행명", "account_number": "계좌번호", "owner_name": "예금주", "payment_cycle": "결제주기", "amount": 금액, "created_at": "...", "updated_at": "..."}
            # 예시:
            # {"id": 1, "name": "C&C 미술", "bank_name": "카드", "account_number": "", "owner_name": "C&C", "payment_cycle": "1M", "amount": 180000, "created_at": _get_current_time(), "updated_at": _get_current_time()},
            # {"id": 2, "name": "김영아", "bank_name": "카드", "account_number": "", "owner_name": "김영아", "payment_cycle": "1M", "amount": 390000, "created_at": _get_current_time(), "updated_at": _get_current_time()},
            # {"id": 3, "name": "농구", "bank_name": "우리은행", "account_number": "1002429296789", "owner_name": "이기범", "payment_cycle": "3M", "amount": 282000, "created_at": _get_current_time(), "updated_at": _get_current_time()},
            # {"id": 4, "name": "늘품재논술", "bank_name": "국민은행", "account_number": "47580102612761", "owner_name": "김현아", "payment_cycle": "1M", "amount": 184000, "created_at": _get_current_time(), "updated_at": _get_current_time()},
            # {"id": 5, "name": "세차", "bank_name": "국민은행", "account_number": "40880101094704", "owner_name": "김란향", "payment_cycle": "1M", "amount": 60000, "created_at": _get_current_time(), "updated_at": _get_current_time()},
            # {"id": 6, "name": "영어과외", "bank_name": "농협", "account_number": "61309851008901", "owner_name": "박채원", "payment_cycle": "1M", "amount": 240000, "created_at": _get_current_time(), "updated_at": _get_current_time()},
            # {"id": 7, "name": "하연과학", "bank_name": "농협", "account_number": "3561340828353", "owner_name": "허기진", "payment_cycle": "1M", "amount": 100000, "created_at": _get_current_time(), "updated_at": _get_current_time()},
        ],
        "next_expense_id": 1,
        "next_payee_id": 8  # 초기 거래처가 7개이므로 다음 ID는 8
    }
    _save_data(initial_data)
    return initial_data


def _save_data_to_csv(data: Dict[str, Any]) -> None:
    """데이터를 CSV 파일에 저장"""
    CSV_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    expenses = data.get("expenses", [])
    if not expenses:
        # 빈 CSV 파일 생성
        with open(CSV_DATA_PATH, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['학원', '금액', '승인 날짜', '거래처', '결제 주기'])
            writer.writeheader()
        return
    
    # 날짜순으로 정렬
    expenses = sorted(expenses, key=lambda x: x.get("approval_date", ""))
    
    # 임시 파일에 먼저 저장 후 원자적으로 교체
    temp_path = CSV_DATA_PATH.with_suffix('.csv.tmp')
    with open(temp_path, 'w', newline='', encoding='utf-8-sig') as f:
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
    
    # 원자적으로 교체
    temp_path.replace(CSV_DATA_PATH)


def _save_payees_to_csv(data: Dict[str, Any]) -> None:
    """거래처 데이터를 CSV 파일에 저장"""
    PAYEES_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    payees = data.get("payees", [])
    
    # 임시 파일에 먼저 저장 후 원자적으로 교체
    temp_path = PAYEES_CSV_PATH.with_suffix('.csv.tmp')
    with open(temp_path, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['ID', '거래처명', '은행명', '계좌번호', '예금주', '결제 주기', '금액']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # 거래처명 순으로 정렬
        sorted_payees = sorted(payees, key=lambda x: x.get("name", ""))
        
        for payee in sorted_payees:
            # 금액 포맷팅 (콤마 포함)
            amount = payee.get('amount', 0)
            amount_str = f"{int(amount):,}" if amount else ""
            
            writer.writerow({
                'ID': payee.get('id', ''),
                '거래처명': payee.get('name', ''),
                '은행명': payee.get('bank_name', ''),
                '계좌번호': payee.get('account_number', ''),
                '예금주': payee.get('owner_name', ''),
                '결제 주기': payee.get('payment_cycle', ''),
                '금액': amount_str
            })
    
    # 원자적으로 교체
    temp_path.replace(PAYEES_CSV_PATH)


def _save_data_to_json(data: Dict[str, Any]) -> None:
    """데이터를 JSON 파일에 저장 (캐시용)"""
    JSON_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 임시 파일에 먼저 저장 후 원자적으로 교체
    temp_path = JSON_DATA_PATH.with_suffix('.json.tmp')
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 원자적으로 교체
    temp_path.replace(JSON_DATA_PATH)


def _save_data(data: Dict[str, Any]) -> None:
    """데이터를 CSV와 JSON 파일에 저장"""
    _save_data_to_csv(data)  # 지출 CSV가 기본 저장소
    _save_payees_to_csv(data)  # 거래처 CSV 저장
    _save_data_to_json(data)  # JSON은 캐시용


def _get_current_time() -> str:
    """현재 시간을 문자열로 반환"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _init_data() -> None:
    """데이터 초기화 (JSON 파일이 없으면 생성)"""
    with _data_lock:
        _load_data()


@app.get("/api/payees")
def list_payees():
    """거래처 목록 조회"""
    with _data_lock:
        data = _load_data()
        payees = sorted(data.get("payees", []), key=lambda x: x.get("name", ""))
        payees = [
            {
                "id": p["id"],
                "name": p["name"],
                "account_number": p.get("account_number", ""),
                "bank_name": p.get("bank_name", ""),
                "owner_name": p.get("owner_name", ""),
                "payment_cycle": p.get("payment_cycle", ""),
                "amount": p.get("amount", 0),
            }
            for p in payees
        ]
    return jsonify({"payees": payees})


@app.post("/api/payees")
def create_payee():
    """거래처 추가"""
    payload = request.get_json(force=True) or {}
    name = payload.get("name", "").strip()
    account_number = payload.get("account_number", "").strip()
    bank_name = payload.get("bank_name", "").strip()
    owner_name = payload.get("owner_name", "").strip()
    payment_cycle = payload.get("payment_cycle", "").strip()

    if not name or not owner_name or not payment_cycle:
        return jsonify({"error": "필수 항목이 누락되었습니다."}), 400

    with _data_lock:
        data = _load_data()
        payee_id = data.get("next_payee_id", 1)
        payee = {
            "id": payee_id,
            "name": name,
            "account_number": account_number,
            "bank_name": bank_name,
            "owner_name": owner_name,
            "payment_cycle": payment_cycle,
            "created_at": _get_current_time(),
            "updated_at": _get_current_time()
        }
        data.setdefault("payees", []).append(payee)
        data["next_payee_id"] = payee_id + 1
        _save_data(data)
    return jsonify({"ok": True})


@app.put("/api/payees/<int:payee_id>")
def update_payee(payee_id: int):
    """거래처 수정"""
    payload = request.get_json(force=True) or {}
    name = payload.get("name", "").strip()
    account_number = payload.get("account_number", "").strip()
    bank_name = payload.get("bank_name", "").strip()
    owner_name = payload.get("owner_name", "").strip()
    payment_cycle = payload.get("payment_cycle", "").strip()

    if not name or not owner_name or not payment_cycle:
        return jsonify({"error": "필수 항목이 누락되었습니다."}), 400

    with _data_lock:
        data = _load_data()
        payees = data.get("payees", [])
        payee = next((p for p in payees if p.get("id") == payee_id), None)
        
        if not payee:
            return jsonify({"error": "거래처를 찾을 수 없습니다."}), 404
        
        payee["name"] = name
        payee["account_number"] = account_number
        payee["bank_name"] = bank_name
        payee["owner_name"] = owner_name
        payee["payment_cycle"] = payment_cycle
        payee["updated_at"] = _get_current_time()
        _save_data(data)
    return jsonify({"ok": True})


@app.delete("/api/payees/<int:payee_id>")
def delete_payee(payee_id: int):
    """거래처 삭제"""
    with _data_lock:
        data = _load_data()
        payees = data.get("payees", [])
        data["payees"] = [p for p in payees if p.get("id") != payee_id]
        _save_data(data)
    return jsonify({"ok": True})


def _parse_amount(amount_input: Union[str, float, int]) -> float:
    """금액을 float로 변환 (콤마 제거, 숫자/문자열 모두 처리)"""
    if amount_input is None:
        return 0.0
    
    # 이미 숫자인 경우
    if isinstance(amount_input, (int, float)):
        return float(amount_input)
    
    # 문자열인 경우
    if not isinstance(amount_input, str):
        amount_str = str(amount_input)
    else:
        amount_str = amount_input.strip()
    
    if not amount_str:
        return 0.0
    
    try:
        # 콤마와 공백 제거 후 변환
        cleaned = amount_str.replace(",", "").replace(" ", "").replace("원", "")
        return float(cleaned)
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
def list_expenses():
    """지출 목록 조회"""
    with _data_lock:
        data = _load_data()
        expenses = sorted(
            data.get("expenses", []),
            key=lambda x: (x.get("approval_date", ""), x.get("id", 0)),
            reverse=True
        )
        expenses = [
            {
                "id": e["id"],
                "merchant": e["merchant"],
                "amount": e["amount"],
                "approval_date": e["approval_date"],
                "payment_method": e["payment_method"],
                "payment_cycle": e["payment_cycle"],
            }
            for e in expenses
        ]
    return jsonify({"expenses": expenses})


@app.post("/api/expenses")
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
    
    with _data_lock:
        data = _load_data()
        expense_id = data.get("next_expense_id", 1)
        expense = {
            "id": expense_id,
            "merchant": merchant,
            "amount": amount,
            "approval_date": approval_date,
            "payment_method": payment_method,
            "payment_cycle": payment_cycle,
            "created_at": _get_current_time(),
            "updated_at": _get_current_time()
        }
        data.setdefault("expenses", []).append(expense)
        data["next_expense_id"] = expense_id + 1
        _save_data(data)
    
    return jsonify({
        "expense": {
            "id": expense["id"],
            "merchant": expense["merchant"],
            "amount": expense["amount"],
            "approval_date": expense["approval_date"],
            "payment_method": expense["payment_method"],
            "payment_cycle": expense["payment_cycle"],
        }
    })


@app.put("/api/expenses/<int:expense_id>")
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
    
    with _data_lock:
        data = _load_data()
        expenses = data.get("expenses", [])
        expense = next((e for e in expenses if e.get("id") == expense_id), None)
        
        if not expense:
            return jsonify({"error": "지출을 찾을 수 없습니다."}), 404
        
        expense["merchant"] = merchant
        expense["amount"] = amount
        expense["approval_date"] = approval_date
        expense["payment_method"] = payment_method
        expense["payment_cycle"] = payment_cycle
        expense["updated_at"] = _get_current_time()
        _save_data(data)
    
    return jsonify({
        "expense": {
            "id": expense["id"],
            "merchant": expense["merchant"],
            "amount": expense["amount"],
            "approval_date": expense["approval_date"],
            "payment_method": expense["payment_method"],
            "payment_cycle": expense["payment_cycle"],
        }
    })


@app.delete("/api/expenses/<int:expense_id>")
def delete_expense(expense_id: int):
    """지출 삭제"""
    with _data_lock:
        data = _load_data()
        expenses = data.get("expenses", [])
        data["expenses"] = [e for e in expenses if e.get("id") != expense_id]
        _save_data(data)
    return jsonify({"ok": True})


@app.post("/api/import/csv")
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
        
        with _data_lock:
            data = _load_data()
            expenses = data.get("expenses", [])
            next_id = data.get("next_expense_id", 1)
            
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
                    existing = next(
                        (e for e in expenses if e.get("merchant") == merchant and 
                         e.get("amount") == amount and e.get("approval_date") == approval_date),
                        None
                    )
                    
                    if existing:
                        continue
                    
                    expense = {
                        "id": next_id,
                        "merchant": merchant,
                        "amount": amount,
                        "approval_date": approval_date,
                        "payment_method": payment_method,
                        "payment_cycle": payment_cycle,
                        "created_at": _get_current_time(),
                        "updated_at": _get_current_time()
                    }
                    expenses.append(expense)
                    next_id += 1
                    inserted += 1
                except Exception as e:
                    errors.append(f"{idx}행: {str(e)}")
            
            data["expenses"] = expenses
            data["next_expense_id"] = next_id
            _save_data(data)
        
        return jsonify({
            "inserted": inserted,
            "errors": errors,
        })
    except Exception as e:
        return jsonify({"error": f"CSV 업로드 중 오류가 발생했습니다: {str(e)}"}), 500


@app.get("/api/statistics")
def get_statistics():
    """통계 정보 조회"""
    with _data_lock:
        data = _load_data()
        expenses = data.get("expenses", [])
        
        # 총 지출액
        total_amount = sum(e.get("amount", 0) for e in expenses)
        
        # 거래처별 합계
        merchant_totals_dict = {}
        for e in expenses:
            merchant = e.get("merchant", "")
            amount = e.get("amount", 0)
            merchant_totals_dict[merchant] = merchant_totals_dict.get(merchant, 0) + amount
        merchant_totals = [
            {"merchant": k, "total": v}
            for k, v in sorted(merchant_totals_dict.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # 지불처별 합계
        payment_totals_dict = {}
        for e in expenses:
            payment_method = e.get("payment_method", "")
            amount = e.get("amount", 0)
            payment_totals_dict[payment_method] = payment_totals_dict.get(payment_method, 0) + amount
        payment_totals = [
            {"payment_method": k, "total": v}
            for k, v in sorted(payment_totals_dict.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # 결제 주기별 합계
        cycle_totals_dict = {}
        for e in expenses:
            payment_cycle = e.get("payment_cycle", "")
            amount = e.get("amount", 0)
            cycle_totals_dict[payment_cycle] = cycle_totals_dict.get(payment_cycle, 0) + amount
        cycle_totals = [
            {"payment_cycle": k, "total": v}
            for k, v in sorted(cycle_totals_dict.items(), key=lambda x: x[1], reverse=True)
        ]
    
    return jsonify({
        "total_amount": total_amount,
        "merchant_totals": merchant_totals,
        "payment_totals": payment_totals,
        "cycle_totals": cycle_totals,
    })


@app.get("/api/expenses/by-date")
def get_expenses_by_date():
    """날짜별 지출 조회"""
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "date 파라미터가 필요합니다."}), 400
    
    with _data_lock:
        data = _load_data()
        expenses = [
            e for e in data.get("expenses", [])
            if e.get("approval_date") == date_str
        ]
        expenses = sorted(expenses, key=lambda x: x.get("id", 0), reverse=True)
        expenses = [
            {
                "id": e["id"],
                "merchant": e["merchant"],
                "amount": e["amount"],
                "approval_date": e["approval_date"],
                "payment_method": e["payment_method"],
                "payment_cycle": e["payment_cycle"],
            }
            for e in expenses
        ]
    return jsonify({"expenses": expenses})


def _calculate_next_payment_date(last_date_str: str, payment_cycle: str) -> str:
    """마지막 결제일과 결제주기를 기반으로 다음 결제일 계산"""
    if not last_date_str or not payment_cycle:
        return ""
    
    try:
        from datetime import datetime
        from calendar import monthrange
        
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
        
        def get_valid_day(year, month, day):
            """해당 월의 유효한 날짜 반환"""
            max_day = monthrange(year, month)[1]
            return min(day, max_day)
        
        if payment_cycle == "1M":
            # 1개월 후
            if last_date.month == 12:
                year = last_date.year + 1
                month = 1
            else:
                year = last_date.year
                month = last_date.month + 1
            day = get_valid_day(year, month, last_date.day)
            next_date = datetime(year, month, day)
        elif payment_cycle == "3M":
            # 3개월 후
            months_to_add = 3
            year = last_date.year
            month = last_date.month + months_to_add
            while month > 12:
                month -= 12
                year += 1
            day = get_valid_day(year, month, last_date.day)
            next_date = datetime(year, month, day)
        elif payment_cycle == "6M":
            # 6개월 후
            months_to_add = 6
            year = last_date.year
            month = last_date.month + months_to_add
            while month > 12:
                month -= 12
                year += 1
            day = get_valid_day(year, month, last_date.day)
            next_date = datetime(year, month, day)
        elif payment_cycle == "1Y":
            # 1년 후
            year = last_date.year + 1
            day = get_valid_day(year, last_date.month, last_date.day)
            next_date = datetime(year, last_date.month, day)
        else:
            return ""
        
        return next_date.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"다음 결제일 계산 실패: {e}")
        return ""


@app.get("/api/expenses/calendar")
def get_calendar_data():
    """캘린더용 월별 지출 데이터 조회"""
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    
    if not year or not month:
        return jsonify({"error": "year와 month 파라미터가 필요합니다."}), 400
    
    # 해당 월의 시작일과 종료일 계산
    start_date = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{month+1:02d}-01"
    
    with _data_lock:
        data = _load_data()
        expenses = data.get("expenses", [])
        
        # 해당 기간의 지출 필터링
        filtered_expenses = [
            e for e in expenses
            if start_date <= e.get("approval_date", "") < end_date
        ]
        
        # 날짜별로 그룹화
        daily_data = {}
        for e in filtered_expenses:
            date_str = e.get("approval_date", "")
            if date_str not in daily_data:
                daily_data[date_str] = {"total": 0, "count": 0}
            daily_data[date_str]["total"] += e.get("amount", 0)
            daily_data[date_str]["count"] += 1
        
        # 다음 결제일 계산
        # 1. 거래처 테이블에서 거래처명과 결제주기 매핑 생성
        payees = data.get("payees", [])
        payee_cycle_map = {}  # {payee_name: payment_cycle}
        for payee in payees:
            payee_name = payee.get("name", "").strip()
            payment_cycle = payee.get("payment_cycle", "").strip()
            if payee_name and payment_cycle:
                payee_cycle_map[payee_name] = payment_cycle
        
        # 2. 지출 내역에서 거래처별로 마지막 결제일 찾기
        merchant_last_payment = {}  # {merchant: {"date": "YYYY-MM-DD", "cycle": "1M"}}
        for e in expenses:
            merchant = e.get("merchant", "").strip()
            approval_date = e.get("approval_date", "")
            
            if not merchant or not approval_date:
                continue
            
            # 결제주기는 거래처 테이블에서 우선 찾고, 없으면 지출 내역에서 가져오기
            payment_cycle = payee_cycle_map.get(merchant, e.get("payment_cycle", "").strip())
            
            if not payment_cycle:
                continue
            
            if merchant not in merchant_last_payment:
                merchant_last_payment[merchant] = {
                    "date": approval_date,
                    "cycle": payment_cycle
                }
            else:
                # 더 최근 날짜로 업데이트
                if approval_date > merchant_last_payment[merchant]["date"]:
                    merchant_last_payment[merchant] = {
                        "date": approval_date,
                        "cycle": payment_cycle
                    }
        
        # 3. 다음 결제일 계산 및 해당 월에 포함되는지 확인
        # 오늘 날짜와 1주일 전 날짜 계산
        from datetime import datetime, timedelta
        today = datetime.now().date()
        one_week_ago = today - timedelta(days=7)
        today_str = today.strftime("%Y-%m-%d")
        one_week_ago_str = one_week_ago.strftime("%Y-%m-%d")
        
        next_payments = {}  # {date_str: [merchant1, merchant2, ...]}
        for merchant, info in merchant_last_payment.items():
            next_date = _calculate_next_payment_date(info["date"], info["cycle"])
            # 해당 월에 포함되고, 오늘 이후이며, 1주일 이내인 날짜만 표시
            if next_date and start_date <= next_date < end_date:
                # 과거 날짜는 제외
                if next_date < today_str:
                    continue
                # 1주일 이상 지난 날짜는 제외
                if next_date < one_week_ago_str:
                    continue
                if next_date not in next_payments:
                    next_payments[next_date] = []
                next_payments[next_date].append(merchant)
        
        # 4. daily_data에 다음 결제일 정보 추가
        for date_str, merchants in next_payments.items():
            if date_str not in daily_data:
                daily_data[date_str] = {"total": 0, "count": 0}
            daily_data[date_str]["next_payments"] = merchants
    
    return jsonify({"daily_data": daily_data})


@app.get("/api/expenses/search")
def search_expenses():
    """거래처 또는 지불처 검색"""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"expenses": []})
    
    with _data_lock:
        data = _load_data()
        expenses = data.get("expenses", [])
        
        # 검색어가 포함된 지출 필터링
        filtered_expenses = [
            e for e in expenses
            if query.lower() in e.get("merchant", "").lower() or 
               query.lower() in e.get("payment_method", "").lower()
        ]
        
        # 날짜와 ID로 정렬
        filtered_expenses = sorted(
            filtered_expenses,
            key=lambda x: (x.get("approval_date", ""), x.get("id", 0)),
            reverse=True
        )
        
        expenses = [
            {
                "merchant": e["merchant"],
                "approval_date": e["approval_date"],
                "amount": e["amount"],
                "payment_method": e["payment_method"],
            }
            for e in filtered_expenses
        ]
        
    return jsonify({"expenses": expenses})


def main() -> None:
    import os
    _init_data()
    
    # Render는 PORT 환경 변수를 제공합니다
    port = int(os.environ.get("PORT", 5056))
    # 프로덕션 환경에서는 debug=False
    debug = os.environ.get("FLASK_ENV") != "production"
    
    print(f"서버 시작: http://0.0.0.0:{port}")
    print(f"데이터 저장 위치: {JSON_DATA_PATH}")
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
