"""HTML → PDF 渲染器（skill 用）。用法: python render.py input.html output.pdf

headless Chromium 不加载系统字体，把 Maple Mono 的 Regular + Italic 两字重
以 base64 内联进 CSS，绕过限制。Italic 必须真嵌（合成假斜体字宽不同会多换行）。
"""
import base64
import sys
from playwright.sync_api import sync_playwright

FONT_DIR = "/Users/yunqing/Library/Fonts"


def _face(weight: str, style: str, fname: str) -> str:
    b64 = base64.b64encode(open(f"{FONT_DIR}/{fname}", "rb").read()).decode()
    return (
        f'@font-face{{font-family:"Maple Mono";'
        f'src:url("data:font/ttf;base64,{b64}");font-weight:{weight};font-style:{style};}}'
    )


def render(html_path: str, pdf_path: str) -> None:
    html = open(html_path, encoding="utf-8").read()
    faces = (
        _face("400", "normal", "MapleMono-NF-CN-Regular.ttf")
        + _face("400", "italic", "MapleMono-NF-CN-Italic.ttf")
    )
    html = html.replace("</style>", faces + "</style>", 1)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content(html, wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.pdf(path=pdf_path, format="A4", print_background=True, prefer_css_page_size=True)
        b.close()
    print(f"PDF: {pdf_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python render.py input.html [output.pdf]")
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp.rsplit(".", 1)[0] + ".pdf"
    render(inp, out)
