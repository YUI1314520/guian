"""生成宣传海报：拼 HTML（字体与截图全部内嵌）→ playwright 渲染 → PNG。

中文字体按实际用到的汉字做子集（思源宋体 24MB → 几十 KB），
避免 file:// 下字体被 CORS 拦，也让 HTML 体积可控。
"""
import asyncio
import base64
import pathlib
import subprocess
import sys

from playwright.async_api import async_playwright
from PIL import Image

ROOT = pathlib.Path(r"F:\Deepseek\jiese")
PROMO = ROOT / "promo"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CN_TTF = r"C:\Windows\Fonts\NotoSerifSC-VF.ttf"


def b64(path, mime):
    return f"data:{mime};base64," + base64.b64encode(pathlib.Path(path).read_bytes()).decode()


def cn_subset(text):
    """把思源宋体裁到只含 text 里出现的汉字，返回 base64 data URI。"""
    chars = "".join(sorted({c for c in text if "\u4e00" <= c <= "\u9fff"}))
    fonts = PROMO / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    out = fonts / "noto-serif-sc-poster.ttf"
    cmd = [
        sys.executable, "-m", "fontTools.subset", CN_TTF,
        f"--text={chars}", "--layout-features=*", "--no-hinting",
        "--drop-tables+=DSIG", f"--output-file={out}",
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    data = out.read_bytes()
    print(f"中文子集：{len(chars)} 字，{len(data) / 1024:.0f} KB")
    return "data:font/ttf;base64," + base64.b64encode(data).decode()


FONT_SANS = b64(ROOT / "assets/fonts/space-grotesk.woff2", "font/woff2")
SHOT = b64(ROOT / "preview/02-today-checked.png", "image/png")
CN_MARK = "__FONT_CN__"

HTML = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  @font-face {{ font-family: 'Noto Serif SC Poster'; src: url({CN_MARK}) format('truetype'); font-weight: 200 900; font-display: block; }}
  @font-face {{ font-family: 'Space Grotesk'; src: url({FONT_SANS}) format('woff2'); font-weight: 300 700; font-display: block; }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: 1080px; height: 1440px; overflow: hidden; }}
  body {{
    position: relative;
    background: #0B1310;
    font-family: 'Space Grotesk', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    color: #F4FBF7;
    -webkit-font-smoothing: antialiased;
  }}

  .glow {{ position: absolute; inset: 0; }}
  .glow::before {{
    content: ''; position: absolute; inset: 0;
    background:
      radial-gradient(64% 52% at 2% -8%, rgba(0, 132, 100, 0.44) 0%, transparent 64%),
      radial-gradient(52% 40% at 96% 96%, rgba(150, 108, 12, 0.34) 0%, transparent 66%),
      radial-gradient(70% 58% at 82% 40%, rgba(138, 213, 188, 0.10) 0%, transparent 70%);
  }}
  .grain {{
    position: absolute; inset: 0; opacity: 0.075; mix-blend-mode: screen; pointer-events: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23n)'/%3E%3C/svg%3E");
  }}
  .frame {{ position: absolute; inset: 34px; border: 1px solid rgba(214, 240, 228, 0.14); }}

  .left {{ position: absolute; left: 88px; top: 92px; width: 496px; }}

  .brand {{ display: flex; align-items: center; gap: 14px; }}
  .brand-mark {{
    width: 44px; height: 44px; border-radius: 13px;
    background: linear-gradient(150deg, #1E6B58, #0E3A2F);
    display: grid; place-items: center;
    box-shadow: 0 10px 24px -12px rgba(0, 0, 0, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.18);
  }}
  .brand-mark svg {{ width: 26px; height: 26px; stroke: #A6F2D8; fill: none; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }}
  .brand-name {{ font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; font-size: 26px; font-weight: 600; letter-spacing: 0.26em; color: #EAF7F0; }}
  .brand-en {{ font-family: 'Space Grotesk', sans-serif; font-size: 12px; letter-spacing: 0.42em; color: #6F8E80; margin-left: 4px; }}

  .eyebrow {{
    margin-top: 96px;
    font-size: 15px; letter-spacing: 0.3em; color: #E0B558;
    display: flex; align-items: center; gap: 14px;
  }}
  .eyebrow span {{ width: 34px; height: 1px; background: rgba(224, 181, 88, 0.55); display: inline-block; }}

  h1 {{
    margin-top: 26px;
    font-family: 'Noto Serif SC Poster', 'Songti SC', SimSun, serif;
    font-size: 116px; line-height: 1.06; font-weight: 600;
    letter-spacing: 0.02em; color: #F7FCF9;
  }}
  h1 em {{ font-style: normal; color: #8AD5BC; }}

  .rule {{ margin-top: 40px; width: 72px; height: 3px; background: #E0B558; }}
  .sub {{ margin-top: 26px; font-size: 27px; line-height: 1.6; color: #A9C6BA; letter-spacing: 0.02em; }}

  .feats {{ margin-top: 74px; display: grid; gap: 40px; }}
  .feat {{ display: grid; grid-template-columns: 42px 1fr; gap: 20px; align-items: start; }}
  .feat svg {{ width: 30px; height: 30px; margin-top: 2px; stroke: #8AD5BC; fill: none; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }}
  .feat b {{ display: block; font-size: 25px; font-weight: 600; color: #E7F4EC; letter-spacing: 0.02em; }}
  .feat p {{ margin-top: 9px; font-size: 20px; line-height: 1.55; color: #86A396; letter-spacing: 0.02em; }}

  .foot {{
    position: absolute; left: 88px; bottom: 74px;
    display: flex; align-items: center; gap: 14px;
    font-size: 17px; letter-spacing: 0.14em; color: #6F8E80;
  }}
  .foot i {{ width: 6px; height: 6px; border-radius: 50%; background: #4E7A67; display: inline-block; }}

  .phone-wrap {{ position: absolute; left: 652px; top: 362px; width: 340px; height: 715px; }}
  .phone-glow {{
    position: absolute; left: 50%; top: 50%; width: 500px; height: 520px;
    transform: translate(-50%, -50%);
    background: radial-gradient(circle, rgba(138, 213, 188, 0.18) 0%, rgba(138, 213, 188, 0.05) 42%, transparent 68%);
  }}
  .phone {{
    position: relative; width: 340px; height: 715px; padding: 9px;
    border-radius: 54px;
    background: linear-gradient(160deg, #35463F 0%, #1A2622 48%, #0F1915 100%);
    box-shadow:
      0 60px 110px -50px rgba(0, 0, 0, 0.95),
      0 26px 50px -30px rgba(0, 0, 0, 0.8),
      inset 0 1px 0 rgba(255, 255, 255, 0.16);
  }}
  .phone img {{ width: 322px; height: 697px; border-radius: 46px; display: block; object-fit: cover; }}
  .screen {{
    position: absolute; inset: 9px; border-radius: 46px; pointer-events: none;
    box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.55);
  }}
  .caption {{
    position: absolute; left: 652px; top: 1108px; width: 340px;
    text-align: center; font-size: 15px; letter-spacing: 0.24em; color: #628073;
  }}
</style>
</head>
<body>
  <div class="glow"></div>
  <div class="grain"></div>
  <div class="frame"></div>

  <div class="left">
    <div class="brand">
      <div class="brand-mark">
        <svg viewBox="0 0 24 24"><path d="M12 21c4-3 7-7 7-11a7 7 0 1 0-14 0c0 4 3 8 7 11Z"/><path d="M12 21V9"/></svg>
      </div>
      <div class="brand-name">归岸</div>
      <div class="brand-en">JIEGUAN</div>
    </div>

    <div class="eyebrow"><span></span>戒断 · 打卡</div>

    <h1>把自己<br>带回<em>岸</em>上</h1>

    <div class="rule"></div>
    <div class="sub">每天一次打卡，<br>看见自己在变好。</div>

    <div class="feats">
      <div class="feat">
        <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="m8.5 12.2 2.4 2.4 4.6-4.9"/></svg>
        <div><b>一天一次，按一下就好</b><p>不用填表、不用记账，打开就打卡</p></div>
      </div>
      <div class="feat">
        <svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M8 3v4M16 3v4M3.5 10h17"/></svg>
        <div><b>日历上看得到的长进</b><p>补记、破戒都能改，记录不替你撒谎</p></div>
      </div>
      <div class="feat">
        <svg viewBox="0 0 24 24"><path d="M12 3.5 19 6v6c0 4.4-3 7.6-7 8.5-4-.9-7-4.1-7-8.5V6l7-2.5Z"/><path d="M12 9.5v3.2M12 15.6v.1"/></svg>
        <div><b>想破戒的那一刻</b><p>呼吸引导、延迟十分钟、把念头写下来</p></div>
      </div>
    </div>
  </div>

  <div class="foot"><i></i>离线可用 · 数据只存在这台手机里</div>

  <div class="phone-wrap">
    <div class="phone-glow"></div>
    <div class="phone">
      <img src="{SHOT}" alt="归岸 · 今日视图">
      <div class="screen"></div>
    </div>
  </div>
  <div class="caption">今日 · 连续打卡</div>
</body>
</html>
"""


async def main():
    PROMO.mkdir(exist_ok=True)
    html = HTML.replace(CN_MARK, cn_subset(HTML))
    html_path = PROMO / "promo.html"
    html_path.write_text(html, encoding="utf-8")
    print("html", f"{html_path.stat().st_size / 1024 / 1024:.1f} MB")

    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, headless=True)
        ctx = await b.new_context(viewport={"width": 1080, "height": 1440}, device_scale_factor=2)
        pg = await ctx.new_page()
        await pg.goto(html_path.as_uri(), wait_until="load")
        await pg.evaluate("document.fonts.ready")
        await pg.wait_for_timeout(700)
        raw = PROMO / "promo@2x.png"
        await pg.screenshot(path=str(raw), clip={"x": 0, "y": 0, "width": 1080, "height": 1440})
        await b.close()

    im = Image.open(raw)
    print("raw", im.size)
    im.convert("RGB").save(PROMO / "归岸-宣传图-2160x2880.png", optimize=True)
    im.resize((1440, 1920), Image.LANCZOS).convert("RGB").save(PROMO / "归岸-宣传图.png", optimize=True)
    for f in ("归岸-宣传图.png", "归岸-宣传图-2160x2880.png"):
        p = PROMO / f
        print(f, Image.open(p).size, f"{p.stat().st_size / 1024:.0f} KB")


asyncio.run(main())
