import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def get_html():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            viewport={"width": 390, "height": 844},
            is_mobile=True,
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        url = "https://www.hmall.com/md/dpl/index?mainDispSeq=2&brodType=all"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="load", timeout=90000)
        await asyncio.sleep(5)

        # Click TV쇼핑
        await page.evaluate("""() => {
            let btns = Array.from(document.querySelectorAll('button, a'));
            let tvBtn = btns.find(b => b.innerText.trim() === 'TV쇼핑');
            if (tvBtn) tvBtn.click();
        }""")
        await asyncio.sleep(5)

        # Scroll several times
        for i in range(10):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            # Try to click 'More' if it appears
            await page.evaluate("""() => {
                let mores = Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('상품 더보기') || b.innerText.includes('더보기'));
                if (mores.length > 0) mores[0].click();
            }""")
            await asyncio.sleep(1)

        # Save HTML
        content = await page.content()
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("HTML saved.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_html())
