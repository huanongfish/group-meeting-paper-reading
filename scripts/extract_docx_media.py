#!/usr/bin/env python3
"""Extract text (with inline image anchors) + media files from a .docx.

Usage: python extract_docx_media.py input.docx outdir
Writes outdir/text.txt (with [[IMG:name]] anchors in document order)
and outdir/media/<name> for every embedded image.
"""
import sys, os, zipfile, shutil
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def para_text(p):
    parts = []
    for node in p.iter():
        tag = node.tag
        if tag == W + "t":
            parts.append(node.text or "")
        elif tag == W + "tab":
            parts.append("\t")
        elif tag in (W + "br", W + "cr"):
            parts.append("\n")
        elif tag == A + "blip":
            rid = node.get(R + "embed") or node.get(R + "link")
            if rid:
                parts.append(f"[[IMG:{rid}]]")
    return "".join(parts)


def main(src, outdir):
    os.makedirs(outdir, exist_ok=True)
    mediadir = os.path.join(outdir, "media")
    os.makedirs(mediadir, exist_ok=True)

    with zipfile.ZipFile(src) as z:
        names = z.namelist()
        xml = z.read("word/document.xml")
        # relationship id -> media target
        rels = {}
        if "word/_rels/document.xml.rels" in names:
            rr = ET.fromstring(z.read("word/_rels/document.xml.rels"))
            for rel in rr:
                rels[rel.get("Id")] = rel.get("Target")
        # dump media
        media_map = {}
        for n in names:
            if n.startswith("word/media/") and not n.endswith("/"):
                base = os.path.basename(n)
                with z.open(n) as fh, open(os.path.join(mediadir, base), "wb") as out:
                    shutil.copyfileobj(fh, out)
                media_map[n.replace("word/", "")] = base

    root = ET.fromstring(xml)
    body = root.find(W + "body")
    out = []
    for child in body:
        if child.tag == W + "p":
            t = para_text(child)
            # resolve rid -> filename
            for rid, target in rels.items():
                fn = media_map.get(target)
                if fn:
                    t = t.replace(f"[[IMG:{rid}]]", f"[[IMG:{fn}]]")
            out.append(t)
        elif child.tag == W + "tbl":
            out.append("[TABLE]")
            for tr in child.findall(W + "tr"):
                cells = []
                for tc in tr.findall(W + "tc"):
                    txt = " ".join(para_text(p) for p in tc.findall(W + "p"))
                    cells.append(txt.strip())
                out.append(" | ".join(cells))
            out.append("[/TABLE]")

    txt = "\n".join(out)
    with open(os.path.join(outdir, "text.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"{src} -> {outdir}/text.txt  ({len(txt)} chars)")
    print(f"  media: {len(media_map)} files")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
