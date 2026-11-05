"""重新生成 preview/ 里的截图与总览图（改版后跑一次即可）。"""
import asyncio
import pathlib

from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFont

APP = pathlib.Path(r"F:\Deepseek\jiese\index.html").as_uri()
OUT = pathlib.Path(r"F:\Deepseek\jiese\preview")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
FONT = r"C:\Windows\Fonts\msyh.ttc"


async def shoot(page, name, full=False):
    path = OUT / name
    await page.screenshot(path=str(path), full_page=full)
    print("shot", name, Image.open(path).size)


async def main():
    OUT.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME, headless=True)

        # 演示数据：26 天 → 破戒 → 12 天
        ctx = await browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto(f"{APP}?demo=1", wait_until="load")
        await page.wait_for_timeout(900)
        if await page.locator("#dialog-host .dialog").count():
            await page.locator("#dialog-host .dialog-actions .btn").last.click()
            await page.wait_for_timeout(400)

        await page.wait_for_timeout(300)
        await shoot(page, "01-today.png")

        await page.locator("#check-btn").click()
        await page.wait_for_timeout(700)
        await shoot(page, "02-today-checked.png")

        for view, name in (("calendar", "03-calendar.png"), ("sos", "04-sos.png"), ("me", "05-me.png")):
            await page.locator(f".nav-item[data-go='{view}']").click()
            await page.wait_for_timeout(600)
            await shoot(page, name)

        # 深色：回到今日再切主题，整页截图
        await page.locator(".nav-item[data-go='today']").click()
        await page.wait_for_timeout(400)
        await page.locator("#theme-btn").click()
        await page.wait_for_timeout(700)
        await shoot(page, "06-dark.png")
        await ctx.close()

        # 首次引导（干净上下文，无演示数据）
        ctx2 = await browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page2 = await ctx2.new_page()
        await page2.goto(APP, wait_until="load")
        await page2.wait_for_timeout(900)
        await shoot(page2, "07-onboarding.png")
        await ctx2.close()
        await browser.close()

    # 总览：三张并排 + 顶部标题
    names = ["01-today.png", "02-today-checked.png", "03-calendar.png"]
    shots = [Image.open(OUT / n).convert("RGB") for n in names]
    scale = 0.5
    shots = [s.resize((int(s.width * scale), int(s.height * scale)), Image.LANCZOS) for s in shots]
    gap, pad, top = 28, 44, 96
    w = pad * 2 + sum(s.width for s in shots) + gap * (len(shots) - 1)
    h = top + max(s.height for s in shots) + pad
    canvas = Image.new("RGB", (w, h), (245, 251, 246))
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype(FONT, 34)
    sub = ImageFont.truetype(FONT, 20)
    draw.text((pad, 28), "归岸 · 每天一次打卡", font=title, fill=(20, 80, 63))
    draw.text((pad, 66), "MD3 风格 / 悬浮底部导航 / 离线可用", font=sub, fill=(90, 110, 102))
    x = pad
    for s in shots:
        canvas.paste(s, (x, top))
        x += s.width + gap
    overview = OUT / "00-overview.png"
    canvas.save(overview, optimize=True)
    print("overview", canvas.size, overview)


asyncio.run(main())
