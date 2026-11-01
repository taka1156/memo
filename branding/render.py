"""branding/ の HTML から docs/assets/ の OGP 画像とアイコンを生成する（黒テーマ）。

    python3 branding/render.py

要: playwright (chromium), Pillow, フォント Noto Sans CJK JP / DejaVu Sans Mono
"""
import os
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "docs" / "assets"
DARK = ("--desk:#0a0e14;--paper:#111823;--rule:#1e2d3d;--margin:#00d4ff;--shadow:#00000090;"
        "--ink:#00d4ff;--pen:#00a8cc;--pen-hi:#00d4ff;--pen-ring:#7d8b9d;--pen-grip:#cdd9e5;--holebg:#0a0e14")


def main():
    tpl = (HERE / "icon.html").read_text()
    tmp = HERE / "_tmp.html"
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 630})
        pg.goto((HERE / "og.html").as_uri()); pg.wait_for_timeout(300)
        pg.screenshot(path=str(ASSETS / "og.png"))

        pg.set_viewport_size({"width": 1024, "height": 1024})
        shots = {}
        for key, cls, holes in (("full", "", 5), ("small", "small t", 3)):
            tmp.write_text(tpl.replace("__VARS", DARK).replace("__CLS", cls).replace("__HOLES", "<i></i>" * holes))
            pg.goto(tmp.as_uri()); pg.wait_for_timeout(200)
            out = HERE / f"_icon-{key}.png"
            pg.screenshot(path=str(out), omit_background=True)
            shots[key] = out
        b.close()
    tmp.unlink()

    full = Image.open(shots["full"]).convert("RGB")      # iOS は透過不可
    small = Image.open(shots["small"]).convert("RGBA")   # ファビコンは簡略・透過
    full.resize((180, 180), Image.LANCZOS).save(ASSETS / "apple-touch-icon.png")
    full.resize((192, 192), Image.LANCZOS).save(ASSETS / "icon-192.png")
    small.resize((32, 32), Image.LANCZOS).save(ASSETS / "icon-32.png")
    small.resize((48, 48), Image.LANCZOS).save(ASSETS / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    for f in shots.values():
        os.remove(f)
    print("updated:", ", ".join(sorted(x.name for x in ASSETS.iterdir())))


if __name__ == "__main__":
    main()
