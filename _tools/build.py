"""作品集生成器：一份 works.json → 作品集站、个人主页 README、社交预览图。

用法（在仓库根目录跑）：
  python3 _tools/build.py shots [slug ...]   重截原型截图（不写 slug 就全截），存到 _tools/shots/
  python3 _tools/build.py build              生成 index.html、assets/、_tools/social/、主页 README
  python3 _tools/build.py all                先截图再生成

主页 README 默认写到同级目录 ../panglezym/README.md（个人主页仓库的本地克隆），
也可以用环境变量 PROFILE_DIR 指定。依赖：playwright（含 chromium）、Pillow。
"""
import base64, html, json, os, sys
from PIL import Image
from playwright.sync_api import sync_playwright

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SHOTS = os.path.join(TOOLS, "shots")
SOCIAL = os.path.join(TOOLS, "social")
ASSETS = os.path.join(ROOT, "assets")
PROFILE_DIR = os.environ.get("PROFILE_DIR", os.path.join(os.path.dirname(ROOT), "panglezym"))

CFG = json.load(open(os.path.join(TOOLS, "works.json"), encoding="utf-8"))
WORKS = CFG["works"]
OWNER = CFG["owner"]
P = f"https://{OWNER}.github.io"
G = f"https://github.com/{OWNER}"
e = html.escape
FONT = "-apple-system,'PingFang SC','Hiragino Sans GB',sans-serif"
BG = "#f4f2ee"


def live(w):
    return f"{P}/{w['repo']}/" if w["pages"] else f"{G}/{w['repo']}#readme"


def repo_url(w):
    return f"{G}/{w['repo']}"


# ---------- 截图 ----------

def run_steps(pg, steps):
    for s in steps:
        for _ in range(s.get("repeat", 1)):
            if "click_text" in s:
                pg.locator(f"text={s['click_text']} >> visible=true").first.click()
            elif "click_text_exact" in s:
                pg.get_by_text(s["click_text_exact"], exact=True).first.click()
            elif "js" in s:
                pg.evaluate(s["js"])
            elif "scroll_y" in s:
                pg.evaluate(f"scrollTo(0, {s['scroll_y']})")
            elif "scroll_to_block_of_text" in s:
                # 找到写着这段字的元素，往上找到宽度过 1000 的整块，让整块顶到窗口上沿
                y = pg.evaluate("""t => {
                  const el = [...document.querySelectorAll('*')].find(e => e.children.length === 0 && (e.innerText || '').trim() === t);
                  let c = el; while (c && c.getBoundingClientRect().width < 1000) c = c.parentElement;
                  return c.getBoundingClientRect().top + scrollY; }""", s["scroll_to_block_of_text"])
                pg.evaluate(f"scrollTo(0, {y} - 8)")
            pg.wait_for_timeout(s.get("wait", 500))


def shots(slugs):
    os.makedirs(SHOTS, exist_ok=True)
    todo = [w for w in WORKS if w.get("shot") and (not slugs or w["slug"] in slugs)]
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w in todo:
            vw, vh = w["shot"]["viewport"]
            pg = b.new_page(viewport={"width": vw, "height": vh}, device_scale_factor=2)
            pg.goto(live(w), wait_until="networkidle", timeout=60000)
            pg.wait_for_timeout(1200)
            run_steps(pg, w["shot"]["steps"])
            tmp = os.path.join(SHOTS, w["slug"] + ".png")
            pg.screenshot(path=tmp)
            Image.open(tmp).convert("RGB").save(tmp[:-4] + ".jpg", quality=92)
            os.remove(tmp)
            pg.close()
            print("截图", w["slug"])
        b.close()


# ---------- 图片合成 ----------

def uri(path):
    return "data:image/jpeg;base64," + base64.b64encode(open(path, "rb").read()).decode()


def toc_panel(card, w, h):
    """没有网页的作品（如白皮书）用一张目录页当它的“截图”。"""
    items = "".join(f"<li><span>{i:02d}</span>{e(t)}</li>" for i, t in enumerate(card["items"]))
    head = "<br>".join(e(x) for x in card["heading"])
    return f"""<div style="width:{w}px;height:{h}px;background:#fffdf8;padding:{h*0.09:.0f}px {w*0.08:.0f}px;font-family:{FONT};color:#1a1714;display:flex;flex-direction:column">
<p style="font-size:{h*0.032:.0f}px;letter-spacing:.2em;color:#b4441f;margin:0">{e(card['kicker'])}</p>
<h2 style="font-size:{h*0.075:.0f}px;line-height:1.25;margin:{h*0.03:.0f}px 0 {h*0.05:.0f}px;font-weight:700">{head}</h2>
<ul style="list-style:none;padding:0;margin:0;border-top:2px solid #1a1714">{items}</ul>
<style>li{{display:flex;gap:{w*0.03:.0f}px;font-size:{h*0.034:.0f}px;padding:{h*0.014:.0f}px 0;border-bottom:1px solid #e6e1d8}}li span{{color:#9a938b;font-variant-numeric:tabular-nums}}</style>
</div>"""


BY_SLUG = {w["slug"]: w for w in WORKS}


def shot_box(slug, w, h):
    work = BY_SLUG[slug]
    if work.get("toc_card"):
        return toc_panel(work["toc_card"], w, h)
    src = os.path.join(SHOTS, slug + ".jpg")
    if not os.path.exists(src):
        sys.exit(f"[停] 缺截图 {src}，先跑 build.py shots {slug}")
    return f'<img src="{uri(src)}" style="width:{w}px;height:{h}px;object-fit:cover;object-position:left top;display:block">'


def social_html(w):
    title = "<br>".join(e(x) for x in w.get("title_lines", [w["title"]]))
    chips = "".join(f"<span>{e(t)}</span>" for t in w["tags"])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0}}
body{{width:1280px;height:640px;background:{BG};font-family:{FONT};color:#1a1714;-webkit-font-smoothing:antialiased;position:relative;overflow:hidden}}
.txt{{position:absolute;left:64px;top:68px;bottom:52px;width:400px;display:flex;flex-direction:column}}
h1{{font-size:46px;line-height:1.28;font-weight:700;text-wrap:balance}}
.en{{font-size:20px;color:#8a837b;margin-top:14px;line-height:1.45}}
.tags{{margin-top:28px;display:flex;flex-wrap:wrap;gap:10px}}
.tags span{{font-size:18px;padding:5px 15px;border:2px solid #1a1714;border-radius:999px}}
.foot{{margin-top:auto;font-size:18px;color:#8a837b;letter-spacing:.02em}}
.shot{{position:absolute;left:510px;top:64px;width:860px;height:620px;border-radius:14px;overflow:hidden;
  box-shadow:0 1px 0 rgba(0,0,0,.04),0 18px 50px rgba(40,30,20,.16);border:1px solid rgba(0,0,0,.08)}}
</style></head><body>
<div class="txt"><h1>{title}</h1><p class="en">{e(w['en'])}</p><div class="tags">{chips}</div><p class="foot">github.com/{OWNER}</p></div>
<div class="shot">{shot_box(w['slug'], 860, 620)}</div>
</body></html>"""


def collage_html(width, height, with_text):
    """首屏拼贴：works.json 里 hero 指定的三张截图错落叠放。"""
    s = width / 1200
    a, b_, c = CFG["hero"]

    def card(slug, x, y, w, h, z):
        return (f'<div style="position:absolute;left:{x*s:.0f}px;top:{y*s:.0f}px;width:{w*s:.0f}px;height:{h*s:.0f}px;z-index:{z};'
                f'border-radius:{12*s:.0f}px;overflow:hidden;border:1px solid rgba(0,0,0,.08);box-shadow:0 {16*s:.0f}px {44*s:.0f}px rgba(40,30,20,.18)">'
                f'{shot_box(slug, round(w*s), round(h*s))}</div>')
    if with_text:
        off = 520
        cards = card(a, 60 + off, 60, 640, 427, 1) + card(b_, 330 + off, 250, 640, 427, 2) + card(c, 40 + off, 400, 520, 347, 3)
        lines = "<br>".join(e(x) for x in CFG["og_lines"])
        text = f"""<div style="position:absolute;left:{64*s:.0f}px;top:{150*s:.0f}px;width:{440*s:.0f}px">
<h1 style="font-size:{64*s:.0f}px;line-height:1.2;margin:0">{e(CFG['name'])}</h1>
<p style="font-size:{30*s:.0f}px;color:#5c5650;margin:{18*s:.0f}px 0 0">AI 产品作品集</p>
<p style="font-size:{22*s:.0f}px;color:#8a837b;margin:{40*s:.0f}px 0 0;line-height:1.6">{len(WORKS)} 个作品：{lines}</p>
<p style="font-size:{20*s:.0f}px;color:#8a837b;margin:{80*s:.0f}px 0 0">{OWNER}.github.io</p></div>"""
    else:
        cards = card(a, 110, 50, 720, 480, 1) + card(b_, 430, 250, 720, 480, 2) + card(c, 60, 400, 570, 380, 3)
        text = ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>*{{box-sizing:border-box;margin:0}}
body{{width:{width}px;height:{height}px;background:{BG};font-family:{FONT};color:#1a1714;position:relative;overflow:hidden;-webkit-font-smoothing:antialiased}}</style></head>
<body>{text}{cards}</body></html>"""


def images():
    os.makedirs(SOCIAL, exist_ok=True)
    os.makedirs(os.path.join(ASSETS, "works"), exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--force-color-profile=srgb"])
        pg = b.new_page(viewport={"width": 1280, "height": 640}, device_scale_factor=1)

        def render(content, dst, w, h):
            pg.set_viewport_size({"width": w, "height": h})
            pg.set_content(content)
            pg.wait_for_timeout(200)
            tmp = dst + ".tmp.png"
            pg.screenshot(path=tmp)
            im = Image.open(tmp).convert("RGB")
            im.save(dst, optimize=True) if dst.endswith(".png") else im.save(dst, quality=86, optimize=True)
            os.remove(tmp)
            assert os.path.getsize(dst) < 1_000_000, f"{dst} 超过 1MB（GitHub 预览图上限）"

        for w in WORKS:
            render(social_html(w), os.path.join(SOCIAL, w["slug"] + ".png"), 1280, 640)
            render(f'<!doctype html><html><body style="margin:0">{shot_box(w["slug"], 1200, 800)}</body></html>',
                   os.path.join(ASSETS, "works", w["slug"] + ".jpg"), 1200, 800)
        render(collage_html(1200, 820, False), os.path.join(ASSETS, "hero.jpg"), 1200, 820)
        render(collage_html(1280, 640, True), os.path.join(ASSETS, "og.png"), 1280, 640)
        b.close()
    print("图片", len(WORKS), "张预览图 + 站点图")


# ---------- 页面与 README ----------

CSS = """
:root {
  --ink: #1a1714; --ink2: #5c5650; --ink3: #9a938b; --line: #ece8e3; --soft: #f7f5f2;
  --accent: #2747d6; --radius: 18px;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: #fff; color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
  line-height: 1.7; -webkit-font-smoothing: antialiased; }
a { color: inherit; }
.wrap { max-width: 1120px; margin: 0 auto; padding: 0 28px; }
header.top { display: flex; justify-content: space-between; align-items: center; padding: 26px 0; font-size: 15px; }
header.top .mark { font-weight: 700; letter-spacing: .02em; text-decoration: none; }
header.top nav a { color: var(--ink2); text-decoration: none; margin-left: 22px; }
header.top nav a:hover { color: var(--ink); }
.hero { display: grid; grid-template-columns: 1.05fr 1fr; gap: 56px; align-items: center; padding: 40px 0 72px; }
.hero h1 { font-size: 60px; line-height: 1.1; margin: 0 0 14px; letter-spacing: .01em; }
.hero .role { font-size: 19px; color: var(--ink2); margin: 0 0 26px; }
.hero .lead { font-size: 17px; color: var(--ink); margin: 0 0 28px; max-width: 34em; }
.chips { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 10px; }
.chips li { font-size: 14px; padding: 6px 14px; border: 1.5px solid var(--ink); border-radius: 999px; }
.hero figure { margin: 0; }
.hero figure img { width: 100%; height: auto; display: block; border-radius: var(--radius); }
.section-head { display: flex; align-items: baseline; justify-content: space-between; border-top: 1.5px solid var(--ink); padding: 22px 0 30px; }
.section-head h2 { font-size: 28px; margin: 0; }
.section-head span { color: var(--ink3); font-size: 15px; }
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 40px 36px; padding-bottom: 80px; }
.work { display: flex; flex-direction: column; }
.shot { display: block; border-radius: var(--radius); overflow: hidden; border: 1px solid rgba(0,0,0,.08); background: #fff; aspect-ratio: 3 / 2; box-shadow: 0 10px 30px rgba(40,30,20,.08); }
.shot img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform .5s cubic-bezier(.2,.7,.2,1); }
.shot:hover img { transform: scale(1.03); }
.body { padding: 20px 4px 0; }
.no { font-size: 13px; color: var(--ink3); margin: 0 0 6px; font-variant-numeric: tabular-nums; letter-spacing: .08em; }
.work h3 { font-size: 22px; line-height: 1.35; margin: 0; }
.en { font-size: 14px; color: var(--ink3); margin: 4px 0 12px; }
.desc { font-size: 15.5px; color: var(--ink2); margin: 0 0 14px; }
.tags { list-style: none; padding: 0; margin: 0 0 16px; display: flex; flex-wrap: wrap; gap: 8px; }
.tags li { font-size: 13px; color: var(--ink2); background: var(--soft); padding: 3px 10px; border-radius: 6px; }
.links { margin: 0; font-size: 15px; display: flex; gap: 20px; }
.links a { text-decoration: none; color: var(--ink2); border-bottom: 1.5px solid transparent; }
.links a:hover { border-bottom-color: currentColor; }
.links a.primary { color: var(--accent); font-weight: 600; }
footer { border-top: 1.5px solid var(--line); padding: 28px 0 48px; font-size: 14px; color: var(--ink3); }
footer p { margin: 0 0 6px; }
@media (max-width: 860px) {
  .hero { grid-template-columns: 1fr; gap: 32px; padding-top: 16px; }
  .hero h1 { font-size: 44px; }
  .grid { grid-template-columns: 1fr; gap: 44px; }
}
"""


def pages():
    name = CFG["name"]
    cards = []
    for i, w in enumerate(WORKS, 1):
        tags = "".join(f"<li>{e(t)}</li>" for t in w["tags"])
        label = "在线看" if w["pages"] else "阅读全文"
        cards.append(f"""
      <article class="work">
        <a class="shot" href="{live(w)}" target="_blank" rel="noopener">
          <img src="assets/works/{w['slug']}.jpg" alt="{e(w['title'])} 的界面截图" loading="lazy" width="1200" height="800">
        </a>
        <div class="body">
          <p class="no">{i:02d}</p>
          <h3>{e(w['title'])}</h3>
          <p class="en">{e(w['en'])}</p>
          <p class="desc">{e(w['desc'])}</p>
          <ul class="tags">{tags}</ul>
          <p class="links"><a class="primary" href="{live(w)}" target="_blank" rel="noopener">{label} →</a><a href="{repo_url(w)}" target="_blank" rel="noopener">仓库</a></p>
        </div>
      </article>""")
    hero_alt = "、".join(BY_SLUG[s]["title"] for s in CFG["hero"]) + "三个作品的界面截图"
    focus = "".join(f"<li>{e(f)}</li>" for f in CFG["focus"])
    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} · AI 产品作品集</title>
<meta name="description" content="{e(CFG['lead'])}">
<meta property="og:type" content="website">
<meta property="og:title" content="{name} · AI 产品作品集">
<meta property="og:description" content="{len(WORKS)} 个 AI 产品设计作品：{e(CFG['og_summary'])}。">
<meta property="og:image" content="{P}/assets/og.png">
<meta property="og:url" content="{P}/">
<meta name="twitter:card" content="summary_large_image">
<style>{CSS}</style>
</head>
<body>
  <div class="wrap">
    <header class="top">
      <a class="mark" href="{P}/">{OWNER}</a>
      <nav><a href="#works">作品</a><a href="{G}" target="_blank" rel="noopener">GitHub</a></nav>
    </header>
    <section class="hero">
      <div>
        <h1>{name}</h1>
        <p class="role">{e(CFG['role'])}</p>
        <p class="lead">{e(CFG['lead'])}</p>
        <ul class="chips">{focus}</ul>
      </div>
      <figure><img src="assets/hero.jpg" alt="{e(hero_alt)}" width="1200" height="820"></figure>
    </section>
    <div class="section-head" id="works"><h2>作品</h2><span>{len(WORKS)} 个 · 点图片直接打开</span></div>
    <section class="grid">{''.join(cards)}
    </section>
    <footer>
      <p>{e(CFG['note'])}</p>
      <p>© 2026 {name} · 内容仅供学习交流，转载请注明出处。</p>
    </footer>
  </div>
</body>
</html>
"""
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(page)

    rows = "\n".join(f"| [{w['title']}]({live(w)}) | {w['short']} | [仓库]({repo_url(w)}) |" for w in WORKS)
    readme = f"""### 你好，我是{name} 👋

{CFG['profile_intro']}

*{CFG['profile_intro_en']}*

**📂 作品集：[{OWNER}.github.io]({P}/)**

| 作品 | 一句话 | 源文件 |
|---|---|---|
{rows}

<sub>{CFG['note']}</sub>
"""
    if os.path.isdir(PROFILE_DIR):
        open(os.path.join(PROFILE_DIR, "README.md"), "w", encoding="utf-8").write(readme)
        print("主页 README →", PROFILE_DIR)
    else:
        out = os.path.join(TOOLS, "profile-README.md")
        open(out, "w", encoding="utf-8").write(readme)
        print(f"没找到主页仓库克隆 {PROFILE_DIR}，README 先写到 {out}")
    print("页面 index.html")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "shots":
        shots(sys.argv[2:])
    elif cmd == "build":
        images(); pages()
    elif cmd == "all":
        shots([]); images(); pages()
    else:
        print(__doc__)
