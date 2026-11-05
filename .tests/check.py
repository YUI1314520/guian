"""归岸 · 自动化回归检查（Playwright + 本机 Chrome）
覆盖：渲染、无横向溢出、触控尺寸、打卡/撤销、日历补记、呼吸、计时、笔记、
      主题、复发流程、首次引导、刷新后持久化、对比度。
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(r"F:\Deepseek\jiese")
SHOTS = ROOT / ".shots"
SHOTS.mkdir(exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE = "http://127.0.0.1:8765/index.html"

results = []
console_errors = []


def check(name, ok, detail=""):
    results.append({"name": name, "ok": bool(ok), "detail": str(detail)[:300]})
    print(("PASS " if ok else "FAIL ") + name + ("  " + str(detail)[:160] if detail else ""))


def no_overflow(page):
    return page.evaluate(
        "() => ({sw: document.documentElement.scrollWidth, iw: window.innerWidth})"
    )


def contrast(page, fg_sel, bg_sel):
    return page.evaluate(
        """([fgSel, bgSel]) => {
      const parse = (c) => (c.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
      const lum = (rgb) => {
        const [r, g, b] = rgb.map((v) => {
          v /= 255;
          return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      const fg = getComputedStyle(document.querySelector(fgSel)).color;
      const bgEl = document.querySelector(bgSel);
      let bg = getComputedStyle(bgEl).backgroundColor;
      if (/rgba\\(.*,\\s*0\\)/.test(bg) || bg === 'transparent') {
        bg = getComputedStyle(document.body).backgroundColor;
      }
      const L1 = lum(parse(fg)), L2 = lum(parse(bg));
      const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
      return Math.round(ratio * 100) / 100;
    }""",
        [fg_sel, bg_sel],
    )


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True)

    # ---------- A. 演示模式：视觉与交互 ----------
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, locale="zh-CN")
    page = ctx.new_page()
    page.on("console", lambda m: console_errors.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))

    page.goto(BASE + "?demo=1", wait_until="networkidle")
    page.wait_for_timeout(600)
    page.screenshot(path=str(SHOTS / "today.png"))
    page.screenshot(path=str(SHOTS / "today-full.png"), full_page=True)

    ov = no_overflow(page)
    check("无横向溢出", ov["sw"] <= ov["iw"] + 1, ov)

    streak = page.locator("#streak-num").inner_text()
    check("演示连续天数为 12", streak == "12", streak)

    box = page.locator("#check-btn").bounding_box()
    check("打卡按钮触控尺寸 >= 44", box and box["width"] >= 44 and box["height"] >= 44, box)

    nav_box = page.locator(".nav-item").first.bounding_box()
    check("导航项触控高度 >= 44", nav_box and nav_box["height"] >= 44, nav_box)

    # 浅色对比度
    c1 = contrast(page, "body", "body")
    c2 = contrast(page, "#check-hint", ".card")
    c3 = contrast(page, ".eyebrow", "body")
    check("正文对比度 >= 4.5", c1 >= 4.5, c1)
    check("辅助文字对比度 >= 4.5", c2 >= 4.5, c2)
    check("eyebrow 对比度 >= 4.5", c3 >= 4.5, c3)

    # 打卡
    page.locator("#check-btn").click()
    page.wait_for_timeout(700)
    check("打卡后 streak=13", page.locator("#streak-num").inner_text() == "13")
    check("打卡后按钮为已完成态", "is-checked" in (page.locator("#check-btn").get_attribute("class") or ""))
    check("出现提示条", page.locator("#snackbar").is_visible())
    page.screenshot(path=str(SHOTS / "today-checked.png"))

    # 撤销
    page.locator("#snack-action").click()
    page.wait_for_timeout(500)
    check("撤销后 streak=12", page.locator("#streak-num").inner_text() == "12")

    # 日历
    page.locator('.nav-item[data-go="calendar"]').click()
    page.wait_for_timeout(600)
    page.screenshot(path=str(SHOTS / "calendar.png"))
    ov = no_overflow(page)
    check("日历无横向溢出", ov["sw"] <= ov["iw"] + 1, ov)
    cells = page.locator(".cal-day:not(.is-blank)").count()
    check("日历格子数合理", 28 <= cells <= 31, cells)

    # 补记：切到上个月，点一个未打卡的过去日子
    page.locator("#cal-prev").click()
    page.wait_for_timeout(500)
    target = page.evaluate(
        """() => {
      const cells = [...document.querySelectorAll('.cal-day:not(.is-blank)')];
      const t = cells.find(c => c.dataset.day && !c.disabled && !c.classList.contains('is-checked') && !c.classList.contains('is-today'));
      return t ? t.dataset.day : null;
    }"""
    )
    check("找到可补记的日期", bool(target), target)
    if target:
        page.locator(f'.cal-day[data-day="{target}"]').click()
        page.wait_for_timeout(400)
        check("补记弹窗出现", page.locator(".dialog").is_visible())
        page.get_by_role("button", name="补记这一天").click()
        page.wait_for_timeout(400)
        check("补记生效", "is-checked" in (page.locator(f'.cal-day[data-day="{target}"]').get_attribute("class") or ""))

    # 应急页
    page.locator('.nav-item[data-go="sos"]').click()
    page.wait_for_timeout(500)
    page.screenshot(path=str(SHOTS / "sos.png"))
    page.locator("#breath-btn").click()
    page.wait_for_timeout(2200)
    phase = page.locator("#breath-phase").inner_text()
    check("呼吸练习运行中", "吸" in phase or "停" in phase, phase)
    page.wait_for_timeout(3000)
    phase2 = page.locator("#breath-phase").inner_text()
    check("呼吸阶段推进", phase2 != phase, f"{phase} -> {phase2}")
    page.locator("#breath-btn").click()

    page.locator("#timer-btn").click()
    page.wait_for_timeout(1400)
    t = page.locator("#timer-time").inner_text()
    check("计时器倒数", t.startswith("09:5"), t)

    page.fill("#note-input", "此刻有点难，但我在这里。")
    page.locator("#note-save").click()
    page.wait_for_timeout(400)
    txt = page.locator("#note-list li").first.inner_text()
    check("笔记保存", "此刻有点难" in txt, txt)

    # 我的
    page.locator('.nav-item[data-go="me"]').click()
    page.wait_for_timeout(500)
    page.screenshot(path=str(SHOTS / "me.png"))
    badges = page.locator(".badge").count()
    check("里程碑 12 个", badges == 12, badges)

    page.locator('#theme-seg button[data-mode="dark"]').click()
    page.wait_for_timeout(400)
    theme = page.evaluate("document.documentElement.dataset.theme")
    check("切换深色", theme == "dark", theme)
    page.screenshot(path=str(SHOTS / "me-dark.png"))
    page.locator('.nav-item[data-go="today"]').click()
    page.wait_for_timeout(500)
    page.screenshot(path=str(SHOTS / "today-dark.png"))
    c_dark = contrast(page, "#check-hint", "body")
    check("深色辅助文字对比度 >= 4.5", c_dark >= 4.5, c_dark)

    # 复发流程
    page.locator("#relapse-btn").click()
    page.wait_for_timeout(400)
    page.screenshot(path=str(SHOTS / "relapse-dialog.png"))
    page.locator(".option-chip", has_text="压力").first.click()
    page.get_by_role("button", name="记录并重新开始").click()
    page.wait_for_timeout(500)
    restarts = page.locator("#stat-restart").inner_text()
    check("重启次数 +1", restarts == "2", restarts)
    check("重启后连续天数归零", page.locator("#streak-num").inner_text() in ("0", "1"))

    errs = [e for e in console_errors if "favicon" not in e.lower()]
    check("控制台无报错", len(errs) == 0, errs)
    ctx.close()

    # ---------- B. 正常模式：首次引导 + 持久化 ----------
    console_errors.clear()
    ctx2 = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, locale="zh-CN")
    pg = ctx2.new_page()
    pg.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_timeout(500)
    check("首次进入显示引导", pg.locator(".dialog").is_visible())
    pg.screenshot(path=str(SHOTS / "onboarding.png"))
    pg.locator('.option-chip', has_text="60 天").click()
    pg.get_by_role("button", name="开始", exact=True).click()
    pg.wait_for_timeout(400)
    check("引导关闭", pg.locator(".dialog").count() == 0)
    check("目标显示 60 天", "60" in pg.locator("#goal-pill").inner_text())

    pg.locator("#check-btn").click()
    pg.wait_for_timeout(600)
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(500)
    check("刷新后保留打卡", pg.locator("#streak-num").inner_text() == "1", pg.locator("#streak-num").inner_text())
    check("刷新后不再弹引导", pg.locator(".dialog").count() == 0)
    check("刷新后目标保留", "60" in pg.locator("#goal-pill").inner_text())

    # 时间篡改/空档：删除今天打卡后 streak 归零但不报错
    pg.locator("#check-btn").click()
    pg.wait_for_timeout(400)
    check("撤销后归零", pg.locator("#streak-num").inner_text() == "0")

    errs2 = [e for e in console_errors if "favicon" not in e.lower()]
    check("正常模式无 JS 报错", len(errs2) == 0, errs2)
    ctx2.close()
    browser.close()

passed = sum(1 for r in results if r["ok"])
print(f"\n{passed}/{len(results)} passed")
(ROOT / ".shots" / "report.json").write_text(json.dumps({"passed": passed, "total": len(results), "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
sys.exit(0 if passed == len(results) else 1)
