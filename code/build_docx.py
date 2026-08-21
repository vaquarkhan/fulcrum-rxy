"""Build a shareable Word (.docx) version of the paper with figures embedded.

Standard-library + python-docx. Handles headings, tables, code blocks, blockquotes, lists,
markdown image tags ![alt](figures/x.png), and inline **bold** / [n] citations.

Run: python build_docx.py
Author: Viquar Khan. Copyright 2026 Viquar Khan.
"""
import re, os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

HERE = os.path.dirname(os.path.abspath(__file__))
# Manuscript and figures live in the parent folder (this script was moved into code/).
PARENT = os.path.dirname(HERE)
MD = os.path.join(PARENT, "Fulcrum-RVx-Research-Paper-Hardened.md")
OUT = os.path.join(PARENT, "Fulcrum-RVx-Research-Paper-Hardened.docx")


def add_inline(p, text):
    pattern = re.compile(r"\*\*(.+?)\*\*|\[(\d+(?:\s*[,\-]\s*\d+)*)\]")
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            p.add_run(text[pos:m.start()].replace("`", ""))
        if m.group(1) is not None:
            r = p.add_run(m.group(1).replace("`", "")); r.bold = True
        else:
            r = p.add_run(m.group(2).replace(" ", "")); r.font.superscript = True
        pos = m.end()
    if pos < len(text):
        p.add_run(text[pos:].replace("`", ""))


def parse_table(lines, doc):
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines]
    if len(rows) < 2:
        return
    header, body = rows[0], rows[2:]
    ncol = len(header)
    table = doc.add_table(rows=1, cols=ncol)
    try:
        table.style = "Light Grid Accent 1"
    except Exception:
        pass
    for i, h in enumerate(header):
        c = table.rows[0].cells[i]; c.paragraphs[0].text = ""
        add_inline(c.paragraphs[0], h)
        for run in c.paragraphs[0].runs:
            run.bold = True
    for r in body:
        cells = table.add_row().cells
        for i in range(ncol):
            cells[i].paragraphs[0].text = ""
            add_inline(cells[i].paragraphs[0], r[i] if i < len(r) else "")
    doc.add_paragraph()


def main():
    lines = open(MD, encoding="utf-8").read().split("\n")
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    i, first_h1, in_code, n_img = 0, True, False, 0
    while i < len(lines):
        raw = lines[i].rstrip("\n")
        s = raw.strip()
        if s.startswith("```"):
            in_code = not in_code; i += 1; continue
        if in_code:
            p = doc.add_paragraph(raw)
            for r in p.runs:
                r.font.name = "Consolas"; r.font.size = Pt(8.5)
            i += 1; continue
        if re.match(r"^---+$", s) or s == "":
            i += 1; continue
        # image
        mi = re.match(r"^!\[[^\]]*\]\(([^)]+)\)$", s)
        if mi:
            path = os.path.join(PARENT, mi.group(1))
            if os.path.exists(path):
                try:
                    doc.add_picture(path, width=Inches(6.2))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                    n_img += 1
                except Exception:
                    pass
            i += 1; continue
        # table
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?[\s:\-|]+\|?$", lines[i + 1].strip()):
            tbl = [raw]; j = i + 1
            while j < len(lines) and lines[j].strip().startswith("|"):
                tbl.append(lines[j]); j += 1
            parse_table(tbl, doc); i = j; continue
        # heading
        mh = re.match(r"^(#{1,6})\s+(.*)$", s)
        if mh:
            lvl = len(mh.group(1)); txt = mh.group(2)
            if lvl == 1 and first_h1:
                first_h1 = False
                p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(txt); r.bold = True; r.font.size = Pt(17)
            else:
                h = doc.add_heading(level=min(lvl, 4)); h.text = ""
                add_inline(h, txt)
            i += 1; continue
        # blockquote
        if s.startswith(">"):
            p = doc.add_paragraph()
            r = p.add_run(re.sub(r"^>\s?", "", raw)); r.italic = True
            r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            i += 1; continue
        # bullet
        mb = re.match(r"^[-*]\s+(.*)$", s)
        if mb:
            add_inline(doc.add_paragraph(style="List Bullet"), mb.group(1)); i += 1; continue
        # numbered
        mn = re.match(r"^(\d+)\.\s+(.*)$", s)
        if mn:
            p = doc.add_paragraph(); p.add_run(mn.group(1) + ". ")
            add_inline(p, mn.group(2)); i += 1; continue
        # italic caption line like *Figure N. ...*
        add_inline(doc.add_paragraph(), raw)
        i += 1
    try:
        doc.save(OUT)
        print(f"wrote {OUT}  (images embedded: {n_img})")
    except PermissionError:
        base, ext = os.path.splitext(OUT)
        alt = base + "-new" + ext
        doc.save(alt)
        print(f"target locked (open in Word?); wrote {alt}  (images embedded: {n_img})")
        print("Close the open document and rename the -new file over the original.")


if __name__ == "__main__":
    main()
