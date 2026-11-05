"""海报自检：版式几何 + 像素（模型看不到图，只能靠这些断言兜底）。"""
import asyncio
import pathlib

from playwright.async_api import async_playwright
from PIL import Image

PROMO = pathlib.Path(r"F:\Deepseek\jiese\promo")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
W, H = 1080, 1440

ok = True


def check(name, cond, detail=""):
    global ok
    if not cond:
        ok = False
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail else ""))


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, headless=True)
        pg = await b.new_page(viewport={"width": W, "height": H})
        await pg.goto((PROMO / "promo.html").as_uri(), wait_until="load")
        await pg.evaluate("document.fonts.ready")
        await pg.wait_for_timeout(500)

        geo = await pg.evaluate(
            """() => {
              const r = s => { const e = document.querySelector(s); const b = e.getBoundingClientRect();
                return {x: +b.x.toFixed(1), y: +b.y.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1),
                        right: +b.right.toFixed(1), bottom: +b.bottom.toFixed(1),
                        sw: e.scrollWidth, cw: e.clientWidth, sh: e.scrollHeight, ch: e.clientHeight}; };
              return {
                doc: {sw: document.documentElement.scrollWidth, sh: document.documentElement.scrollHeight},
                left: r('.left'), h1: r('h1'), sub: r('.sub'), feats: r('.feats'),
                foot: r('.foot'), phone: r('.phone'), wrap: r('.phone-wrap'), caption: r('.caption'),
                img: (() => { const i = document.querySelector('.phone img');
                              return {nw: i.naturalWidth, nh: i.naturalHeight, w: i.clientWidth, h: i.clientHeight}; })(),
                fonts: {serif: document.fonts.check('116px "Noto Serif SC Poster"'),
                        sans: document.fonts.check('20px "Space Grotesk"')},
                overflowX: document.documentElement.scrollWidth > 1080,
                overflowY: document.documentElement.scrollHeight > 1440,
              };
            }"""
        )
        await b.close()

    d = geo
    check("画布无溢出", not d["overflowX"] and not d["overflowY"], f'{d["doc"]}')
    check("中文思源宋体已加载（标题不走回退）", d["fonts"]["serif"])
    check("Space Grotesk 已加载", d["fonts"]["sans"])
    check("手机截图已加载", d["img"]["nw"] > 0, f'{d["img"]["nw"]}x{d["img"]["nh"]}')

    # 左栏与手机不打架
    check("左栏右缘 < 手机左缘", d["left"]["right"] < d["phone"]["x"] - 40,
          f'{d["left"]["right"]} vs {d["phone"]["x"]}')
    # 各块首尾相接但不重叠
    check("标题在副标题上方", d["h1"]["bottom"] <= d["sub"]["y"] + 1,
          f'{d["h1"]["bottom"]} <= {d["sub"]["y"]}')
    check("副标题在卖点上方", d["sub"]["bottom"] <= d["feats"]["y"] + 1,
          f'{d["sub"]["bottom"]} <= {d["feats"]["y"]}')
    check("卖点不压页脚", d["feats"]["bottom"] <= d["foot"]["y"] - 10,
          f'{d["feats"]["bottom"]} vs {d["foot"]["y"]}')
    check("页脚在画布内", d["foot"]["bottom"] <= H - 40, f'{d["foot"]["bottom"]}')
    check("手机框在画布内", d["phone"]["y"] >= 40 and d["phone"]["bottom"] <= H - 40,
          f'{d["phone"]["y"]}..{d["phone"]["bottom"]}')
    check("手机说明不压手机", d["caption"]["y"] >= d["phone"]["bottom"], f'{d["caption"]["y"]}')
    check("手机说明在画布内", d["caption"]["bottom"] <= H - 20, f'{d["caption"]["bottom"]}')
    # 文本没被裁
    for k in ("h1", "sub", "feats"):
        check(f"{k} 横向无裁切", d[k]["sw"] <= d[k]["cw"] + 1, f'sw{d[k]["sw"]}/cw{d[k]["cw"]}')
    # 行盒允许小幅超出（中文回退字体的 ascender 比盒子高），只要有 12px 余量且无人裁切
    check("标题行盒不侵入下一条", d["h1"]["sh"] - d["h1"]["ch"] <= 24, f'{d["h1"]["sh"]} vs {d["h1"]["ch"]}')
    check("标题下方留够 12px", d["sub"]["y"] - (d["h1"]["y"] + d["h1"]["sh"]) >= 12,
          f'{d["sub"]["y"] - (d["h1"]["y"] + d["h1"]["sh"]):.1f}')
    # 手机宽高比接近 390:844
    ratio = d["img"]["w"] / d["img"]["h"]
    check("截图比例未变形", abs(ratio - 390 / 844) < 0.005, f"{ratio:.4f}")

    # ---------- 像素 ----------
    im = Image.open(PROMO / "归岸-宣传图.png").convert("RGB")
    sx = im.width / W
    px = lambda x, y: im.getpixel((int(x * sx), int(y * sx)))
    lum = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    check("尺寸 2160×2880", im.size == (2160, 2880), str(im.size))
    check("背景是深色", lum(px(20, 20)) < 60, f"{px(20, 20)} lum={lum(px(20,20)):.0f}")
    check("左上角有绿色光晕", px(60, 40)[1] > px(60, 40)[0] + 8, f"{px(60, 40)}")

    def bright_count(x0, y0, x1, y1, th=170):
        n = 0
        for x in range(int(x0 * sx), int(x1 * sx), 4):
            for y in range(int(y0 * sx), int(y1 * sx), 4):
                if lum(im.getpixel((x, y))) > th:
                    n += 1
        return n

    check("标题区有亮色字", bright_count(88, 380, 560, 500) > 300, str(bright_count(88, 380, 560, 500)))
    check("手机区有亮色界面", bright_count(660, 420, 980, 1000) > 900, str(bright_count(660, 420, 980, 1000)))
    check("卖点区有文字", bright_count(88, 700, 560, 1000, 120) > 250, str(bright_count(88, 700, 560, 1000, 120)))

    # 画面不是一整块纯色
    small = im.resize((180, 240), Image.LANCZOS)
    colors = len({small.getpixel((x, y)) for x in range(0, 180, 2) for y in range(0, 240, 2)})
    check("画面有层次（非纯色）", colors > 400, f"{colors} 色")

    # 左右两侧都有内容（不是半边空）
    left_ink = bright_count(60, 60, 560, 1380, 110)
    right_ink = bright_count(620, 300, 1040, 1180, 110)
    check("左栏有内容", left_ink > 500, str(left_ink))
    check("右栏有内容", right_ink > 500, str(right_ink))

    print("\n全部通过" if ok else "\n有失败项")
    return 0 if ok else 1


raise SystemExit(asyncio.run(main()))
