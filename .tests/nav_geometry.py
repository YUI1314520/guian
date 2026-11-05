"""底部导航几何检查：是否贴满左右下三边、入口是否收在内容宽度内、是否遮挡内容。"""
import asyncio
import pathlib

from playwright.async_api import async_playwright

APP = pathlib.Path(r"F:\Deepseek\jiese\index.html").as_uri()
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

SIZES = [(360, 640), (390, 844), (430, 932), (600, 900), (800, 1000)]
VIEWS = ["today", "calendar", "sos", "me"]


async def main():
    ok = True
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, headless=True)
        for w, h in SIZES:
            ctx = await b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
            pg = await ctx.new_page()
            await pg.goto(f"{APP}?demo=1", wait_until="load")
            await pg.wait_for_timeout(700)
            if await pg.locator("#dialog-host .dialog").count():
                await pg.locator("#dialog-host .dialog-actions .btn").last.click()
                await pg.wait_for_timeout(400)
            for v in VIEWS:
                await pg.evaluate(
                    "v => { const b = document.querySelector(`.nav-item[data-go='${v}']`); b && b.click(); }", v
                )
                await pg.wait_for_timeout(320)
                geo = await pg.evaluate(
                    """() => {
                    const nav = document.querySelector('.nav');
                    const r = nav.getBoundingClientRect();
                    const cs = getComputedStyle(nav);
                    const items = [...nav.querySelectorAll('.nav-item')].map(i => i.getBoundingClientRect());
                    const first = items[0], last = items[items.length - 1];
                    return {
                      left: +r.left.toFixed(1), right: +r.right.toFixed(1),
                      bottom: +r.bottom.toFixed(1), width: +r.width.toFixed(1),
                      vw: innerWidth, vh: innerHeight,
                      radius: cs.borderTopLeftRadius,
                      itemSpan: +(last.right - first.left).toFixed(1),
                      itemMinH: Math.min(...items.map(i => +i.height.toFixed(1))),
                    };
                  }"""
                )
                bad = []
                if abs(geo["left"]) > 0.5 or abs(geo["right"] - geo["vw"]) > 0.5:
                    bad.append(f'横向未铺满 left={geo["left"]} right={geo["right"]} vw={geo["vw"]}')
                if abs(geo["bottom"] - geo["vh"]) > 0.5:
                    bad.append(f'底部未贴边 bottom={geo["bottom"]} vh={geo["vh"]}')
                if geo["radius"] != "0px":
                    bad.append(f'圆角未归零 {geo["radius"]}')
                if geo["itemSpan"] > 500:
                    bad.append(f'入口摊太开 {geo["itemSpan"]}px')
                if geo["itemMinH"] < 44:
                    bad.append(f'触控高度不足 {geo["itemMinH"]}')
                # 内容是否被遮：滚到底，看最后一个可见块底部是否低于导航顶
                covered = await pg.evaluate(
                    """() => {
                    window.scrollTo(0, document.body.scrollHeight);
                    const nav = document.querySelector('.nav').getBoundingClientRect();
                    const view = document.querySelector('.view:not([hidden])');
                    const blocks = [...view.querySelectorAll('.card, .footer-note, .btn')].filter(e => e.offsetParent);
                    if (!blocks.length) return null;
                    const last = blocks[blocks.length - 1].getBoundingClientRect();
                    return +(last.bottom - nav.top).toFixed(1);
                  }"""
                )
                if covered is not None and covered > 0:
                    bad.append(f"内容被遮 {covered}px")
                status = "ok " if not bad else "BAD"
                if bad:
                    ok = False
                print(f"{status} {w}x{h} {v:9} nav w={geo['width']} 高={geo['itemMinH']} 入口跨度={geo['itemSpan']} " + ("; ".join(bad)))
            await ctx.close()
        await b.close()
    print("\n导航几何：全部通过" if ok else "\n导航几何：有问题")
    return 0 if ok else 1


raise SystemExit(asyncio.run(main()))
