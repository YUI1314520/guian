"""多尺寸布局检查：横向溢出、导航遮挡、弹窗适配、字体加载、触控尺寸。"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(r"F:\Deepseek\jiese")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE = "http://127.0.0.1:8765/index.html"
SIZES = [(360, 640), (390, 844), (430, 932)]
VIEWS = ["today", "calendar", "sos", "me"]
out = []


def run():
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, headless=True)
        for (w, h) in SIZES:
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=True, has_touch=True)
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: out.append({"type": "js-error", "msg": str(e)}))
            for v in VIEWS:
                pg.goto(f"{BASE}?demo=1&view={v}", wait_until="networkidle")
                pg.wait_for_timeout(500)
                info = pg.evaluate(
                    """() => {
                  const nav = document.querySelector('.nav').getBoundingClientRect();
                  const main = document.querySelector('#main');
                  const view = document.querySelector('.view:not([hidden])');
                  const cards = [...view.querySelectorAll('.card, .quote-card, .text-btn, .hint-line, .footer-note')];
                  const last = cards[cards.length - 1];
                  const r = last ? last.getBoundingClientRect() : null;
                  const small = [...view.querySelectorAll('button, a, [role=button]')]
                    .map(el => ({t: (el.textContent||'').trim().slice(0,12), w: Math.round(el.getBoundingClientRect().width), h: Math.round(el.getBoundingClientRect().height)}))
                    .filter(x => x.h > 0 && x.h < 44);
                  return {
                    sw: document.documentElement.scrollWidth,
                    iw: window.innerWidth,
                    docH: document.documentElement.scrollHeight,
                    navTop: Math.round(nav.top),
                    lastBottom: r ? Math.round(r.bottom) : null,
                    padBottom: getComputedStyle(main).paddingBottom,
                    smallTargets: small,
                  };
                }"""
                )
                out.append({"size": f"{w}x{h}", "view": v, **info})
                # 滚到底，检查最后一块内容不被浮动导航压住
                pg.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                pg.wait_for_timeout(350)
                overlap = pg.evaluate(
                    """() => {
                  const nav = document.querySelector('.nav').getBoundingClientRect();
                  const cards = [...document.querySelectorAll('.view:not([hidden]) .card, .view:not([hidden]) .quote-card, .view:not([hidden]) .footer-note, .view:not([hidden]) .hint-line')];
                  const last = cards[cards.length-1];
                  if (!last) return null;
                  const r = last.getBoundingClientRect();
                  return {lastBottom: Math.round(r.bottom), navTop: Math.round(nav.top), covered: r.bottom > nav.top + 1};
                }"""
                )
                out.append({"size": f"{w}x{h}", "view": v, "scrollBottom": overlap})
            # 弹窗适配（首次引导 + 复发确认 + 目标）
            pg.goto(BASE, wait_until="networkidle")
            pg.wait_for_timeout(600)
            dlg = pg.evaluate(
                """() => {
              const d = document.querySelector('.dialog');
              const host = document.querySelector('#dialog-host');
              if (!d) return null;
              const r = d.getBoundingClientRect();
              return {top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height),
                      vh: window.innerHeight, hostScroll: host.scrollHeight, hostClient: host.clientHeight};
            }"""
            )
            out.append({"size": f"{w}x{h}", "onboarding": dlg})
            pg.evaluate("""() => { document.querySelectorAll('.option-chip')[1]?.click(); }""")
            ctx.close()
        # 字体
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        pg = ctx.new_page()
        pg.goto(BASE + "?demo=1", wait_until="networkidle")
        pg.wait_for_timeout(800)
        fonts = pg.evaluate(
            """async () => {
          await document.fonts.ready;
          return {
            serif: document.fonts.check('16px "Instrument Serif"'),
            grotesk: document.fonts.check('16px "Space Grotesk"'),
            size: document.fonts.size,
            body: getComputedStyle(document.body).fontSize,
            bodyLH: getComputedStyle(document.body).lineHeight,
            family: getComputedStyle(document.querySelector('#streak-num')).fontFamily,
            streakSize: getComputedStyle(document.querySelector('#streak-num')).fontSize,
          };
        }"""
        )
        out.append({"fonts": fonts})
        ctx.close()
        b.close()


run()
print(json.dumps(out, ensure_ascii=False, indent=1))
