import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def debug_page():
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
        try:
            await page.goto(url, wait_until="load", timeout=60000)
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Initial navigation failed/timed out: {e}")
            # Try to proceed anyway as some content might have loaded

        # Take screenshot of initial state
        await page.screenshot(path="debug_initial.png")
        print("Initial screenshot saved.")

        # Try to find 'TV쇼핑' tab
        tabs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button, a'))
                .map(b => ({ tag: b.tagName, text: b.innerText.trim(), visible: b.offsetParent !== null }))
                .filter(b => b.text.length > 0);
        }""")
        print(f"Found {len(tabs)} clickable elements.")
        tv_tabs = [t for t in tabs if "TV쇼핑" in t['text']]
        print(f"TV Shopping tabs found: {tv_tabs}")

        # Click 'TV쇼핑' if found
        if tv_tabs:
            print(f"Clicking TV쇼핑 tab: {tv_tabs[0]}")
            await page.evaluate("""() => {
                let btns = Array.from(document.querySelectorAll('button, a'));
                let tvBtn = btns.find(b => b.innerText.trim() === 'TV쇼핑');
                if (tvBtn) tvBtn.click();
            }""")
            await asyncio.sleep(5)
            await page.screenshot(path="debug_after_tv_click.png")
            print("Screenshot after TV click saved.")

        # Check products and their containers
        structure = await page.evaluate("""() => {
            let samples = [];
            let links = document.querySelectorAll('a[href*="slitmCd="]');
            for (let i = 0; i < Math.min(5, links.length); i++) {
                let a = links[i];
                let parentInfo = [];
                let curr = a;
                for (let d = 0; d < 10 && curr; d++) {
                    parentInfo.push({
                        tag: curr.tagName,
                        className: curr.className,
                        text: curr.innerText.substring(0, 50)
                    });
                    curr = curr.parentElement;
                }
                samples.push({
                    href: a.href,
                    text: a.innerText.substring(0, 50),
                    parents: parentInfo
                });
            }
            return samples;
        }""")
        print(f"Structure samples: {structure}")

        # Scroll a bit more
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(1)

        # Save HTML
        content = await page.content()
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("Full HTML saved to debug_page.html")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page())
