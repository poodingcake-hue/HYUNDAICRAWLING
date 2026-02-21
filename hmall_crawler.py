import asyncio
import csv
import datetime
import os
import json
import gspread
from google.oauth2.service_account import Credentials
import re
from playwright.async_api import async_playwright

# ───────────────────────────────────────────────────
# 설정 영역 (Google Sheets 정보 입력)
# ───────────────────────────────────────────────────
SPREADSHEET_ID = "1NEsimkXycdXQCz4g0cr31j93MGI7HKNDeoiJO4HjgOw"  # 시트 URL의 /d/와 /edit 사이 값
SHEET_NAME = "크롤링"              # 데이터를 저장할 시트 탭 이름
SERVICE_ACCOUNT_FILE = "service_account.json"  # 서비스 계정 JSON 파일 경로
# ───────────────────────────────────────────────────


def get_gspread_client():
    """Google Sheets 클라이언트를 반환합니다."""
    # GitHub Actions에서는 GOOGLE_CREDENTIALS 환경 변수에서 읽음
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/spreadsheets",
            ]
        )
    elif os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/spreadsheets",
            ]
        )
    else:
        raise FileNotFoundError(
            f"서비스 계정 파일({SERVICE_ACCOUNT_FILE})이 없고,\n"
            "GOOGLE_CREDENTIALS 환경 변수도 설정되지 않았습니다.\n"
            "로컬 실행 시 service_account.json 파일을 이 스크립트와 같은 폴더에 놓아주세요."
        )
    
    return gspread.authorize(creds)


def save_to_gsheet(results: list):
    """수집한 데이터를 Google Sheets에 저장합니다."""
    print("📊 Google Sheets 연결 중...")
    client = get_gspread_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=5000, cols=10)

    # 기존 데이터 전체 삭제 후 새로 씀 (항상 최신 상태 유지)
    worksheet.clear()

    updated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    header = ["날짜", "방송시간", "상품코드", "상품명", f"업데이트: {updated_at}"]
    rows = [header]

    for item in results:
        rows.append([
            item["날짜"],
            item["방송시간"],
            item["상품코드"],
            item["상품명"],
        ])

    # 한 번에 업로드 (속도 최적화)
    worksheet.update(rows, "A1")

    print(f"✅ Google Sheets 저장 완료 — {len(results)}개 항목 (탭: {SHEET_NAME})")


async def crawl_hmall() -> list:
    """현대홈쇼핑 방송편성표를 크롤링하여 결과 리스트를 반환합니다."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/16.6 Mobile/15E148 Safari/604.1"
            ),
            viewport={"width": 390, "height": 844},
            is_mobile=True,
        )
        page = await context.new_page()

        # stealth 적용 (봇 감지 우회)
        try:
            from playwright_stealth import Stealth
            await Stealth().apply_stealth_async(page)
        except Exception:
            pass

        url = "https://www.hmall.com/md/dpl/index?mainDispSeq=2&brodType=all"
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 접속 중: {url}")

        try:
            await page.goto(url, wait_until="load", timeout=120000)
            await asyncio.sleep(10)
        except Exception as e:
            print(f"❌ 접속 실패: {e}")
            await browser.close()
            return []

        # ── 날짜 탭 목록 수집 ────────────────────────────
        tab_info = await page.evaluate("""() => {
            let btns = Array.from(document.querySelectorAll('button'));
            return btns
                .filter(b => (b.innerText.includes('오늘') || /\\d+/.test(b.innerText)) && b.innerText.length < 15)
                .map(b => b.innerText.trim());
        }""")

        print(f"📅 발견된 날짜 탭: {len(tab_info)}개")

        # 오늘(또는 첫 번째)부터 시작
        start_idx = next((i for i, t in enumerate(tab_info) if "오늘" in t), 0)
        print(f"'{tab_info[start_idx]}'부터 수집 시작")

        results = []

        for i in range(start_idx, start_idx + 1):  # '오늘' 탭에서 시작하여 무한 스크롤로 전체 수집
            current_day_text = tab_info[i]
            clean_date = current_day_text.replace("\n", " ").strip()
            print(f"\n  📆 {clean_date} 수집 중...")

            # JavaScript로 탭 클릭 (viewport 바깥 요소도 안전하게 처리)
            try:
                button_label = current_day_text.split("\n")[0]
                await page.evaluate("""(label) => {
                    let btns = Array.from(document.querySelectorAll('button'));
                    let target = btns.find(b => b.innerText.includes(label));
                    if (target) target.click();
                }""", button_label)
                await asyncio.sleep(4)
            except Exception as e:
                print(f"  ⚠️ 탭 전환 실패: {e}")
                continue

            # ── 'TV쇼핑' 탭 필터링 추가 ─────────────────────────
            try:
                print(f"  📺 'TV쇼핑' 필터 적용 중...")
                await page.evaluate("""() => {
                    let btns = Array.from(document.querySelectorAll('button, a'));
                    let tvBtn = btns.find(b => b.innerText.trim() === 'TV쇼핑' || b.innerText.includes('TV쇼핑'));
                    if (tvBtn) tvBtn.click();
                }""")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"  ⚠️ 'TV쇼핑' 필터 적용 실패: {e}")

            # ── 스크롤 및 증분 수집 (Virtuoso 대응) ────────────────────
            print("  🔽 모든 상품 증분 수집 중...")
            day_results = {} # { (time, code): item_dict }
            
            last_height = 0
            scroll_count = 0
            stagnant_count = 0
            
            while scroll_count < 200: # 충분히 늘려 편성표 전체(7일치) 수집 보장
                # 현재 보이는 상품 수집
                new_items = await page.evaluate("""() => {
                    let items = [];
                    // data-time 속성이 있는 컨테이너 또는 상품 링크 탐색
                    let containers = Array.from(document.querySelectorAll('[data-time], ._1jauv3p0'));
                    
                    containers.forEach(container => {
                        let broadcastTime = container.getAttribute('data-time') || "";
                        if (broadcastTime && broadcastTime.includes(' ')) {
                            broadcastTime = broadcastTime.split(' ')[1];
                        }
                        
                        // 시간 정보 추출
                        if (!broadcastTime || broadcastTime === "") {
                            let tMatch = container.innerText.match(/(\\d{2}:\\d{2})/);
                            if (tMatch) broadcastTime = tMatch[1];
                        } else {
                            let startMatch = broadcastTime.match(/(\\d{2}:\\d{2})/);
                            if (startMatch) broadcastTime = startMatch[1];
                        }

                        // 날짜 정보 추출 (예: "오늘", "2월 23일")
                        let itemDate = "오늘";
                        let dMatch = container.innerText.match(/(\\d{1,2}월\\s*\\d{1,2}일)/);
                        if (dMatch) {
                            itemDate = dMatch[1];
                        } else if (container.innerText.includes("내일")) {
                            itemDate = "내일";
                        } else if (container.innerText.includes("오늘")) {
                            itemDate = "오늘";
                        }

                        // 해당 컨테이너 내의 모든 상품 코드 링크 탐색
                        let links = Array.from(container.querySelectorAll('a[href*="slitmCd="], [data-slitm-cd], [data-slitm_cd]'));
                        links.forEach(l => {
                            let code = l.getAttribute('data-slitm-cd') || l.getAttribute('data-slitm_cd');
                            if (!code) {
                                let match = l.href ? l.href.match(/slitmCd=(\\d+)/) : null;
                                if (match) code = match[1];
                            }
                            if (!code) return;

                            let name = l.innerText.trim().split('\\n')[0].replace(/\\d+%.*/, '').trim();
                            if (name.length < 2) {
                                let nameEl = container.querySelector('[aria-label="제품명"], .pdname, .h84bfs5 span');
                                if (nameEl) name = nameEl.innerText.trim().split('\\n')[0].trim();
                            }
                            
                            if (name.length >= 2) {
                                items.push({ 
                                    time: broadcastTime || "시간정보없음", 
                                    code, 
                                    name,
                                    itemDate: itemDate
                                });
                            }
                        });
                    });
                    return items;
                }""")
                
                # 수집된 데이터 저장 (중복 자동 제거)
                today = datetime.datetime.now()
                for item in new_items:
                    # 날짜 정규화
                    raw_date = item["itemDate"]
                    final_date = clean_date 
                    
                    if raw_date == "오늘":
                        final_date = today.strftime("%m.%d")
                    elif raw_date == "내일":
                        final_date = (today + datetime.timedelta(days=1)).strftime("%m.%d")
                    elif "월" in raw_date and "일" in raw_date:
                        m_match = re.search(r"(\d+)월", raw_date)
                        d_match = re.search(r"(\d+)일", raw_date)
                        if m_match and d_match:
                            final_date = f"{int(m_match.group(1)):02d}.{int(d_match.group(1)):02d}"
                    
                    key = (final_date, item["time"], item["code"])
                    if key not in day_results:
                        day_results[key] = {
                            "날짜": final_date,
                            "방송시간": item["time"],
                            "상품코드": item["code"],
                            "상품명": item["name"],
                        }

                # 스크롤 다운
                scroll_count += 1
                previous_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(1.5)
                
                # "상품 더보기" 버튼 클릭 (있을 경우)
                expanded = False
                try:
                    more_button = page.locator("button:has-text('상품 더보기'), .btn_more").first
                    if await more_button.is_visible():
                        await more_button.click()
                        await asyncio.sleep(2)
                        expanded = True
                        stagnant_count = 0 
                except:
                    pass

                new_height = await page.evaluate("document.body.scrollHeight")
                
                if new_height == previous_height:
                    stagnant_count += 1
                else:
                    stagnant_count = 0
                
                if scroll_count % 10 == 0:
                    print(f"    ... 스크롤 중 ({scroll_count}회, 현재 {len(day_results)}개 발견)", end='\r')
                
                # 더 이상 로딩되지 않으면 종료 (15회 연속 높이 변화 없음)
                if stagnant_count >= 15 and not expanded:
                    break
            before = len(results)
            results.extend(day_results.values())
            print(f"  ✔ {len(results) - before}개 수집 (누적 {len(results)}개)")

        await browser.close()
        return results


def save_to_csv(results: list, filename="hmall_schedule.csv"):
    """결과를 CSV 파일로 저장합니다."""
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["날짜", "방송시간", "상품코드", "상품명"])
        writer.writeheader()
        writer.writerows(results)
    print(f"💾 CSV 저장: {filename} ({len(results)}개)")


async def main():
    print("=" * 50)
    print("  현대홈쇼핑 방송편성표 크롤러")
    print(f"  실행 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    results = await crawl_hmall()

    if not results:
        print("⚠️ 수집된 데이터가 없습니다.")
        return

    # CSV 저장 (백업용)
    save_to_csv(results)

    # Google Sheets 저장
    try:
        save_to_gsheet(results)
    except Exception as e:
        print(f"❌ Google Sheets 저장 실패: {e}")
        print("   (CSV 파일은 정상 저장되었습니다)")

    print("\n🎉 완료!")


if __name__ == "__main__":
    asyncio.run(main())
