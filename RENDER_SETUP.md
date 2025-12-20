# Render 배포 가이드

## 데이터 저장 구조

### 현재 상태

현재 코드는 **CSV 파일**을 기본 저장소로 사용합니다:

1. **로컬 환경**: 
   - `expenses_data.csv`: 지출 데이터 (Git에 포함, 기본 저장소)
   - `data.json`: 캐시 및 거래처 정보 (자동 생성, Git 제외)
2. **Render 환경**: 
   - `DATA_DIR` 환경 변수가 설정되지 않으면: 프로젝트 폴더에 저장 (재배포 시 초기화됨)
   - `DATA_DIR` 환경 변수가 설정되면: 해당 경로에 저장 (Render Disk 사용 시 영구 저장)

### ✅ DB 설정 불필요

**별도의 데이터베이스 설정이 필요 없습니다!** CSV 파일 기반으로 동작하므로:
- PostgreSQL, MySQL 등 외부 DB 설정 불필요
- SQLite 설정 불필요
- 데이터베이스 드라이버 설치 불필요
- **CSV 파일은 Git에 포함되어 자동 백업됨!**

### Render에서 데이터 영구 저장하기

#### 방법 1: Render Disk 사용 (권장, 유료)

1. **Render Disk 생성**:
   - Render 대시보드 → Web Service → Disks 탭
   - "Create Disk" 클릭
   - 이름: `expense-data`
   - 크기: 최소 1GB
   - 마운트 경로: `/opt/render/project/src`

2. **환경 변수 설정**:
   - Environment 탭에서 추가:
     ```
     DATA_DIR=/opt/render/project/src
     ```

3. **재배포**: 
   - 변경사항이 적용되도록 서비스를 재배포합니다.

#### 방법 2: CSV 파일 Git 포함 (무료 플랜, 권장! ⭐)

**가장 간단하고 효과적인 방법입니다!**

1. **GitHub에 expenses_data.csv 커밋**:
   ```bash
   git add expenses_data.csv
   git commit -m "Add expenses data CSV"
   git push
   ```
   - CSV 파일은 Git에 포함되어 자동으로 백업됩니다
   - 재배포 시 GitHub에서 자동으로 복원됩니다
   - 새로운 데이터 입력 시 CSV 파일이 자동으로 업데이트됩니다

2. **재배포**:
   - GitHub에 `expenses_data.csv`가 있으면 자동으로 불러옵니다!
   - 새로운 데이터 입력 시 CSV 파일이 자동으로 업데이트됩니다
   - **Render 무료 플랜**: 재배포 시 CSV가 초기화되지만, GitHub에서 자동으로 복원됩니다

**✅ 데이터 유지 방식**
- ✅ **초기 데이터**: GitHub의 `expenses_data.csv`에서 자동 로드
- ✅ **이후 입력 데이터**: 로컬 CSV에 저장되고, **GitHub에 커밋하면 영구 보존**
- 💡 **권장 워크플로우**:
  1. 데이터 입력/수정/삭제 → 로컬 CSV 자동 업데이트
  2. 주기적으로 GitHub에 커밋: `git add expenses_data.csv && git commit -m "Update data" && git push`
  3. 재배포 시 GitHub에서 자동으로 최신 데이터 복원

**장점**:
- ✅ 무료 플랜에서도 데이터 영구 보존
- ✅ 재배포 시 자동으로 데이터 복원
- ✅ 버전 관리 가능 (Git 히스토리)
- ✅ 별도의 백업 작업 불필요

#### 방법 3: 정기 백업 (수동)

수동으로 백업하고 싶은 경우:

1. **정기적으로 CSV 내보내기**:
   ```bash
   python export_to_csv.py
   ```

2. **GitHub에 백업 파일 저장**:
   - `expenses_export.csv` 파일을 GitHub에 커밋
   - 또는 별도의 백업 저장소에 저장

3. **재배포 후 복원**:
   - Render 웹사이트에서 CSV 가져오기 기능 사용

#### 방법 4: 외부 스토리지 서비스 사용 (선택사항)

JSON 파일 대신 외부 스토리지를 사용하고 싶다면:
- AWS S3, Google Cloud Storage 등에 JSON 파일 저장
- 또는 PostgreSQL, MySQL 등 데이터베이스로 마이그레이션

**참고**: 현재는 JSON 파일만으로도 충분히 동작합니다.

## 현재 저장 구조 확인

현재 코드는 다음 경로에 데이터를 저장합니다:

```python
# app.py에서
DATA_DIR = os.environ.get('DATA_DIR', str(APP_DIR))
CSV_DATA_PATH = Path(DATA_DIR) / "expenses_data.csv"  # 기본 저장소
JSON_DATA_PATH = Path(DATA_DIR) / "data.json"  # 캐시용
```

- **로컬**: `./expenses_data.csv` (Git에 포함)
- **Render (기본)**: `/opt/render/project/src/expenses_data.csv` (재배포 시 GitHub에서 복원)
- **Render (Disk 사용)**: `/opt/render/project/src/expenses_data.csv` (영구 저장)

## 데이터가 사라지는 경우

다음 상황에서 데이터가 초기화될 수 있습니다:

1. **재배포**: Render 무료 플랜에서 재배포 시
2. **서비스 재시작**: 일시적인 재시작은 데이터를 유지하지만, 완전한 재배포는 초기화될 수 있음
3. **디스크 공간 부족**: Render가 임시 파일을 정리할 때

## 권장 사항

1. **정기 백업**: `export_to_csv.py`를 주기적으로 실행하여 CSV로 백업
2. **Render Disk 사용**: 유료 플랜을 사용할 수 있다면 Render Disk 사용
3. **GitHub 백업**: CSV 파일을 GitHub에 커밋하여 버전 관리
