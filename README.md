# 현대홈쇼핑 방송편성표 크롤러

매 1시간마다 현대홈쇼핑(H.mall) 방송편성표를 자동으로 수집해 Google Sheets에 저장합니다.

## 📁 파일 구조

```
현대홈쇼핑/
├── hmall_crawler.py           ← 메인 크롤러 스크립트
├── requirements.txt           ← 패키지 목록
├── service_account.json       ← (로컬 전용) Google 서비스 계정 키
├── hmall_schedule.csv         ← 크롤링 결과 백업
└── .github/
    └── workflows/
        └── crawl.yml          ← GitHub Actions 자동화 설정
```

---

## 🚀 설정 방법

### 1단계 — Google 서비스 계정 준비

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 생성 → **API 및 서비스 > 라이브러리**
3. **Google Sheets API** & **Google Drive API** 활성화
4. **API 및 서비스 > 사용자 인증 정보 > 서비스 계정 만들기**
5. 서비스 계정 생성 후 **키 추가 > JSON** 다운로드 → `service_account.json`으로 저장
6. 서비스 계정 이메일(예: `xxx@yyy.iam.gserviceaccount.com`)을 **Google Sheets에 편집자로 공유**

### 2단계 — Google Sheets URL 설정

`hmall_crawler.py` 상단의 설정 변경:

```python
SPREADSHEET_ID = "여기에_시트_ID_입력"  # URL의 /d/와 /edit 사이 값
SHEET_NAME = "편성"                      # 저장할 탭 이름
```

### 3단계 — 로컬 테스트

```bash
# service_account.json을 이 폴더에 넣은 후:
python hmall_crawler.py
```

---

## 🤖 GitHub Actions 자동화 설정

### 1. 이 폴더를 GitHub 저장소로 업로드

```bash
git init
git add .
git commit -m "초기 커밋"
git remote add origin https://github.com/[유저명]/[저장소명].git
git push -u origin main
```

> ⚠️ `service_account.json`은 절대 GitHub에 올리면 안 됩니다!  
> `.gitignore` 파일에 이미 추가되어 있습니다.

### 2. GitHub Secret 등록

GitHub 저장소 → **Settings > Secrets and variables > Actions > New repository secret**

| Secret 이름 | 값 |
|-------------|-----|
| `GOOGLE_CREDENTIALS` | `service_account.json` 파일의 **전체 내용** (JSON 텍스트) |

### 3. 자동 실행 확인

저장소 → **Actions 탭** → `현대홈쇼핑 편성표 크롤링` 워크플로우 확인

- ⏰ 매 시간 정각(한국 기준 매 시간)에 자동 실행
- 🔧 **Run workflow** 버튼으로 수동 실행도 가능

---

## 📋 수집 데이터

| 컬럼 | 설명 |
|------|------|
| 날짜 | 방송 날짜 (오늘, 22 일, 23 월 ...) |
| 방송시간 | 예: `10:00 ~ 11:00` |
| 상품코드 | Hmall 상품 고유 코드 |
| 상품명 | 방송 상품명 |
