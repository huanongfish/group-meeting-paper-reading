#!/usr/bin/env python3
"""从论文 PDF 中提取图表，供组会文献解读文档插图使用。

依赖: PyMuPDF (pip install pymupdf --break-system-packages)

用法:
  # 模式一（默认）：提取 PDF 内嵌的位图，过滤掉小图标/logo
  python extract_figures.py paper.pdf -o figures/

  # 模式二：把指定页整页渲染成高清 PNG（内嵌图提取不全/矢量图时用，
  # 渲染后可再用任意工具裁剪出图的区域）
  python extract_figures.py paper.pdf -o figures/ --render-pages 3,5,7-9

输出文件命名: p{页码}_{序号}.png（嵌入图）/ page{页码}.png（整页渲染）。
提取完成后请逐张查看，人工对应正文图号（Figure 1、Figure 2…），
小图/残图/装饰图直接删掉。矢量绘制的图（线条图常见）不会以嵌入位图形式
存在，只能用 --render-pages 渲染整页获取。
"""
import argparse
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("缺少 PyMuPDF，请先运行: pip install pymupdf --break-system-packages")

MIN_W, MIN_H = 120, 120          # 过滤小图标
MIN_BYTES = 8 * 1024             # 过滤过小文件


def parse_pages(spec: str):
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            pages.update(range(int(a), int(b) + 1))
        elif part:
            pages.add(int(part))
    return sorted(pages)


def extract_embedded(doc, outdir: Path):
    count = 0
    for pno in range(len(doc)):
        seen_xrefs = set()
        for idx, info in enumerate(doc[pno].get_images(full=True)):
            xref = info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:  # CMYK 等转 RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.width < MIN_W or pix.height < MIN_H:
                    continue
                data = pix.tobytes("png")
                if len(data) < MIN_BYTES:
                    continue
                out = outdir / f"p{pno + 1}_{idx + 1}.png"
                out.write_bytes(data)
                count += 1
                print(f"  {out.name}  {pix.width}x{pix.height}")
            except Exception as e:  # 个别损坏对象不应中断整体提取
                print(f"  [跳过] 第{pno + 1}页 xref{xref}: {e}")
    return count


def render_pages(doc, outdir: Path, pages, dpi=200):
    count = 0
    for pno in pages:
        if not 1 <= pno <= len(doc):
            print(f"  [跳过] 页码 {pno} 超出范围 (共 {len(doc)} 页)")
            continue
        pix = doc[pno - 1].get_pixmap(dpi=dpi)
        out = outdir / f"page{pno}.png"
        pix.save(out)
        count += 1
        print(f"  {out.name}  {pix.width}x{pix.height}")
    return count


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("-o", "--outdir", default="figures")
    ap.add_argument("--render-pages", help="整页渲染的页码，如 3,5,7-9")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(args.pdf)

    if args.render_pages:
        n = render_pages(doc, outdir, parse_pages(args.render_pages), args.dpi)
        print(f"整页渲染 {n} 页 -> {outdir}/")
    else:
        n = extract_embedded(doc, outdir)
        print(f"提取嵌入图 {n} 张 -> {outdir}/")
        if n == 0:
            print("未提取到嵌入位图：论文的图可能是矢量绘制，请改用 --render-pages。")


if __name__ == "__main__":
    main()
