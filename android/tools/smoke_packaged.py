"""在真实浏览器里验证「打包进 APK 的那份资源」能跑：无报错、字体加载、file:// 下 localStorage 持久化。"""
import asyncio
import pathlib

from playwright.async_api import async_playwright

APP = pathlib.Path(r"F:\Deepseek\apk-build\android\assets\www\index.html").as_uri()
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME, headless=True)
        ctx = await browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page = await ctx.new_page()
        errors, failed = [], []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("requestfailed", lambda r: failed.append(r.url))

        await page.goto(APP, wait_until="load")
        await page.wait_for_timeout(1200)

        if await page.locator("#dialog-host .dialog").count():
            start = page.locator("#dialog-host .dialog-actions .btn").last
            await start.click()
            await page.wait_for_timeout(600)

        streak_before = (await page.locator("#streak-num").first.inner_text()).strip()
        fonts = await page.evaluate("document.fonts.check('16px \"Space Grotesk\"')")

        await page.locator("#check-btn").click()
        await page.wait_for_timeout(600)
        await page.reload(wait_until="load")
        await page.wait_for_timeout(900)
        streak_after = (await page.locator("#streak-num").first.inner_text()).strip()

        ok_theme = await page.evaluate(
            "document.querySelector('#theme-btn').click(); document.documentElement.dataset.theme"
        )

        print("streak:", streak_before, "-> after reload:", streak_after, "(打卡后应为 1)")
        print("font loaded:", fonts)
        print("theme after toggle:", ok_theme)
        print("console errors:", errors[:6])
        print("failed requests:", failed[:6])
        await browser.close()


asyncio.run(main())
