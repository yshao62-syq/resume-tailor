"""HTML → PDF 渲染器。HTML 是事实来源（手动 contenteditable 可编辑），本脚本只负责
把编辑好的 HTML 渲染成可移植 PDF。

为什么内联字体：headless Chromium 不加载系统字体，file:// / page.route 都试过无效，
只有 base64 data: URL 内联稳。嵌 Regular + Italic 两字重——
  · Italic 让全文 <i> 用真斜体（真斜体字形窄、每行容字多、换行少，才稳稳一页；
    合成假斜体用常规字宽会多换行 ~20%、把一页撑成两页）
  · Regular 给非斜体的姓名 / 联系方式
粗体由 Chromium 从对应字重合成（faux bold），标题够用。

用法: python html2pdf.py [input.html] [output.pdf]
"""
import base64
import os
import sys
from playwright.sync_api import sync_playwright

FONT_DIR = "/Users/yunqing/Library/Fonts"
ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IN = os.path.join(ROOT, "sample_data", "syq_resume.html")
DEFAULT_OUT = os.path.join(ROOT, "sample_data", "syq_resume.pdf")


def _face(weight: str, style: str, fname: str) -> str:
    b64 = base64.b64encode(open(os.path.join(FONT_DIR, fname), "rb").read()).decode()
    return (
        f'@font-face{{font-family:"Maple Mono";'
        f'src:url("data:font/ttf;base64,{b64}");font-weight:{weight};font-style:{style};}}'
    )


def render(html_path: str = DEFAULT_IN, pdf_path: str = DEFAULT_OUT) -> None:
    html = open(html_path, encoding="utf-8").read()
    # Regular（normal 400）+ Italic（italic 400）两字重内联
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
    render(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IN,
           sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT)
