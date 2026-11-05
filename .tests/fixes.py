"""回归：顶部栏铺满屏宽、底部导航回到悬浮胶囊、点击不再出现外框。"""
import asyncio
import pathlib

from playwright.async_api import async_playwright
from PIL import Image

APP = pathlib.Path(r"F:\Deepseek\jiese\index.html").as_uri()
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SHOT = pathlib.Path(r"F:\Deepseek\jiese\.shots")

ok = True


def check(name, cond, detail=""):
    global ok
    if not cond:
        ok = False
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail else ""))


async def main():
    SHOT.mkdir(exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, headless=True)
        for w, h in [(360, 640), (390, 844), (800, 1000)]:
            ctx = await b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
            pg = await ctx.new_page()
            await pg.goto(f"{APP}?demo=1", wait_until="load")
            await pg.wait_for_timeout(800)
            if await pg.locator("#dialog-host .dialog").count():
                await pg.locator("#dialog-host .dialog-actions .btn").last.click()
                await pg.wait_for_timeout(350)

            # 1) 底部导航：悬浮胶囊
            geo = await pg.evaluate(
                """() => {
                  const r = document.querySelector('.nav').getBoundingClientRect();
                  return {left: r.left, right: r.right, bottom: r.bottom, width: r.width,
                          vw: innerWidth, vh: innerHeight,
                          radius: getComputedStyle(document.querySelector('.nav')).borderTopLeftRadius};
                }"""
            )
            check(f"{w}px 导航左侧留白", geo["left"] >= 14, f'{geo["left"]:.1f}')
            check(f"{w}px 导航右侧留白", geo["vw"] - geo["right"] >= 14, f'{geo["vw"] - geo["right"]:.1f}')
            check(f"{w}px 导航宽 ≤436", geo["width"] <= 436, f'{geo["width"]:.1f}')
            check(f"{w}px 导航离底 14px", abs(geo["vh"] - geo["bottom"] - 14) < 1.5, f'{geo["vh"] - geo["bottom"]:.1f}')
            check(f"{w}px 导航是圆角", geo["radius"] not in ("0px", ""), geo["radius"])

            # 2) 顶部栏背景横向铺满：滚动后截图取像素
            await pg.evaluate("window.scrollTo(0, 620)")
            await pg.wait_for_timeout(450)
            shot = SHOT / f"appbar-{w}.png"
            await pg.screenshot(path=str(shot))
            im = Image.open(shot).convert("RGB")
            band_y = 40
            left_px = im.getpixel((2, band_y))
            right_px = im.getpixel((im.width - 3, band_y))
            mid_px = im.getpixel((im.width // 2, band_y))
            same_as_mid = max(abs(a - c) for a, c in zip(left_px, mid_px)) <= 6
            same_right = max(abs(a - c) for a, c in zip(right_px, mid_px)) <= 6
            check(f"{w}px 顶栏左边缘是顶栏底色", same_as_mid, f"{left_px} vs {mid_px}")
            check(f"{w}px 顶栏右边缘是顶栏底色", same_right, f"{right_px} vs {mid_px}")
            await pg.evaluate("window.scrollTo(0, 0)")
            await pg.wait_for_timeout(250)

            # 3) 点击后无焦点外框
            await pg.locator("#check-btn").click()
            await pg.wait_for_timeout(450)
            outline = await pg.evaluate(
                """() => {
                  const a = document.activeElement;
                  const cs = getComputedStyle(a);
                  return {tag: a.tagName, cls: a.className, style: cs.outlineStyle,
                          width: cs.outlineWidth, kbd: document.documentElement.classList.contains('kbd')};
                }"""
            )
            check(f"{w}px 点击后无外框", outline["style"] == "none" or outline["width"] == "0px",
                  f'{outline["tag"]}.{outline["cls"]} {outline["style"]} {outline["width"]}')
            check(f"{w}px 点击后未挂 kbd 类", not outline["kbd"])

            # 4) 键盘 Tab 仍能看到焦点环
            await pg.keyboard.press("Tab")
            await pg.wait_for_timeout(200)
            kbd = await pg.evaluate(
                """() => {
                  const a = document.activeElement;
                  const cs = getComputedStyle(a);
                  return {kbd: document.documentElement.classList.contains('kbd'),
                          style: cs.outlineStyle, width: cs.outlineWidth};
                }"""
            )
            check(f"{w}px Tab 后挂 kbd 类", kbd["kbd"])
            check(f"{w}px Tab 后显示焦点环", kbd["style"] != "none" and kbd["width"] not in ("0px", "0"),
                  f'{kbd["style"]} {kbd["width"]}')

            # 5) 点击高亮色透明
            hl = await pg.evaluate(
                "() => getComputedStyle(document.querySelector('.nav-item'))['-webkit-tap-highlight-color']"
            )
            check(f"{w}px 点击高亮透明", "0, 0, 0, 0" in hl or hl in ("transparent", "rgba(0, 0, 0, 0)"), hl)
            await ctx.close()
        await b.close()
    print("\n全部通过" if ok else "\n有失败项")
    return 0 if ok else 1


raise SystemExit(asyncio.run(main()))
